# Cycle 17-02: Best Practices for Gap-Driven, State-File, Schema-Prioritized Agents

**Date:** 2026-02-12
**Type:** Research (no code, no planning)
**Scope:** Gap-driven intelligence, state-file-driven agents, schema-based prioritization, delta-only output

---

## TL;DR — What Production Systems Do That Naive Ones Miss

| Dimension | Naive Implementation | Production System |
|-----------|---------------------|-------------------|
| Gap detection | Re-scan everything each cycle | Maintain explicit (Evidence, Gap) tuples; only work on gaps |
| State loading | Read flat JSON, process top-to-bottom | Schema-validated state with dependency DAGs and topological sort |
| Prioritization | Static priority field or FIFO | RICE/WSJF scoring + aging + dependency-aware ordering |
| Output | Regenerate full report every run | Delta-only: compare before/after state, emit only what changed |
| Partial completion | Binary done/not-done | Track sub-task progress, checkpoint, resume from last good state |
| Concurrency | No locking; last-write-wins | Optimistic locking with version fields; conflict detection |
| Schema evolution | Break when fields added | Semantic versioning, backward-compatible optional fields |
| Failure handling | Crash or silently skip | Circuit breakers, retry with backoff, graceful degradation |
| Observability | Print statements | State transition logs, reasoning traces, structured audit trail |
| Memory | Goldfish — forget everything between runs | Distill operational intelligence, not narrative summaries |

---

## 1. Gap-Driven Intelligence Systems

### Core Concept

A gap-driven system explicitly models the **delta between current state and desired state**, then uses that delta to select actions. The agent asks: "What's missing?" — not "What should I do?"

### Key Patterns

