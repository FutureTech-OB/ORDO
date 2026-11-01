"""End-to-end stdio protocol smoke test; no paid inference."""
import asyncio
import json
import os
from pathlib import Path
import sys
import uuid
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params=StdioServerParameters(command=sys.executable,args=['-m','orgabm.mcp_server','--output-root',
        str(Path('runs')/('mcp-check-'+uuid.uuid4().hex))],env=dict(os.environ))
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            listing=await session.list_tools()
            names={tool.name for tool in listing.tools}
            assert {'describe_interface','preview_experiment','start_experiment','get_experiment','inspect_decision',
                    'preview_persona_assignment','start_persona_assignment'}<=names
            assignment_job=json.loads(Path('examples/persona_assignment.json').read_text(encoding='utf-8'))
            assignment_preview=await session.call_tool('preview_persona_assignment',{'job':assignment_job})
            assert not assignment_preview.isError
            assert json.loads(assignment_preview.content[0].text)['threshold']==0.5
            blocked_assignment=await session.call_tool('start_persona_assignment',{'job':assignment_job})
            assert blocked_assignment.isError, 'Unenabled paid population preparation must be rejected.'
            rejected=await session.call_tool('preview_experiment',{'plan':{'employees':8,'decision_mode':'rule/best'}})
            assert rejected.isError, 'Unknown experiment field aliases must not be accepted.'
            chat=await session.call_tool('preview_experiment',{'plan':{'decision':{'provider':'deepseek'}}})
            assert chat.isError, 'The research assistant must not select itself as the simulated decision engine.'
            jev=await session.call_tool('preview_experiment',{'plan':{'base':{'agents':16,'rounds':2},'decision':{'provider':'jev','batch_size':8}}})
            assert not jev.isError
            assert json.loads(jev.content[0].text)['provider_requests']==4
            base=json.loads(Path('examples/persona_organization.json').read_text(encoding='utf-8'))
            seed=base.pop('seed')
            base.pop('engine')
            base['rounds']=2
            plan={'base':base,'seeds':[seed]}
            preview=await session.call_tool('preview_experiment',{'plan':plan})
            assert not preview.isError
            started=await session.call_tool('start_experiment',{'plan':plan})
            assert not started.isError
            data=json.loads(started.content[0].text)
            for _ in range(20):
                status=await session.call_tool('get_experiment',{'experiment_id':data['id']})
                info=json.loads(status.content[0].text)
                if info['status'] in ['complete','failed']:break
                await asyncio.sleep(.2)
            assert info['status']=='complete',info
            trace=await session.call_tool('inspect_decision',dict(experiment_id=data['id'],world=0,round_no=2,agent=0))
            assert not trace.isError
            question=json.loads(trace.content[0].text)['question']
            observation=json.loads(question['instructions'].split('\n',1)[0])
            assert 'persona' in observation and 'organization' in observation
            assert 'source' not in observation['persona']
            from orgabm.templates import workflow_plan
            workflow=workflow_plan();workflow['seeds']=[7];workflow['base']['review_capacity']=2
            wf_preview=await session.call_tool('preview_experiment',{'plan':workflow})
            assert not wf_preview.isError,wf_preview
            assert json.loads(wf_preview.content[0].text)['counts_are_upper_bounds']
            wf_started=await session.call_tool('start_experiment',{'plan':workflow})
            assert not wf_started.isError,wf_started
            wf_id=json.loads(wf_started.content[0].text)['id']
            for _ in range(20):
                wf_status=await session.call_tool('get_experiment',{'experiment_id':wf_id})
                wf_info=json.loads(wf_status.content[0].text)
                if wf_info['status'] in ['complete','failed']:break
            assert wf_info['status']=='complete',wf_info
            wf_trace=await session.call_tool('inspect_decision',dict(experiment_id=wf_id,world=0,round_no=1,agent=0,stage='review_0'))
            assert not wf_trace.isError,wf_trace
            wf_record=json.loads(wf_trace.content[0].text)
            assert wf_record['stage_effects']['events']
            wf_observation=json.loads(wf_record['question']['instructions'])
            assert wf_observation['task']['requested_at']==1
            assert 'success_probability' not in wf_observation['task']
            memory_plan=workflow_plan('memory_permissions')
            memory_start=await session.call_tool('start_experiment',{'plan':memory_plan})
            assert not memory_start.isError,memory_start
            memory_id=json.loads(memory_start.content[0].text)['id']
            memory_status=await session.call_tool('get_experiment',{'experiment_id':memory_id,'wait_seconds':10})
            memory_info=json.loads(memory_status.content[0].text)
            assert memory_info['status']=='complete',memory_info
            employee_record=await session.call_tool('inspect_decision',dict(experiment_id=memory_id,world=0,round_no=1,agent=1,stage='proposal'))
            manager_record=await session.call_tool('inspect_decision',dict(experiment_id=memory_id,world=0,round_no=1,agent=0,stage='review_0'))
            assert not employee_record.isError and not manager_record.isError
            employee_json=json.loads(employee_record.content[0].text)
            manager_json=json.loads(manager_record.content[0].text)
            employee_view=json.loads(employee_json['question']['instructions'])['memory']
            manager_view=json.loads(manager_json['question']['instructions'])['memory']
            assert not any(n['node_id']=='demand' for n in employee_view['items'])
            assert any(n['node_id']=='demand' and n['level']=='detail' for n in manager_view['items'])
            assert 'memory_visibility' in manager_json['stage_effects']
            print(json.dumps({'mcp_tools':len(names),'status':info['status'],'worlds':info['completed_worlds'],
                              'workflow_worlds':wf_info['completed_worlds'],'workflow_trace':wf_record['id'],
                              'memory_worlds':memory_info['completed_worlds'],'memory_permissions_checked':True,
                              'persona_in_decision':True,
                              'decision_trace':json.loads(trace.content[0].text)['id']}))


if __name__=='__main__':asyncio.run(main())
