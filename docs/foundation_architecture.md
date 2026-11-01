# ORDO architecture and development roadmap

ORDO is organizational research infrastructure built on existing agent-based modeling. Its first ABM integration uses Mesa's Model, Agent/AgentSet and DataCollector. Environment adapters retain world dynamics; replaceable engines supply decisions; experiment services coordinate plans, execution and evidence. The current proposal and technical appendix describe the release, while this document retains the architecture and development directions confirmed during October 2026.

## Organizational modeling

Agents combine four separately configured components: a stable Persona, an organizational position and permissions, evolving state, and private memory. Persona import supports three public-data formats and custom records, with source hashes and reproducible population sampling. Education, experience, expertise, preferences and goals are optional fields. A position change alters duties and authority without silently rewriting personal background.

The population-construction stage estimates the probability that a candidate occupies a specified position given the Persona, duties and organization. Full-pool assignment evaluates candidate–position combinations and samples without replacement by score. Streaming assignment draws candidates and accepts those at or above a threshold, default 0.5, until quotas or limits are reached. Vacancies remain explicit; candidates are not duplicated and thresholds do not automatically relax. Assignment is sequential rather than globally optimized. Probabilities, position order, seeds, costs and resulting reporting relationships are saved. The Python/CLI, browser and MCP interfaces share this implementation.

Organizational structure distinguishes membership, reporting, information contacts, decision authority, task dependencies and payoff responsibility. The NK learning environment supports local contacts and adoption thresholds. The task_workflow environment supports a task DAG, fixed owners, acyclic reporting, employee authority limits, nearest or highest eligible reviewer, FIFO approval queues, per-manager review slots, revision and waiting, execution capacity, shared budgets and individual/shared returns. Manager inputs contain submitted reports and their own permitted information. Proposals, authorizations and executed actions have distinct records.

The staged environment processes employee proposals, managerial reviews and execution/settlement in order. Independent decisions within a stage can be batched; later stages observe earlier committed outcomes. A manager slot is an explicit decision event. Each new relevant event receives a fresh judgment. Existing synchronous NK execution remains supported. Current review routes select one approving superior; committees, sequential multilevel approval, matrix authority, endogenous reporting and reorganization are development targets.

## Memory and information asymmetry

Organization, department and personal memory trees separate ownership from reading permissions. Department trees default to their department, personal trees to their owner. A managerial title does not automatically grant access to all private records. Nodes can restrict summaries and full text by position, department or member; ancestor restrictions apply to descendants. Unauthorized titles and content are excluded before context budgets are applied. Optional release windows add timing to access rules.

Each stage records the permission version, nodes and detail levels actually supplied, view hashes and capacity omissions. Researcher-configured records support controlled information asymmetry. Active retrieval, writing, forwarding, automatic summarization and event-generated memories remain development targets. Access and actual input exposure are implemented; comprehension and belief require separate behavioral measurement.

## Public interfaces and execution

Environment implementations expose describe(), prepare(round) and advance(round, actions, probabilities). MesaAdapter wraps model-specific preparation and commit callbacks. StagedEnvironment adds ordered decision stages. Engines expose decide(state, questions) and usage(). JSON plans define base, vary, seeds and decision. The MCP service currently registers nk_organization and task_workflow and offers seven research tools, including population construction and event inspection. The browser contains organizational-learning and task-workflow workbenches.

The adapter declares local information, feasible actions, source timing and state updates. Model substitution preserves that contract. Native Jev batching groups ready questions from independent agents or worlds, with barriers at causal dependencies. Every person/event is judged anew; probabilities are not shared across members or states. Rules and optional chat-model adapters enable explicit comparisons. Credentials are configured separately from saved plans.

The single-organization scale work removes population-wide per-transaction payoff updates through individual and shared per-person accumulators. Tests check balances, observations, budgets and aggregate conservation. Independent-process benchmarks retain complete plans, task states and evidence. Thousand- and ten-thousand-member rule workloads complete six rounds; live model throughput is measured separately. Sparse reporting and task graphs, evidence size, memory, batching and service limits are distinct scale dimensions. Hundred-thousand-member operation is a later target.

## Research assistance and non-code input

DeepSeek Harness is the first integrated research assistant. Researchers can describe populations, departments, reporting, information permissions, environments and policies in natural language, tables or forms. The assistant turns these inputs into supported structured plans, previews workload, starts simulations, modifies parameters and inspects executed events. Existing tools accept registered mechanisms; unsupported descriptions require an environment implementation.

Harness uses the researcher's compatible model/API credentials and communicates through standard MCP. Jev credentials belong to the simulation engine. Numerical results come from executed environment transitions and analysis, while the assistant helps plan and explain them. The official Harness plugin architecture supports stdio and Streamable HTTP. Recorded trials cover both free-rule operation and 36,000 fresh Jev decisions in six 1,000-member worlds.