**Evidence-Gap State Abstraction (MemR3)**
- Maintain a tuple `(E, G)` where E = established evidence, G = remaining gaps
- Gaps drive query refinement — the agent knows what questions to ask next
- Stopping condition: G is empty or below a threshold
- Source: [MemR3 — arxiv.org/pdf/2512.20237](https://arxiv.org/pdf/2512.20237)

**Classical AI Planning Foundations**
- **STRIPS**: Actions have preconditions (gaps) and effects (gap closers). Planner identifies which preconditions aren't satisfied yet
- **GPS (General Problem Solver)**: Means-ends analysis — recursively reduce differences between initial and goal state
- **HTN**: Hierarchical decomposition tracks gaps at multiple abstraction levels

**Finite State Machines for Workflow Control**
- StateFlow models LLM workflows as FSMs where each state = a phase of task completion
- Transitions occur when preconditions/gaps are satisfied
- Separates deterministic control flow from non-deterministic LLM reasoning
- Source: [StateFlow — arxiv.org/html/2403.11322v1](https://arxiv.org/html/2403.11322v1)

**Judge-Planner Verification Loop**
- A judge LLM critiques proposed plans for missing steps, contradictions, irrelevant actions
- 96.5% of plans converge within 3 iterations; 62% corrected after first pass
- Prevents both redundant work (removing unnecessary steps) and missing work (identifying gaps)
- Source: [arxiv.org/abs/2509.02761](https://arxiv.org/abs/2509.02761)

### Critical Failure Modes

| Failure | Description | Mitigation |
|---------|-------------|------------|
| Hallucinated gaps | Agent invents work that doesn't need doing | Ground gap detection in structured state, not LLM reasoning |
| Missed gaps | Agent skips critical missing pieces | Explicit dependency graphs; judge-planner verification |
| Re-doing completed work | No memory of what was already done | Persistent state with completion markers; idempotency checks |
| Context window overflow | Early gaps forgotten as context fills | Distillation over summarization; preserve operational state |
| Plan drift | Execution errors degrade reasoning over time | Separate state tracking from semantic reasoning |

### Critical Insight

> **79% of multi-agent failures originate from specification and coordination issues, not technical implementation.** Gap detection fails when agents lack shared understanding of goals and state.
> — [arxiv.org/pdf/2503.13657](https://arxiv.org/pdf/2503.13657)

---

## 2. State-File-Driven LLM Agents

### Core Concept

Agent loads structured external state (JSON/YAML/TOML) to determine what to do next. The state file is the source of truth — not the agent's memory.

### Three Agent Archetypes

| Archetype | How It Works | Best For |
|-----------|-------------|----------|
| **Checklist-driven** | Work through items sequentially or by priority; mark done | Batch processing, migrations, structured workflows |
| **Event-driven** | React to external events; state transitions triggered by signals | Real-time systems, distributed workflows, high concurrency |
| **State machine** | FSM with explicit transitions; current state + input = next state | Complex multi-step processes, compliance, deterministic control |

**2026 best practice: Hybrid approach** — match architecture to use case. Give the system the smallest amount of freedom that still delivers the outcome.

### Schema Design: Essential Fields

```yaml
# Minimum viable state schema
version: "1.0"          # Schema version for evolution
items:
  - id: "unique-id"
    status: "pending"    # pending | in_progress | completed | blocked
    priority: 2          # Numeric or RICE score
    created_at: "..."
    updated_at: "..."
    blocks: []           # IDs this item blocks
    blocked_by: []       # IDs that must complete first
    sub_tasks:           # For partial completion tracking
      - id: "sub-1"
        status: "completed"
      - id: "sub-2"
        status: "pending"
    metadata: {}         # Extension point for future fields
```

### Lessons from Infrastructure-as-Code

**Terraform State Patterns**
- `.tfstate` as single source of truth for all managed resources
- S3 backend + DynamoDB locking for concurrent access
- `terraform plan` output: visual delta with `+` (create), `~` (change), `-` (destroy) indicators
- Summary: "Plan: X to add, Y to change, Z to destroy"
- Never expose full state (contains sensitive data); retrieve only needed parameters

**Ansible Facts Pattern**
- Facts = stateful, truthful information gathered from infrastructure
- Idempotent: running same playbook multiple times = same result
- Agentless: state files readable without the agent running
- Lesson: **design state files to be human-readable and self-describing**

### Concurrency and Consistency

**Optimistic Locking (preferred for most agent use cases)**
- Include `version` field in every state item
- On update: check if version matches what you started with
- If mismatch: reject, notify, offer retry/merge/discard
- Low overhead; works well when conflicts are rare

**Pessimistic Locking (for critical operations)**
- Grab exclusive lock before proceeding
- Include lock expiration and owner tracking
- Admin dashboard to release stale locks
- Higher overhead but prevents all conflicts

**Production pattern: S3 + DynamoDB** — proven at scale for distributed state locking.

### Schema Evolution

- **Always include a version field** in state files
- **Make new fields optional** with defaults — ensures backward compatibility
- Use semantic versioning: MAJOR (breaking), MINOR (new features), PATCH (fixes)
- Validate schemas before loading — use JSON Schema or similar
- Never store secrets in state files — use environment variables or secret managers

### Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Giant monolithic state file | Bottleneck, slow reads, merge conflicts | Partition by domain/module |
| Hardcoded file paths | Breaks across environments | Environment variables, discovery |
| No version tracking | Breaks on schema changes | Always version state schemas |
| State drift | In-memory state diverges from file | Regular checkpointing |
| Missing idempotency | Different results on re-run | Design transitions to be idempotent |
| Secrets in state files | Security risk | External secret management |

---

## 3. Schema-Driven Prioritization

### Core Concept

Agent reads a structured schema that describes "what good looks like" and works toward it, selecting highest-impact work first while respecting dependencies.

### Scoring Mechanisms

**RICE Score** = (Reach x Impact x Confidence) / Effort
- Best for user-focused product decisions
- Impact scale: 3 (massive) to 0.25 (minimal)
- Source: [productplan.com/glossary/rice-scoring-model](https://www.productplan.com/glossary/rice-scoring-model/)

**WSJF** = (User-Business Value + Time Criticality + Risk Reduction) / Job Duration
- Best for deadline-driven, portfolio-level decisions
- Source: [6sigma.us/work-measurement/weighted-shortest-job-first-wsjf](https://www.6sigma.us/work-measurement/weighted-shortest-job-first-wsjf/)

### Dependency-Aware Ordering

**Topological Sort on DAG**
- Model tasks as directed acyclic graph
- Process nodes with zero in-degree first (Kahn's algorithm)
- Detect cycles to prevent deadlocks
- Used by: Apache Airflow, Gradle, Make, Bazel

**Critical rule:**
> Don't rank a task as low-priority if ten other tasks depend on it.

### Anti-Starvation Mechanisms

| Mechanism | How It Works |
|-----------|-------------|
| **Aging** | Lower-priority tasks gradually increase priority over time |
| **Weighted Fair Queuing** | Round-robin across priority tiers with weights |
| **Deadline Lanes** | Separate queues by time criticality |
| **SRTF** | Prioritize tasks closest to completion |

### Handling Partial Completion

**The problem:** Claude 3.5 fully completes only 24% of assigned tasks (34% with partial credit). Source: [metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/)

**Solutions:**
1. **Checkpointing** — save progress at key points; resume from last good state
2. **Sub-task tracking** — 3 of 5 sub-tasks done = 60%, not "incomplete"
3. **Pause/resume** — agents can be interrupted for progress reports, then continue
4. **Time travel** — save, examine, and branch from prior execution states (LangGraph)
5. **Workflow decomposition** — break into small schema-driven chunks, not one big prompt

### What Production Systems Add

| Production Feature | Why It Matters |
|-------------------|----------------|
| Context engineering | Every token competes for attention; prune aggressively |
| Graceful degradation | Fallback mechanisms when AI fails (no dead ends) |
| Human oversight | Confidence thresholds trigger escalation |
| Observability | Execution tracing, structured logging, automated evaluation |
| Strong schemas | Typed fields, explicit relationships, machine-parsable descriptions |
| Task decomposition | Small bounded tasks > one large prompt |

---

## 4. Delta-Only Output Patterns

### Core Concept

Report only what changed — not everything. Compare before-state to after-state and emit meaningful, structured deltas.

### Proven Patterns

**Terraform-Style Plan Output**
- Compare desired configuration with current state
- Visual indicators: `+` (create), `~` (change), `-` (destroy)
- Summary: "Plan: X to add, Y to change, Z to destroy"
- JSON output for programmatic consumption
- Best model for agent delta reporting

**Event Sourcing + CQRS**
- Persist state as sequence of state-changing events
- Append-only: each change = new event
- Separate read (query) and write (command) paths
- Provides detailed audit trail: what happened, when, and why
- Can reconstruct state at any point in time

**Streaming Delta Delivery**
- Stream tokens/chunks as generated rather than waiting for full response
- JSON Patch format for real-time state updates
- Enables optimistic UI updates before tool execution completes
- Source: [AG-UI State Management — learn.microsoft.com](https://learn.microsoft.com/en-us/agent-framework/integrations/ag-ui/state-management)

**Incremental Checkpointing**
- Store only deltas since last checkpoint (not full snapshots)
- Delta State CRDTs: disseminate only recently applied changes
- Append-only changelogs continuously uploaded to durable storage
- Source: [Generic Log-Based Incremental Checkpoint — ververica.com](https://www.ververica.com/blog/generic-log-based-incremental-checkpoint)

**Semantic Caching**
- Detect semantically similar queries via embeddings
- Return cached response instead of regenerating
- Prevents duplicate delta reports for equivalent requests

### The Idempotency Challenge

> True idempotency implies strict invariance under repeated application — something at odds with stochastic LLM systems.

**Production approach: Approximate idempotency**
- Retry policies with exponential backoff
- Circuit breaker patterns to prevent cascading failures
- Checkpointing for long-running workflows
- Deduplication via version tracking and execution IDs
- Source: [Can AI Agents Exhibit Idempotency? — medium.com](https://medium.com/autonomous-agents/can-ai-agents-exhibit-idempotency-2cea33cc681c)

### Building Meaningful Change Narratives

| Pattern | Description |
|---------|-------------|
| **Reasoning traces** | Log of decisions, tool calls, reasoning steps (Amazon Bedrock, ReAct) |
| **Episodic memory** | Store goal, reasoning, actions, outcomes, reflections per episode |
| **Memory consolidation** | Periodically compress episodic events into long-term summaries |
| **Structured output via JSON Schema** | Enforce consistent delta format with constrained decoding |
| **Context compaction** | Monitor context size; prune/summarize between agent steps |

### Failure Modes

| Failure | Description | Fix |
|---------|-------------|-----|
| Report everything as changed | No before/after comparison | Explicit state snapshots + diff |
| Miss actual changes | Drift detection gaps | Real-time monitoring, model versioning |
| Inconsistent delta format | Output varies unpredictably | JSON Schema validation, Agent SOPs |
| Oscillatory corrections | Agents "fix" each other in loops | Convergence criteria, trust scoring |
| Duplicate deltas | Same change reported twice | Deduplication via execution IDs, version checks |

---

## 5. Cross-Cutting Insights

### The Architecture Gap Is the Real Problem

> The gap isn't intelligence — it's architecture. Focus is shifting from building smarter agents to building trustworthy, deployable, governable systems.
> — [Deloitte Insights, 2026](https://www.deloitte.com/us/en/insights/topics/technology-management/tech-trends/2026/agentic-ai-strategy.html)

### Separate Deterministic Control from Non-Deterministic Reasoning

This single principle eliminates 44.2% of system design issues and 23.5% of task verification failures. Use FSMs, DAGs, or graph-based orchestration for control flow. Use the LLM only for reasoning within each controlled step.

### Memory: Distillation Over Summarization

The "goldfish problem" — traditional summarization discards exactly the operational intelligence needed to track gaps. Solution: distill "Current Status & Blockers" rather than narrative.

Multi-session memory retention ceiling is ~37%. Most compression strategies fundamentally lose critical context. Source: [arxiv.org/pdf/2511.13998](https://arxiv.org/pdf/2511.13998)

### Context Engineering Is Non-Negotiable

> Every token you add to the context window competes for the model's attention — stuffing 100K tokens of history degrades the model's ability to reason about what actually matters.
> — [LangChain, Context Engineering for Agents](https://blog.langchain.com/context-engineering-for-agents/)

Strategies:
- **Pruning**: Remove unused context automatically
- **Reordering**: Restructure by importance
- **Hierarchical pruning**: Different rules for different context types
- **Multi-agent isolation**: Split context across sub-agents

### Production Requires Four Building Blocks

1. **Reliable LLMs** for reasoning/generation
2. **Agent frameworks** for orchestration
3. **Systematic evaluations** for quality assurance
4. **Memory systems** for persistent intelligence

---

## 6. Key Sources

### Gap-Driven Intelligence
- [MemR3: Memory Retrieval via Reflective Reasoning](https://arxiv.org/pdf/2512.20237)
- [GAP: Graph-Based Agent Planning](https://arxiv.org/abs/2510.25320)
- [StateFlow: State-Driven Workflows](https://arxiv.org/html/2403.11322v1)
- [Plan Verification for LLM-Based Agents](https://arxiv.org/abs/2509.02761)
- [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/pdf/2503.13657)
- [ReAct: Synergizing Reasoning and Acting](https://react-lm.github.io/)

### State-File Patterns
- [Agent Memory: Building Persistence — Dust.tt](https://dust.tt/blog/agent-memory-building-persistence-into-ai-collaboration)
- [How We Solved the Agent Memory Problem — Sanity](https://www.sanity.io/blog/how-we-solved-the-agent-memory-problem)
- [The Agent Deployment Gap — ZenML](https://www.zenml.io/blog/the-agent-deployment-gap-why-your-llm-loop-isnt-production-ready-and-what-to-do-about-it)
- [State/Session Management — AgentScope](https://doc.agentscope.io/tutorial/task_state.html)
- [FlatAgents: State machines in YAML](https://github.com/memgrafter/flatagents)

### Schema-Driven Prioritization
- [Schemas: Secret Sauce for AI Agents](https://medium.com/@oaistack/schemas-the-secret-sauce-for-smarter-ai-agents-888c2f8f084d)
- [Schema-Driven Design for AI Automation — OpsM ill](https://opsmill.com/blog/schema-driven-design-ai-automation/)
- [How to Write a Good Spec for AI Agents — Addy Osmani](https://addyosmani.com/blog/good-spec/)
- [12 Failure Patterns of Agentic AI](https://www.concentrix.com/insights/blog/12-failure-patterns-of-agentic-ai-systems/)
- [Tackling the Partial Completion Problem](https://medium.com/@georgekar91/tackling-the-partial-completion-problem-in-llm-agents-9a7ec8949c84)

### Delta Output
- [Event Sourcing — Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [Terraform Plan Command](https://spacelift.io/blog/terraform-plan)
- [Can AI Agents Exhibit Idempotency?](https://medium.com/autonomous-agents/can-ai-agents-exhibit-idempotency-2cea33cc681c)
- [Automated Patch Diff Analysis with LLMs](https://blog.syss.com/posts/automated-patch-diff-analysis-using-llms/)
- [Delta CRDTs — WorkOS](https://workos.com/blog/in-memory-distributed-state-with-delta-crdts)

### Frameworks and Architecture
- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [CrewAI Tasks](https://docs.crewai.com/en/concepts/tasks)
- [The 2026 Guide to Agentic Workflow Architectures](https://www.stack-ai.com/blog/the-2026-guide-to-agentic-workflow-architectures)
- [Context Engineering for Agents — LangChain](https://blog.langchain.com/context-engineering-for-agents/)
- [AI Agent Observability in 2026](https://www.n-ix.com/ai-agent-observability/)
