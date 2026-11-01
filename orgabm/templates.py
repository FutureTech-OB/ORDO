"""Editable task-workflow templates; these encode explicit modeling assumptions."""
import copy


def workflow_plan(template='authority_comparison'):
    if template not in ('functional_hierarchy','delegated_teams','authority_comparison','review_capacity_comparison','memory_permissions'):
        raise ValueError('Unknown workflow template.')
    workers = [1,2,3,5,6,7,9,10,11]
    tasks=[]
    for wave in range(2):
        for i, owner in enumerate(workers):
            signal = .35 if i in (2,7) else .8
            tasks.append(dict(id=f'w{wave}_task{i}',title=f'Synthetic delivery task {wave+1}-{i+1}',owner=owner,
                dependencies=[] if wave==0 else [f'w0_task{i}',f'w0_task{(i+3)%9}'],
                effort=2,revision_effort=1,cost=2,value=8,signal=signal,
                success_probability=signal,deadline=5 if wave==0 else 10))
    records=[]
    for a in range(12):
        records.append(dict(id=f'workflow-member-{a}',name=f'Fictional member {a}',
            description='Coordinate team resources and tasks.' if a in (0,4,8) else 'Perform R&D delivery and specialist tasks.',
            background={'occupation':'Department manager' if a in (0,4,8) else 'Specialist employee'},
            source={'dataset':'Org ABM fictional workflow example','synthetic':True}))
    base=dict(agents=12,departments=3,rounds=12,tasks=tasks,budget=40,review_capacity=1,
        delegation_limit=2 if template=='delegated_teams' else 0,
        population={'records':records,'sampling':'ordered','seed':2026},
        structure={'template':'department_hierarchy'})
    vary = {'delegation_limit':[0,2]} if template=='authority_comparison' else {'review_capacity':[1,2]} if template=='review_capacity_comparison' else {}
    plan=dict(scenario='task_workflow',base=base,vary=vary,seeds=[7,8,9],
              decision={'provider':'rule','rule':'threshold'})
    if template=='memory_permissions':
        plan['seeds']=[7]
        base['rounds']=6
        base['review_capacity']=2
        all_members=[{'everyone':True}]
        def grant(audience,level='detail',start=1):
            return dict(audience=audience,level=level,from_round=start)
        base['memory']=dict(organization_id='example-org',max_items=20,max_chars=8000,trees=[
            dict(id='organization',scope='organization',nodes=[
                dict(id='overview',title='Organizational notices',summary='Organization-wide information directory.',grants=[grant(all_members)]),
                dict(id='demand',parent='overview',title='Customer demand report',summary='Recent customer demand faces downside risk.',
                    content='Fictional internal report: a major customer is considering delaying orders. This report has not been externally verified.',
                    grants=[grant([{'roles':['manager']}]),grant([{'roles':['employee']}],'summary',3),grant(all_members,'detail',5)]),
                dict(id='restricted',title='Restricted member records',summary='Access granted only to member 0.',content='Fictional board discussion record.',
                    grants=[grant([{'agents':[0]}])]),
                dict(id='restricted-detail',parent='restricted',title='Discussion attachment',summary='Inherits the parent node access restrictions.',
                    content='Fictional attachment: the proposal remains under discussion; no formal decision has been made.')]),
            dict(id='department-0',scope='department',owner=0,nodes=[
                dict(id='department-root',title='Department 0 experience',summary='Internal departmental task experience.',grants=[grant(all_members)]),
                dict(id='incident',parent='department-root',title='Previous delivery experience',summary='Communication delays occurred during the previous delivery.',
                    content='Fictional retrospective: an unreported task dependency caused a delay.',
                    grants=[grant([{'roles':['manager']}]),grant([{'roles':['employee']}],'summary')])]),
            dict(id='member-1',scope='personal',owner=1,nodes=[
                dict(id='private-note',title='Personal experience',summary='Personal record of work experience.',
                    content='Fictional personal record: an approval wait caused a missed delivery date.',grants=[grant(all_members)])])])
    return copy.deepcopy(plan)
