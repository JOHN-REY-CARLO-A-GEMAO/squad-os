# squad.yaml — Manifest Specification v1.0.0

The `squad.yaml` file is the human-authored entry point for Squad OS Agent
Packages (`.sqad`).  It describes **who** the agents are, **how** they are
connected in a directed acyclic graph (DAG), and **what** runtime environment
they require.

The CLI compiles it into a compact `.sqad` bundle:

```bash
python -m squad_os.store.cli build ./squad.yaml
```

---

## 1.  Structure Overview

```yaml
spec_version: "1.0.0"
metadata:
  name: string
  version: semver
  description: string
  author: string
  license: string
topology:
  engine: "dag"
  agents:
    - id: string
      role: "researcher" | "developer" | "qa" | "custom"
      system_prompt: string
      llm_default: string
      tools: string[]
  dependencies:
    - parent: string
      child: string
      condition: string
runtime:
  required_tools:
    - name: string
      min_version: semver
  environment_defaults:
    KEY: value
```

---

## 2.  Fields

### 2.1  `spec_version`

The version of the squad.yaml schema this file targets.

| | |
|---|---|
| **Required** | No (default `"1.0.0"`) |
| **Type**     | string (semver) |

---

### 2.2  `metadata`

Package identity.

```yaml
metadata:
  name: "devops-self-healer"
  version: "0.1.0"
  description: "Monitors production logs, diagnoses exceptions, and auto-fixes."
  author: "@solodev"
  license: "Apache-2.0"
```

| Field       | Required | Type   | Description |
|-------------|----------|--------|-------------|
| `name`      | **yes**  | string | Human-readable package name.  Used to derive the internal package `id`. |
| `version`   | **yes**  | semver | Must follow `X.Y.Z` semver. |
| `description` | no    | string | Short summary. |
| `author`    | no       | string | Author handle or name. |
| `license`   | no       | string | SPDX identifier (e.g. `MIT`, `Apache-2.0`). |

---

### 2.3  `topology`

Defines the execution graph — the agents that participate and how they
are connected.

#### 2.3.1  `topology.engine`

The orchestration engine to use.

| | |
|---|---|
| **Type** | string |
| **Default** | `"dag"` |

Only `"dag"` is currently supported.  Future values may include
`"sequential"`, `"fan-out"`, or `"pipeline"`.

---

#### 2.3.2  `topology.agents`

List of agent definitions.  Each agent becomes a node in the DAG.

```yaml
agents:
  - id: "log_analyzer"
    role: "researcher"
    system_prompt: "You monitor log streams. Identify fatal exceptions."
    llm_default: "gpt-4o-mini"
    tools: ["web_search", "file_io"]

  - id: "code_patcher"
    role: "developer"
    system_prompt: "You fix bugs. Analyze stack traces and patch Python files."
    llm_default: "gpt-4o"
    tools: ["file_io", "terminal", "self_healing"]
```

| Field            | Required | Type   | Description |
|------------------|----------|--------|-------------|
| `id`             | **yes**  | string | Unique identifier within this squad.  Referenced by `dependencies[].parent` / `child`. |
| `role`           | **yes**  | string | Agent archetype.  Built-in roles: `researcher`, `developer`, `qa`, `scout`, `planner`.  Freeform for custom roles. |
| `system_prompt`  | **yes**  | string | The core instruction that defines the agent's behavior.  Equivalent to `goal` in earlier schema versions. |
| `llm_default`    | no       | string | Model identifier (e.g. `gpt-4o`, `gpt-4o-mini`, `claude-3-opus`).  Falls back to the runtime's default when absent. |
| `tools`          | no       | string[] | Tool names the agent is permitted to call. |

---

#### 2.3.3  `topology.dependencies`

Directed edges between agent nodes.  Each edge declares that `child` must
wait for `parent` to finish before it starts, optionally gated by a
condition expression.

```yaml
dependencies:
  - parent: "log_analyzer"
    child: "code_patcher"
    condition: "exception_found == true"
  - parent: "code_patcher"
    child: "qa_validator"
    condition: "patch_applied == true"
```

| Field       | Required | Type   | Description |
|-------------|----------|--------|-------------|
| `parent`    | **yes**  | string | Must match an agent `id`. |
| `child`     | **yes**  | string | Must match an agent `id`. |
| `condition` | no       | string | Python expression evaluated against the mission context.  If absent the edge is unconditional. |

If `dependencies` is empty or omitted the DAG runner executes all agents
in parallel (subject to the runtime's parallelism cap).

---

### 2.4  `runtime`

Runtime constraints and environment configuration.

```yaml
runtime:
  required_tools:
    - name: "self_healing"
      min_version: "1.2.0"
  environment_defaults:
    LOG_PATH: "/var/log/app.log"
    MODE: "production"
```

#### 2.4.1  `runtime.required_tools`

Tools that must be discoverable by the runtime *before* the mission starts.
If a tool is missing or below `min_version`, the mission is rejected with a
clear error.

| Field         | Required | Type   | Description |
|---------------|----------|--------|-------------|
| `name`        | **yes**  | string | Tool name as registered in the SkillRegistry. |
| `min_version` | no       | semver | Minimum acceptable version. |

#### 2.4.2  `runtime.environment_defaults`

Default environment variables injected into every agent's execution
context.  Agents may override these; if they don't, the runtime applies
these defaults.

---

## 3.  Translation to Internal Format

When `squad build` compiles `squad.yaml` into a `.sqad` bundle:

1. **`topology.agents`** become **tasks** in the workflow, one task per agent.
   The `system_prompt` becomes the task's `description` / `goal`.

2. **`topology.dependencies`** are resolved from string IDs to integer
   `depends_on` indices.  If a dependency carries a `condition`, it is
   stored in a `conditions` list on the child task.

3. **`runtime.environment_defaults`** are embedded in the workflow so the
   DAG runner can inject them before execution.

4. The **`metadata.license`** field is preserved in the manifest and can
   be surfaced in the Agent Store UI.

---

## 4.  Example: Minimal Valid squad.yaml

```yaml
spec_version: "1.0.0"
metadata:
  name: "hello-world"
  version: "0.0.1"
  description: "A single agent that prints a greeting."
topology:
  agents:
    - id: "greeter"
      role: "developer"
      system_prompt: "Print 'Hello from Squad OS!' to stdout."
      tools: ["terminal"]
```

This compiles to a `.sqad` with one task and no dependencies — the DAG
runner executes it immediately.
