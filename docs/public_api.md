# Public experimental API (v0.6.0)

The SDK is a foundation for **configurable experiments on existing ABMs**. Public interfaces are experimental and versioned. Mesa 3.5.1 requires Python 3.12+. Use a project virtual environment:

```bash
python -m venv .venv
# Activate .venv with your platform's standard activation command.
python -m pip install -e ".[mesa,harness]"
python -m examples.run_mesa
```

## Use Jev or explicit rules for simulated decisions

Harness plans and operates experiments. Mesa/ABM computes outcomes. Jev or explicit rules supply simulated decisions. Model-written prose is never an experimental data source.

```python
from pathlib import Path
from orgabm.mesa_bridge import organization_adapter
from orgabm.engines import JevEngine
from orgabm.sdk import run_simulation

config = dict(agents=16, rounds=3, departments=4, seed=7, engine="jev")
# Set TYPESAFE_API_KEY in the process environment before launching.
calls = Path("runs/jev-example-calls")
calls.mkdir(parents=True, exist_ok=False)
engine = JevEngine(output=calls, cap_usd=0.10, batch_size=64, concurrency=4)
result = run_simulation(organization_adapter(config), engine,
                        rounds=3, seed=7, output="runs/jev-example-world")
```

In the NK scene, every agent receives a fresh decision each round. Questions are natively batched within a synchronous round; there is no cross-agent or cross-round probability cache. The task-workflow scene requests fresh decisions only for members with an eligible task or review, batching separately within each ordered stage. Client cost guards use the adapter's configured rate and returned usage, not a billing guarantee. The pinned endpoint/model and accounting assumptions are documented in the README.

`FunctionEngine` wraps local rules or offline decision functions. The existing `orgabm.deepseek.DeepSeekEngine` remains an optional Python-only comparator. It is not the default or a selectable MCP-plan provider. Comparative LLM-agent studies must be explicitly designed and evaluated separately from Harness usability.

## Jev through OpenRouter (Python SDK)

Set `OPENROUTER_API_KEY` in the process environment. The optional adapter uses the native Decisions API, with ready Choice questions in a single batch; it does not call Jev Router or chat completions.

```python
from orgabm.openrouter import OpenRouterJevEngine
from orgabm.sdk import run_simulation
from examples.llm_abm_cookbook.environments import NamingGame

engine = OpenRouterJevEngine('runs/openrouter-calls', cap_usd=0.01,
                             max_requests=20, batch_size=64, concurrency=1)
world = NamingGame(agents=24, options=list('QMXYFJPRCD'), seed=7)
result = run_simulation(world, engine, rounds=6, seed=7,
                        output='runs/openrouter-world')
```

