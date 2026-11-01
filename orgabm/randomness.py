import hashlib
import math
import random


def stable_seed(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:8], 'big')


def sample(probabilities, seed):
    if not probabilities or any(not math.isfinite(p) or p < 0 for p in probabilities.values()):
        raise ValueError('Invalid action probabilities')
    total = sum(probabilities.values())
    if total <= 0:
        raise ValueError('Empty probability mass')
    draw = random.Random(seed).random()
    cumulative = 0.0
    for action in sorted(probabilities):
        cumulative += probabilities[action] / total
        if draw < cumulative:
            return action
    return sorted(probabilities)[-1]
