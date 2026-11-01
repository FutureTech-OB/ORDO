"""Full published scale, source initialization, declared Figure-2 flood calendar."""
from statistics import mean, stdev

from .environment import FloodEnvironment, PAPER_ID


def build_cases():
    return [dict(id=f'wrr_flood_r{i:02d}', paper_id=PAPER_ID,
                 environment=FloodEnvironment(20261030+i), rounds=10,
                 seed=20261030+i,
                 condition=dict(replicate=i, agents=100, years=10, flood_years=[3, 4, 9],
                                initialization='source_generator_new_seed',
                                source_paper_initialization_discrepancy=True))
            for i in range(50)]


def analyze(results):
    """Compare directions without treating successful execution as replication."""
    if len(results) != 50:
        raise ValueError('The declared 50-replicate protocol was not completed.')
    rows = []
    states = ['Do Nothing', 'Only Flood Insurance', 'Only House Elevation',
              'Both Flood Insurance and House Elevation', 'Relocate']
    for year in range(1, 11):
        counts = [r['result']['metrics'][year-1]['adaptation_counts'] for r in results]
        rows.append(dict(year=year, state_shares={s:dict(
            mean=mean(c[s]/100 for c in counts),
            sd=stdev(c[s]/100 for c in counts),
            minimum=min(c[s]/100 for c in counts), maximum=max(c[s]/100 for c in counts))
            for s in states}))
    inactive = [r['state_shares']['Do Nothing']['mean'] for r in rows]
    elevation = [r['state_shares']['Only House Elevation']['mean'] for r in rows]
    relocation = [r['state_shares']['Relocate']['mean'] for r in rows]
    early = (inactive[0]+inactive[1])/2
    return dict(protocol='100 households x 10 years x 50 replicates; source initialization; Figure-2 flood years 3/4/9',
                exact_paper_inputs=False, initialization_discrepancy=True,
                fresh_decisions=sum(r['result']['decisions'] for r in results),
                trajectories=rows,
                directional_comparisons=[
                    dict(paper_pattern='About 90% do nothing in Years 1-2.',
                         jev_mean_year1_year2_do_nothing=early,
                         absolute_difference_from_reported_approximate_90_percent=abs(early-.9),
                         judgement='Descriptive distance, not a prespecified equivalence test.'),
                    dict(paper_pattern='House elevation only increases after first flood.',
                         jev_year3_minus_year2=elevation[2]-elevation[1],
                         direction_supported=elevation[2]>elevation[1]),
                    dict(paper_pattern='Inaction remains dominant while adaptation is gradual.',
                         jev_year10_do_nothing=inactive[-1],
                         jev_end_minus_initial_do_nothing=inactive[-1]-inactive[0],
                         direction_supported=(inactive[-1]>.5 and inactive[-1]<inactive[0])),
                    dict(paper_pattern='Relocation emerges with later flood experience.',
                         jev_year2_relocation=relocation[1], jev_year4_relocation=relocation[3],
                         jev_year10_relocation=relocation[-1],
                         direction_supported=relocation[3]>relocation[1])],
                conclusion='Source-defined full-scale LLM-engine substitution. Exact paper-behavior replication is not established: author profiles/seeds are absent, source and article initialization differ, and numerical Figure-2 reference tables are not in the repository.',
                not_tested=['Gemma/Jev human fidelity', 'LLM-generated reasoning or sentiment',
                            'Traditional ABM contrast', 'Sensitivity figures 5/6/7',
                            'Author 50-run individual trajectories or initial population equality'])