The request pins `typesafe/jev-1.14`; returned dated snapshots are recorded and checked against that family. Reported cost is summed from `usage.cost`. Byte-based reservations and request counts provide client guards, not a provider billing cap. Errors stop the engine without automatic retries; saved logs omit headers and credentials. The adapter currently exposes Choice probabilities only. Its Python API can use custom environments or Mesa adapters, but the general CLI/MCP provider registry remains unchanged. See the [real two-cookbook trial](llm_abm_cookbook/openrouter_live_trial.md) and [official interface documentation](https://openrouter.ai/docs/guides/community/jev).

## Adapt your existing Mesa model

Supply a `MesaAdapter` with a `prepare(model, round_no)` callback returning `DecisionBatch(state, questions, agent_ids)`, and a `commit(model, round_no, actions, probabilities)` callback returning metrics. The model remains responsible for state, permissions and updates. Each question has `instructions` and `criteria` (action ID → description). IDs must be unique across rounds. Only the observation intended for that agent belongs in its question.

The generic `Environment` protocol supports other Python ABMs with the same three methods. A non-Mesa adapter does not import Mesa. `FunctionEngine` wraps a local rule or an offline decision function.

The original runner implements a synchronous round barrier. v0.5 adds `StagedEnvironment` / `run_staged_simulation` for ordered within-round decisions; see Task workflow below. Continuous-time scheduling still requires an explicit adapter. Do not change original timing merely to gain batching. Adapters are trusted local Python code, not sandboxed uploads. `describe()` should include parameters, source version and initial-state fingerprints; caller-supplied factories and initialization stay under the researcher's control.

## Experiment plan and Harness tools

`examples/foundation_plan.json` crosses department contact and approval threshold over paired seeds. `orgabm.plans.expand_plan(plan)` validates the plan and returns configurations and workload without contacting any provider. The registered service supports `nk_organization` and `task_workflow`, with scenario-specific rules or Jev. Custom models use the SDK until explicitly registered.

```bash
python -m orgabm.mcp_server --output-root runs/harness
```

This stdio server exposes seven tools: `describe_interface`, `preview_experiment`, `start_experiment`, `get_experiment`, `inspect_decision`, `preview_persona_assignment`, and `start_persona_assignment`. `start_experiment` returns a job ID promptly. Read its status later; the actual execution writes a fixed output folder with per-world events and metrics. One job runs at a time. No arbitrary filesystem path or shell command is accepted in tool arguments.

Load the insertion in `examples/deepseek-harness.entry.yml` into the active Harness profile patch, replacing its Python executable and working directory. `examples/harness-assistant-gateway.patch.yml` supplies a compatible gateway route using `HARNESS_API_KEY`, `HARNESS_BASE_URL` and `HARNESS_MODEL` from the launch environment. Those credentials drive the planning assistant independently of simulated agents. Keep the gateway base URL free of the `/chat/completions` suffix.

Do not forward the assistant's model key to the ABM server. For Jev, explicitly launch with `--allow-paid --max-requests 100 --max-cost-usd 0.10` and forward only `TYPESAFE_API_KEY` through the plugin's `env` field. The official plugin scrubs inherited key variables. The example references environment variables without storing secrets.

Jev plans use `{"provider":"jev","batch_size":64,"concurrency":4}`. The request allowance counts native batch HTTP calls, is reserved at job submission, and spans the server process. The cost guard spans worlds and jobs. A failed paid run stops subsequent paid work in the process because ambiguous failures may be billed. Restarting resets client limits. The assistant cannot increase them in plan arguments.

`get_experiment(experiment_id, wait_seconds=10)` waits at most 15 seconds for completion before returning, avoiding repeated model-driven polling. Simulation API usage excludes the research assistant's own calls and costs. For NK, `final` contains last-round metrics except cumulative earnings; `whole_run` separately summarizes all rounds. Workflow `final` contains cumulative task/financial outcomes, current queue/blockage counts and separately named cumulative event counters; see the workflow section for their meanings.

The official `@deepseek-ai/dsh` headless host was tested with a user-selected compatible gateway and free ABM rules, followed by a live Jev experiment with six thousand-agent worlds and 36,000 fresh decisions. See [the rule host trial](harness_trial.md) and [the Jev host trial](harness_jev_trial.md). Bounded waiting was exercised in the Jev trial; repeated polling still creates assistant overhead. Researchers may use any compatible MCP host.

```bash
python -m unittest discover -s tests -q
python tools/check_mcp.py
```

## Reusable starter plans

[`examples/templates/catalog.json`](../examples/templates/catalog.json) includes five NK plans: an open learning group, department silos, cross-department contacts, a contact comparison, and a contact-by-permission-threshold comparison. Each `plan` path is relative to the catalog directory. Only `runnable` entries have executable plan files; `design_only` organization families are a roadmap. Those five plans use the NK environment and free rules. v0.5 adds four task-workflow plans: functional hierarchy, delegated teams, authority comparison and review-capacity comparison. They are not five independent ABMs or validated representations of real organizations.

Load a plan file and pass its object to `preview_experiment` / `start_experiment`, or to the existing Python service. The catalog is metadata, not an accepted experiment plan. The workflow browser has a five-template picker. MCP accepts these explicit plans; a general cross-scenario discovery tool remains planned.

```python
import json
from pathlib import Path
from orgabm.plans import expand_plan

source = Path("examples/templates/plans/contact_comparison.json")
plan = json.loads(source.read_text(encoding="utf-8"))
plan["base"]["agents"] = 240
preview = expand_plan(plan)  # validates without running or calling any API
print(preview["worlds"], preview["decisions"])

# To execute with the existing service:
# from orgabm.mcp_server import ExperimentService
# service = ExperimentService(Path("runs/template-demo"))
# job = service.start(plan)
# service.jobs[job["id"]].result()  # local Python example only
# result = service.get(job["id"])
# service.pool.shutdown()
```

Set `decision` to `{"provider":"jev","batch_size":64,"concurrency":4}` only when using the separately enabled, budgeted Jev service. Best-member and conformity rules ignore advisory text and department identity. Their output is not evidence about responses to those cues. All NK plans retain the NK positive-improvement adoption rule, including when `approval_gain` is zero. Template metadata describes limitations; the plan JSON remains fully explicit and independently editable. General composition and automatic template-version provenance remain planned; retain a copy of the source template/catalog alongside your edited plan.

## Personas, populations and roles

v0.3.0 adds optional `population` and `structure` fields to the NK configuration. They work in CLI runs, the browser, `organization_adapter`, and MCP plan `base`/`vary`. Defaults remain `null`, preserving the original behavior without Personas. The browser's **People and organization** panel supports file imports, editable JSON records, structure selection, roster preview and configuration export. The example button loads `examples/persona_organization.json` (16 agents, four fictional profiles sampled with replacement, four departments, three rounds).

```python
from orgabm.personas import load_personas, import_personas

# Local subsets only: the adapter does not download a whole dataset.
people = load_personas("people.jsonl", preset="nemotron", limit=2000)
# Also supports preset="personahub" or "finepersonas".
# For Parquet/Hugging Face datasets, pass selected row dicts:
# people = import_personas(selected_rows, preset="nemotron",
#                          source={"revision": "your-pinned-dataset-revision"})

# User-defined CSV columns; canonical nested columns can contain JSON cells.
people = load_personas("employees.csv", field_map={
    "id": "person_id", "description": "bio",
    "background.occupation": "job", "traits.risk_preference": "risk"
})

population = {"records": people, "sampling": "without_replacement", "seed": 2026}
config = {"agents": 16, "departments": 4, "rounds": 3, "seed": 7,
          "population": population, "structure": {"template": "department_hierarchy"}}
```

Canonical records contain `id`, optional `name`, `description`, `background`, `traits`, `skills`, `goals`, and `source`. The four attribute/source groups are JSON objects; goals is a list of strings. At least one substantive attribute is required. Imports generate an ID if absent; explicit IDs must be unique in the source pool. Unknown canonical fields fail validation. Custom maps specify destination → source column, with dotted paths supported. CSV scalar cells remain strings: convert numeric fields explicitly if numeric types matter to a custom engine.

Sampling modes:

- `ordered`: exactly one record per agent, in the supplied order. Use this for researcher-controlled individual assignments.
- `without_replacement`: sample distinct records; the pool must be at least as large as the organization.
- `with_replacement`: reuse profile descriptions for distinct agents with independent runtime states. Optional nonnegative `weights` specify relative sampling weights, not exact quotas.

All modes preserve each record's joint attributes instead of independently resampling age, skill or experience. An explicit population seed fixes the same people across policy/structure conditions and world seeds. Without it, sampling follows the world seed. This is empirical-row sampling, not a learned demographic generator or proof of population representativeness. A repeated profile is not a second independent human observation. Current limits are 20,000 source records and 32,000 characters per record; the browser accepts requests up to 2 MB and raw file subsets up to 1 MB. CSV/JSONL loading is streamed to `limit`; JSON arrays are loaded into memory. Import first and place normalized records in plans; remote tools do not load arbitrary filesystem paths.

Built-in adapters were checked against the official [Nemotron schema](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA), [PersonaHub schema](https://huggingface.co/datasets/proj-persona/PersonaHub), and [FinePersonas schema](https://huggingface.co/datasets/argilla/FinePersonas-v0.1) on 2026-10-16. They attach source/permission metadata (CC-BY-4.0, CC-BY-NC-SA-4.0, and llama3 respectively). They do not bundle those datasets or supersede their licenses. Nemotron imports its professional/general description, selected background, skill description and career goals; unrelated hobby/sports fields are omitted. Users can override the mapping and supply a source revision. The bundled demonstration and test records are fictional schema fixtures, not sampled human data.

```bash
python -m orgabm import-personas --input subset.jsonl --preset personahub --output people.json --limit 1000
python -m orgabm run --config examples/persona_organization.json --output runs/persona-demo
```

`structure.template` supports `flat`, `department_hierarchy`, or `custom`. The hierarchy selects the lowest-index member of each seeded department as its manager, independently of Persona attributes; it does not infer leadership from demographics. Roles are defined separately:

```json
{
  "template": "department_hierarchy",
  "roles": {
    "employee": {"title": "Team member", "responsibilities": "Improve routine work", "allowed_actions": ["keep", "copy"]},
    "manager": {"title": "Department lead", "responsibilities": "Coordinate learning", "allowed_actions": ["keep", "explore", "copy"]}
  }
}
```

The capability `copy` expands to the three currently visible coworkers. `keep` must always be available. Permissions filter actual decision choices and are enforced again at execution. Best/conformity rules renormalize their preferred choices over permitted actions; if none remain, they keep the current process. They ignore descriptive Persona/role text. A role description does not automatically grant extra information, modify skill/productivity, or create manager approval decisions.

For `custom`, supply an `assignments` list with exactly one `{ "agent": 0, "department": 0, "role": "employee", "manager": null }` entry per agent. Departments/agents are zero-based, roles must exist, and manager references must be valid and acyclic. Each department needs at least four members for this NK scenario. Custom department membership controls actual contact sampling; reporting edges supply role context and visible colleague relationship cues. They do not add communication edges or an approval stage. Multi-parent matrix reporting, reorganization and role-dependent payoff functions remain future extensions.

Only the focal agent's Persona enters its question, without source metadata or the dataset ID. Coworkers expose department/role/relationship cues when identity is enabled, never their Persona or private histories. `anonymous=true` hides structured department and colleague-role/reporting cues, but preserves the focal agent's own role and Persona. It does not scrub identity information embedded in arbitrary user-written prose; use neutral profiles when that matters to an experiment.

Runs retain the full researcher-visible workforce, source metadata, separate population/organization SHA-256 hashes, and per-decision observations. Fixed profiles are separate from mutable positions, balances and recent outcomes. Jev uses these observations in fresh native batches each round. Tests verify input propagation with mocked API responses; no claim of live Persona sensitivity or human behavioral validity follows from that test.

## Position-conditioned Persona assignment

v0.4.0 adds a pre-simulation population-construction step in `orgabm.placement`.
Jev estimates **P(holds the target position | Persona, position description, organizational context)**. This is a separate binary question for each candidate/role pair, not a hiring recommendation or performance score. Probabilities across different roles are not normalized into one categorical distribution.

Two modes implement different sampling procedures:

- `pool`: score every candidate against every occupied role, then fill each role's slots by probability-weighted sampling without replacement. Zero-weight candidates cannot fill that role. This mode does not use the stream threshold.
- `stream`: randomly order candidates for a role, judge them in bounded batches, and accept candidates whose normalized occupancy probability is **greater than or equal to `threshold`**, default **0.5**. Below-threshold candidates are skipped for that role. Stop on quota completion, candidate exhaustion, or the evaluation limit. No extra Bernoulli draw follows the threshold check.

Roles and slot counts come from the existing organization configuration. The seed determines role order, slot order and candidate draws. A person cannot occupy two slots. An unassigned person rejected for one role may be assessed for a different role, but no candidate/role pair is queried twice. Batching can evaluate a tail of candidates after a role's quota would already have filled; these are explicitly recorded as `unused_batch_tail`. This changes the number of calls, not the candidate order used for selection.

```python
import json
from pathlib import Path
from orgabm.placement import preview_assignment, assign_personas, save_assignment
from orgabm.engines import JevEngine

job = json.loads(Path("examples/persona_assignment.json").read_text(encoding="utf-8"))
job["mode"] = "stream"    # or "pool"
job["threshold"] = 0.5    # inclusive; only used by stream
print(preview_assignment(job))  # no model requests

# For an explicitly initiated paid run; credentials stay in the process environment.
output = Path("runs/position-population")
output.mkdir(parents=True, exist_ok=False)
engine = JevEngine(output, cap_usd=0.10, batch_size=job["batch_size"], concurrency=1)
result = assign_personas(job, engine, output=output)
save_assignment(result, output)
```

Job fields: optional `scenario` (`nk_organization`, default, or `task_workflow`), `config` (including normalized `population.records`), `mode`, `threshold`, `seed`, `batch_size` (1–128), optional `max_evaluations` (up to 100,000 candidate/role pairs), and optional `context` (up to 4,000 characters). Candidate-pool `sampling`, `weights`, and `seed` do not drive this procedure: it uses the assignment seed and does not duplicate profiles. The pool must contain at least as many distinct records as organizational slots. Use the existing import adapters before constructing the job. Pool mode must have enough allowance to evaluate all pairs.

```bash
python -m orgabm assign-personas --job examples/persona_assignment.json --preview
# The example preview has at most 2 native requests. Larger jobs need their own allowance.
python -m orgabm assign-personas --job examples/persona_assignment.json --output runs/placement --max-requests 2 --max-cost-usd 0.10
python -m orgabm run --config runs/placement/config.json --output runs/placement-abm
```

Only a `complete` assignment produces a runnable `config.json`. It uses ordered Personas and an explicit custom structure to freeze who occupies which role, including department membership and reporting lines, across world seeds. An `incomplete` result reports vacancies and exports evidence only; the implementation never lowers the threshold or silently duplicates candidates to fill them. The algorithm is sequential and may fail to fill a role even when a different global assignment would succeed; recorded role order is part of the design.

`assignment.json` contains returned probabilities, normalized scores, selection outcomes, source-pool hash, seed, role order, allocations and usage. `assignment-events.jsonl` records progress; Jev's `calls.jsonl` retains raw requests/responses. Selected records carry assignment provenance under `source.orgabm_assignment`, which is excluded from simulated agents' observations. Population-preparation costs are separate from subsequent ABM decision costs. Probabilities and the threshold define a model-conditioned sample, not proof of unbiased sampling from the real job population; study threshold sensitivity when interpreting results.

Harness tools: `preview_persona_assignment(job)` and `start_persona_assignment(job)`. Poll the returned ID using `get_experiment`; `complete` returns an evidence-file path and a config-file path. The start tool uses the same server-side paid opt-in, native-request allowance, spending guard and single-job queue as simulations. It does not run ABM rounds. Unused reserved requests are released on successful or incomplete completion; ambiguous failures stop further paid work in that process.

The browser's **Position-conditioned population** panel loads a fictional 24-candidate example, previews and exports jobs, and imports completed configurations for roster inspection and free rule experiments. It does not invoke a paid provider. This first implementation uses Jev; embedding retrieval is not substituted for a role probability.

## Run provenance

SDK runs write `events.jsonl` (local questions, identities, returned probabilities, sampled actions and metrics) and `result.json` (configuration metadata, completed rounds, usage and SDK hash). A failed decision batch cannot commit the round. Exact state reconstruction additionally depends on the adapter's initialization and transition code; the organization example reuses its deterministic kernel. Researchers adapting other models must record their own source hash and environment dependencies.

Sources: [Mesa](https://mesa.readthedocs.io/stable/), [DeepSeek API](https://api-docs.deepseek.com/), [JSON output](https://api-docs.deepseek.com/guides/json_mode/), [Harness MCP plugin](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/mcp/mcp-client).


## Task workflow and executable organization design (v0.5)

`task_workflow` is a new simplified Mesa reference model inspired by the organizational-design problems in Puranam et al., VDT task/coordination modeling, and MOISE's explicit roles and obligations. It is not a faithful replication of VDT, SimVision or MOISE and does not depend on their code. The existing NK environment and its timing remain unchanged.

```bash
python -m orgabm experiment --plan examples/workflow_plan.json --preview
python -m orgabm experiment --plan examples/workflow_plan.json --output runs/workflow-demo
```

The default example has 12 members, 18 tasks, 12 ticks, two delegation limits and three paired seeds. `orgabm.templates.workflow_plan(name)` returns an editable plan. Names: `functional_hierarchy`, `delegated_teams`, `authority_comparison`, `review_capacity_comparison`. Browser entry: `/workflow`; free rules only. It previews the first condition's roster/task graph, starts the plan, shows all worlds and inspects stage decisions. CLI/MCP can run larger plans and Jev with separately configured credentials and explicit request/cost allowances. No live Jev validation of this scene has yet been performed.

### Configuration and mechanics

- Organization: reuse `population` and `structure`. Role capabilities are `work`, `request`, `revise`, `abandon`, `approve`, `reject`, `wait`; every role includes `wait`. NK role capabilities are different. Custom reporting edges must be acyclic. Task owners need `work`; tasks above the delegation limit need `request` and a reachable ancestor with `approve`.
- Tasks: required `id` and `owner`; optional `title`, `dependencies`, `effort` (default 2), `revision_effort` (1), `cost` (1), `value` (5), `signal` (.7), `success_probability` (.7), `deadline` (round horizon). IDs are unique; dependencies form a DAG. A completed predecessor unlocks dependents even if its stochastic payoff is zero. Rejected predecessors remain blocking. Task allocation is fixed; specialization is researcher-assigned, not inferred task competence.
- `delegation_limit` is a per-task cost limit, not a personal budget. At or below it, an employee may self-authorize work or request review. Above it, review is required. `authority_level=direct|top` routes to the nearest/highest approving ancestor; it does not implement sequential approval at every level.
- `review_capacity` (1–8) is decisions per manager per tick. `worker_capacity` (1–8) is progress units per employee per tick. Capacity measures differ and are not interchangeable; managers in the default hierarchy have no production tasks. Varying authority while holding capacities fixed does not equalize their utilization.
- `budget` is one shared, non-replenishing fund. Authorization charges the task cost once. Concurrent claims use a recorded-seed tie break; insufficient funds produce a `budget_denied` event rather than execution. An approval intention can thus fail to authorize. Direct claims are processed in the earlier employee stage, before manager claims.
- `individual_reward_weight` allocates that fraction of realized task value minus cost to its owner; the remainder is shared equally among all members, including managers. Ledger totals equal organizational net value. Time and revision work consume capacity but have no additional monetary wage cost in this version.
- Deadlines are measured, not automatic cancellation or penalties. `missed_deadlines` includes tasks unfinished (including rejected) after their due tick and tasks completed late. `signal` is the observed estimate; hidden `success_probability` determines stochastic payoff at completion. By default these are equal, so an experiment on judgment error should specify their relationship deliberately.

### Causal stages and information boundaries

Each tick proceeds as employee proposal → `review_0` … `review_N` → mechanical work/settlement. Workers choose one ready task (continuation/revision first, then earliest deadline and task ID). Managers see the oldest unprocessed dossier, with seeded tie-breaking. An application is reviewed at most once per tick; `wait` consumes a review opportunity. A request submitted this tick can be reviewed this tick. Approved work starts no earlier than the next tick; delegated work can start immediately. Dependencies completed during settlement unlock next tick.

Managers receive only the selected submitted dossier, their own Persona/earnings, the shared budget balance and declared policies. They do not receive other members' Personas, private provenance or hidden success probabilities. Reports are transmitted faithfully; strategic misreporting and informal communication are not implemented. Revision consumes the owner's work capacity, then requires a new request. It does not automatically improve task quality or its observed signal. `max_revisions` bounds returns. The local `threshold` rule uses signal ≥ .5 for new delegated work and approval; `permissive` accepts all. Neither rule uses Persona descriptions or earnings.

`orgabm.staged.StagedEnvironment` exposes `describe`, `stages`, `prepare_stage`, `advance_stage`, `finish_round`. The runner calls the decision provider only on nonempty batches. Each phase has a probability-validation barrier, fresh question IDs and seed-based action draws. Later phase questions are constructed after earlier phase actions. Jev can batch independent questions within a phase; never combine causally dependent phases. Preview counts are conservative upper bounds, not realized decisions. Experiment-service request reservations are conservative across the plan.

The transaction boundary is a stage. If a later decision fails, earlier stages remain committed and logged, the run stops, and the incomplete tick is not counted as completed. There is no silent rollback, retry or resume. Exact whole-round atomicity is not claimed.

### Evidence and limits

Each world writes `events.jsonl`, `result.json`, and `workflow-state.json`; provider requests/responses go in sibling `calls-N` directories. Events distinguish decisions from authorization, budget denial, revision work and task completion. Call `inspect_decision(..., stage="review_0")` for a manager; without a stage, ambiguous coordinates are rejected. Source hashes, expanded configuration and full researcher roster are retained. `final` has cumulative task/outcome/accounting measures, nested `cumulative` counts, and final-tick-only `execution_events`.

Tests verify permissions, dependency timing, capacity, resource conservation, privacy, phase ordering, failures, replay, assignment compatibility and actual MCP transport. Mock HTTP tests exercise the real Jev batch serializer. These are implementation checks, not human-behavior or policy-effect evidence. The reference model currently lacks committees, matrix reporting, communication costs/networks, endogenous task selection, task reassignment and dynamic reorganization.

References for the design: [Puranam et al. (2014)](https://strategy.univie.ac.at/fileadmin/user_upload/p_strategy/Corporate/Puranam_Alexy_Reitzig_AMR_2014.pdf), [VDT (Levitt, 2012)](https://www.jorgdesign.net/article/download/6345/6048/22916), [MOISE](https://github.com/moise-lang/moise). These motivate abstractions; implementation choices above are this project's explicit assumptions.

### Large single-organization fixtures (v0.5.1)

`examples.large_organization.large_organization_plan(agents=1000, rounds=6, mode="delegated", seed=7)` returns an ordinary registered plan with synthetic Personas, departments of ten and a sparse multilevel reporting tree. `mode="reviewed"` requires manager approval. Use a member count divisible by ten between 20 and 10,000. This is a runtime fixture with independent tasks and explicit homogeneous assumptions, not a representative corporate population. The returned plan can be edited or passed to the normal CLI/MCP service; it does not bypass workload limits. Browser bounds remain smaller.

```bash
python -m examples.large_organization --agents 1000 --output runs/large-plan.json
python -m orgabm experiment --plan runs/large-plan.json --preview
python -m orgabm experiment --plan runs/large-plan.json --output runs/large-experiment
```

Use new output paths under an existing directory. `WorkflowModel.earnings_for(agent)` reads the current balance without expanding the population; `earnings` and `snapshot()['earnings']` materialize an independent list for inspection. Shared reward updates have constant per-transaction cost. Mathematical allocation is unchanged, but floating-point addition order can differ from v0.5.0.

See [the scale benchmark](verification.md#v051-scale-benchmark) for measured scope and remaining bottlenecks. Multiple organizations and external market interfaces are documented design targets, not registered runnable scenarios.

## Organizational memory permissions (v0.6)

Optional `base.memory` in `task_workflow` defines a forest of organization, department and personal records. **Permissions are evaluated before constructing each local question.** The complete store and permission audit stay with the researcher. Jev receives only the selected member's bounded `memory.items` view, with fresh questions and the existing phase barriers.

```json
{
  "organization_id": "org-0",
  "max_items": 20,
  "max_chars": 8000,
  "trees": [{
    "id": "engineering",
    "scope": "department",
    "owner": 0,
    "nodes": [{
      "id": "incident",
      "title": "Delivery review",
      "summary": "A dependency was communicated late.",
      "content": "Researcher-authored detailed account of the incident.",
      "grants": [
        {"audience": [{"roles": ["manager"]}], "level": "detail"},
        {"audience": [{"roles": ["employee"]}], "level": "summary"}
      ]
    }]
  }]
}
```

This example gives department 0 managers full access and its employees a summary. Managers elsewhere receive neither. Use [`memory_permissions.json`](../examples/templates/plans/memory_permissions.json) for a complete runnable plan with organization, department and personal trees.

Permission semantics:

- A tree's `scope` records ownership. `owner` is a department index or personal member index, omitted/null for organization scope. Default tree `readers` are everyone in the current organization, the owning department, or the owner respectively. Explicit `readers` replace this default; include all intended audiences when granting a cross-department exception. Seniority alone grants no access.
- Audience lists use OR between selectors and AND between fields inside a selector. `{"departments":[0],"roles":["manager"]}` means managers in department 0. `[{"departments":[0]},{"agents":[4]}]` also permits explicitly named member 4. Values within one field use OR. `{"everyone":true}` must be explicit and standalone. Empty audience lists deny access. Agent/department references and role names must exist in the configured roster.
- Nodes have `id`, `parent` (within the same tree), `title`, `summary`, `content` and `grants`. Root nodes without grants are hidden. Missing/null child grants inherit their parent's level; `grants: []` explicitly hides a node and its descendants. The effective level is capped by every ancestor, so a child grant cannot bypass a restricted parent. Multiple matching grants choose the highest level within that cap.
- `summary` discloses only title and summary; `detail` additionally discloses content. Unauthorized titles, node IDs, descendants, counts and release schedules are not included in the member's view. Researcher-supplied summaries must be appropriate for their audience; there is no automatic redaction or LLM summarization.
- Optional `from_round` defaults to 1; `until_round` is absent/null by default. Both endpoints are inclusive. Time is an additional condition on access, not a substitute for permission. Expiry stops subsequent provision of the record; this does not model erasing information already learned.
- `max_items` (1–200, default 20) and `max_chars` (128–64,000, default 8,000) bound the JSON view. The character budget is not a token budget. Eligible items are selected in configured tree order and parent-first depth-first order. Whole items that do not fit are omitted; a descendant is not delivered without its parent. No hidden-node count is sent to the decision model.

`MemoryForest(policy, roster).observe(agent, round_no, organization_id=...)` returns `(view, audit)`. It resolves identity from its trusted roster, so the caller cannot grant a different role by adding role text to a question. An explicit different organization ID produces an empty view; omitting it uses this store's organization. Tree audience indexes avoid scanning all department/personal trees for every member. This is an SDK component; multiple organizations are not yet a registered simulation scenario.

Each committed stage records `effects.memory_visibility[agent]`: policy hash, eligible/delivered counts, omissions due to context limits, delivered node IDs/levels and an exact view hash. This separates **authorized access**, **actual inclusion in the input**, and the still-unmeasured **understanding or belief**. The existing `inspect_decision` MCP tool exposes the question and its stage audit. The browser has a free member/round permission preview for the first condition of the plan.

Current scope: configured records and read permissions, shared with the workflow runner. Active lookup, writing new memories, forwarding information, automatic event capture, semantic retrieval, learned forgetting and dynamic role changes remain future work. The standard `threshold` and `permissive` rules ignore memory text; their runs verify access and mechanics only. Memory permissions apply to `memory.items`; task dossiers, shared budget and other existing observation fields retain their declared visibility. Experiments must consistently place restricted facts in the protected channel instead of duplicating them in public task descriptions. Records can represent reports or beliefs and do not automatically modify hidden task success probabilities.

## Bounded OpenRouter retries and exact-event recovery

New SDK callers can explicitly select `orgabm.openrouter_reliable.ReliableOpenRouterJevEngine`. It implements the same `decide(state, questions)` contract and native Choice batching as `OpenRouterJevEngine`. The original strict adapter remains available, preserving the source versions used in earlier evidence. These settings do not change the separate Typesafe adapter or the general plan/MCP providers.

```python
from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine

engine = ReliableOpenRouterJevEngine(
    "runs/my-run/calls",  # New output path; OPENROUTER_API_KEY in the environment.
    cap_usd=3, max_requests=6000, batch_size=32, concurrency=2,
    max_retries=3, timeout=90,
)
```

The default is at most three retries after the initial attempt. Backoff is exponential with jitter. `Retry-After` is respected; a delay exceeding `max_retry_delay` (default 60 seconds) stops the request instead of retrying too soon. Transient connection/read failures and HTTP 408, 429, 500, 502, 503 and 504 are retryable. A 402 is retryable only when its metadata identifies `openrouter_in_flight_budget` and a `Retry-After` is present. Authentication, ordinary credit exhaustion, invalid parameters, certificate verification and invalid model results stop. The adapter never substitutes probabilities after a failure.

All attempts share the request and client cost guards. Failed attempts retain conservative reservations because their billing can be uncertain; reported successful-response cost is a separate measurement. `retry_events.jsonl` records a batch hash, attempt number, status, error class and wait decision, without credentials. Provider-side idempotency or exactly-once billing is not claimed. See [OpenRouter's error semantics](https://openrouter.ai/docs/api_reference/errors-and-debugging).

The [organizational-conventions cookbook](organizational_conventions/README.md) adds a dedicated `resume` command. It verifies frozen source hashes and exact local inputs, reconstructs completed periods from recorded probabilities, and restores successful responses for the same original event IDs from the call journal. Only missing decisions are submitted. A reused ID with different input stops recovery. This is checkpoint restoration for the original events; it does not reuse probabilities for new people or future states. The helper preserves interrupted traces and shares the original experiment's allowances across recovery attempts. Generic stage-level or distributed recovery remains a development target.

## Large-organization convention extension

The same [cookbook](organizational_conventions/README.md) combines the naming-game interaction mechanism with existing `build_workforce`, reporting relations and `MemoryForest.observe` permissions. Its public `Environment` implements `describe`, `prepare` and `advance`, then runs through `orgabm.sdk.run_simulation` with rules or a decision model. It compares minority placement at employee/manager positions and absent/peer/authorized-official department announcements in a 1,000-member organization.

Independent, disjoint pairs are batched within each period and settled after all valid probabilities arrive. A failed decision period does not advance the world. This synchronous scheduling is an explicit extension of the source paper's asynchronous protocol. Announcements are advisory, with verified publishing rights and department readers; they do not force the chosen action. Different experimental worlds do not interact. The scene is available through the Python SDK and its dedicated CLI, not yet the browser or generic MCP scenario registry.