## Reusable templates

Population descriptions, organizational structures, tasks/environments, policies and experiment grids are separate configuration concerns. Templates retain IDs, versions, sources, assumptions, editable parameters, required capabilities, timing and metrics. Five NK and five workflow plans provide editable starting points. Current plans are complete snapshots; a general composition and capability-discovery system is planned.

Functional hierarchies, delegated teams and memory-permission examples are executable. Divisions with separate accounts, matrix arrangements, committees, cross-functional projects and interorganizational networks require additional environmental mechanisms. Templates specify mechanisms rather than presumed outcomes such as conservative hierarchies or obedient employees. AgentSociety's profile/block separation, registered modules and research tools inform the planned catalog and discovery interfaces.

## Multiple organizations and external environments

The next scope connects multiple organizations in a shared market. Organizations can act as customers or suppliers while containing departments, teams and individuals. Entity composition is independent of transaction role: the same organization may buy, sell and partner in different relationships. A proposed containment tree remains separate from reporting, collaboration and transaction graphs.

The world maintains organization IDs, a shared clock, market conditions and distinct accounts. Market adapters define exogenous shocks, public/private signals, feasible boundary actions, allocation and settlement. Organization adapters turn internal authorized activity into procurement, production, hiring or offers. A proposed phase sequence is exogenous updates and signals, internal decisions, production and market actions, common settlement, and state updates. Priority rules are explicit rather than an accidental effect of traversal order.

The first proposed market example uses competing firms, finite orders and delivery deadlines, with fixed personnel and one product. Internal authorization and capacity determine fulfillment; settlement affects cash and later resources. Consumer demand may be statistical or represented by explicit agents. Exogenous prices and prices formed through competition are separate model choices. Organizational funds, delegated spending limits, personal returns and contract liabilities have explicit boundaries to avoid double counting.

A client–supplier example can connect a requesting department, procurement and finance approvals, an authorized organizational order, supplier task allocation, delivery, acceptance and settlement. Organizational boundary actions originate from internal roles and authorization. General recursive organization objects and shared-market execution remain development targets.

## Policies and environments

Policies modify local information, feasible actions, actual incentives or state transitions. Guidance, binding rules, incentives and external shocks are declared separately, with targets, triggers, duration and changed variables. The environment applies them at its stated phase and records execution. Existing guidance, penalty, approval_gain and intervention_round fields are scenario-specific examples. General demand shocks, taxes, subsidies, policy withdrawal and conditional triggers require new mechanisms.

Independent variation of contact structure and authority can examine adaptation while holding populations, resources and review capacity fixed or explicitly recorded. Market feedback should eventually connect strategy, internal coordination, delivery, revenue and future resources. The present release's completed organizational convention extension demonstrates roles, reporting and departmental publishing permissions; it does not require a market model.

## Human-data feedback and reusable research accumulation

The planned feedback cycle imports observed behavior, aligns tasks and available information, calibrates populations or engines, runs interactive simulations, evaluates held-out behavior and recommends further evidence. Interfaces should record participant/group, role, condition, feasible choices, observed action and feedback, with provenance and observation level. Aggregate data support aggregate evaluation; individual prediction needs corresponding individual records.

Fixed APIs can use external probability calibration; trainable engines can use a separate training adapter. Jev fine-tuning is not assumed. Centaur motivates learning from observed human choices, with development and final evaluation kept separate. Population fidelity, single-choice prediction and autonomous interaction trajectories are different evaluation targets.

The proposed public workbench combines a Python core, web interface, plans, templates, tutorials and replication records. Expected Parrot informs the project–population–environment–design–run–evidence workflow. Researchers supply credentials for external services; local rules require no model account. Current source is published in the ORDO repository. Persistent projects, a general editor, shared catalogs and a hosted service are future delivery options. The operating form is undecided.

## Scientific and engineering evaluation

Research questions examine how information, authority and organizational arrangement shape collective outcomes across decision policies and scales. Record proposed choices, institutional execution, local inputs, probabilities and outcomes. Use paired seeds and independently repeated worlds. Architecture benchmarks compare message routing on the same allowed interaction graph; experiments that change the graph are organizational interventions.

Assistant evaluation measures faithful conversion of intended models, tool execution and numerical traceability. Simulation evaluation measures local behavior, emergent dynamics, sensitivity, runtime and cost. Saved-probability replay checks recorded execution; independent fresh runs measure behavioral replication. Source protocols and organizational extensions are reported separately.

## Related interfaces and records

- [Public API](public_api.md)
- [Related systems and literature](related_work.md)
- [Organizational cookbook](cookbook/README.md)
- [Harness trial](harness_trial.md)
- [Harness–Jev trial](harness_jev_trial.md)
- [Scale and reuse evidence](scale_and_reuse_evidence.md)
