"""Explicit bounded transport retries for the native OpenRouter Jev adapter.

The original strict adapter is retained for historical replay/source provenance.
Retries are not provider-idempotent: ambiguous attempts may incur extra charges.
"""
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import hashlib
import http.client
import io
import json
import math
import random
import ssl
import time
import urllib.error

from .openrouter import OpenRouterJevEngine


def retry_after_seconds(value):
    if value is None:return None
    try:
        seconds=float(value)
        return max(0,seconds) if math.isfinite(seconds) else None
    except (TypeError,ValueError):
        try:
            date=parsedate_to_datetime(value)
            if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
            return max(0,(date-datetime.now(timezone.utc)).total_seconds())
        except (TypeError,ValueError,OverflowError):return None


class _RetryTransport:
    def __init__(self,engine,transport):self.engine,self.transport=engine,transport
    def open(self,request,timeout=None):
        e=self.engine; body=request.data; reservation=len(body)*e.price
        batch=hashlib.sha256(body).hexdigest()
        for attempt in range(e.max_retries+1):
            if attempt:
                with e.lock:
                    if e.failed:raise RuntimeError('Another batch stopped this engine.')
                    if e.started>=e.max_requests or e.cost+e.reserved+reservation>e.cap:
                        raise ValueError('No client request/cost allowance remains for retry.')
                    # Keep failed-attempt reservations: the provider may have billed them.
                    e.started+=1; e.reserved+=reservation; e.retry_attempts+=1
            status=None; retry_after=None; reason=''; transient=False
            try:
                with self.transport.open(request,timeout=e.timeout) as response:raw=response.read()
                # A syntactically invalid response is not treated as transient inference.
                json.loads(raw)
                return io.BytesIO(raw)
            except urllib.error.HTTPError as error:
                status=error.code; reason=type(error).__name__
                transient=status in (408,429,500,502,503,504)
                retry_after=retry_after_seconds(error.headers.get('Retry-After') if error.headers else None)
                if status==402:
                    try:
                        payload=json.loads(error.read(8192))
                        transient=(payload.get('error',{}).get('metadata',{}).get('limit_source')=='openrouter_in_flight_budget'
                                   and retry_after is not None)
                    except Exception:transient=False
                error.close()
            except urllib.error.URLError as error:
                reason=type(error.reason).__name__
                transient=not isinstance(error.reason,(ssl.SSLCertVerificationError,ssl.CertificateError))
            except (TimeoutError,ConnectionError,http.client.IncompleteRead,http.client.RemoteDisconnected,ssl.SSLEOFError) as error:
                reason=type(error).__name__; transient=True
            except Exception as error:
                reason=type(error).__name__
            delay=e.backoff_base*(2**attempt)+random.uniform(0,e.jitter)
            if retry_after is not None:delay=max(delay,retry_after)
            retry=transient and attempt<e.max_retries and delay<=e.max_retry_delay
            record=dict(batch_sha256=batch,body_bytes=len(body),attempt=attempt+1,http_status=status,
                error_type=reason,transient=transient,will_retry=retry,delay_s=delay if retry else None,
                possible_additional_billing=True)
            with e.lock:
                e.transport_failures+=1
                with (e.output/'retry_events.jsonl').open('a',encoding='utf-8') as stream:
                    stream.write(json.dumps(record)+'\n')
            if not retry:
                raise RuntimeError(f'OpenRouter transport stopped after {attempt+1} attempt(s), status={status}, type={reason}.') from None
            time.sleep(delay)
        raise AssertionError('Unreachable retry state.')


class ReliableOpenRouterJevEngine(OpenRouterJevEngine):
    def __init__(self,*args,max_retries=3,timeout=90,backoff_base=1.0,jitter=.25,max_retry_delay=60,**kwargs):
        if type(max_retries) is not int or not 0<=max_retries<=5:raise ValueError('Use 0..5 retries per batch.')
        if type(timeout) not in (int,float) or not 0<timeout<=180:raise ValueError('Use a timeout in (0,180].')
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in (backoff_base,jitter,max_retry_delay)):
            raise ValueError('Retry delays must be finite and nonnegative.')
        super().__init__(*args,**kwargs)
        self.max_retries=max_retries;self.timeout=timeout;self.backoff_base=backoff_base
        self.jitter=jitter;self.max_retry_delay=max_retry_delay;self.retry_attempts=0;self.transport_failures=0
        self.transport=self.opener;self.opener=_RetryTransport(self,self.transport)

    def _call(self,state,questions):
        try:return super()._call(state,questions)
        except RuntimeError:
            if self.transport_failures:
                raise RuntimeError('OpenRouter request stopped after bounded retry handling; inspect retry_events.jsonl. Failed attempts may be billed.') from None
            raise

    def usage(self):
        usage=super().usage()
        usage.update(max_retries=self.max_retries,request_timeout_s=self.timeout,
            retry_attempts=self.retry_attempts,transport_failures=self.transport_failures,
            outstanding_or_uncertain_cost_reserve_usd=self.reserved,
            retry_policy='bounded exponential backoff; Retry-After honored; terminal/auth/credit/validation failures stop',
            accounting='Reported successful usage.cost plus conservative byte-based reservations for ambiguous failed attempts; no provider idempotency guarantee.')
        return usage
