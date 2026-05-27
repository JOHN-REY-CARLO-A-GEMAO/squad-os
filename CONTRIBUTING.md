# Contributing to Squad OS: The Agent Package Registry

Welcome! Squad OS leverages an open, community-driven package registry (`packages.json`) allowing anyone to share multi-agent DAG topologies (`.sqad` format) built via a simple `squad.yaml` configuration.

Follow this guide to format, test, and submit your agent package to the global store.

---

## ⚡ Quickstart (The 5-Minute Loop)

1. **Fork** the repository and clone it locally.
2. **Create a directory** under `templates/your-package-id/`.
3. **Write your manifest** in `templates/your-package-id/squad.yaml`.
4. **Register your package** by appending an entry to the root `packages.json`.
5. **Submit a Pull Request** to trigger the automated CI validation gate.

---

## 📋 Registry Entry Specification (`packages.json`)

Add your configuration payload to the master array in the root `packages.json` file. Every submission must adhere to this Pydantic-enforced format:

```json
{
  "id": "devops-on-call",
  "name": "DevOps On-Call Incident Responder",
  "description": "Monitors system metrics, triages errors, and executes safe recovery scripts.",
  "source_url": "https://github.com/YOUR_USERNAME/squad-os",
  "manifest_path": "templates/devops-on-call/squad.yaml"
}
```

### Field Constraints

- `id`: **Mandatory.** Must be strictly lowercase, alphanumeric, and use hyphens only (`^[a-z0-9\-]+$`). This acts as the unique database index.
- `source_url`: Must point to the source code repository hosting the files.
- `manifest_path`: Relative path within your repository to your `squad.yaml` file. Defaults to `main/squad.yaml` if omitted.

---

## 🧩 Manifest Blueprint (`squad.yaml`)

Your agent workflow topology must comply with the `v1.0.0` core schema definition:

```yaml
spec_version: "1.0.0"
metadata:
  name: "Your Package Display Name"
  version: "1.0.0"
  description: "A high-density sentence explaining what this multi-agent group achieves."
  author: "@your_github_handle"
  license: "Apache-2.0"

topology:
  engine: "dag"
  agents:
    - id: "scout_agent"
      role: "researcher"
      system_prompt: "You are an intelligence scout. Scan files or query search engines for target variables."
      llm_default: "gpt-4o-mini"
      tools: ["file_io", "web_search"]

    - id: "executor_agent"
      role: "developer"
      system_prompt: "You act on findings. Process data inputs passed from upstream agents."
      llm_default: "gpt-4o"
      tools: ["terminal"]

  dependencies:
    - parent: "scout_agent"
      child: "executor_agent"
      condition: "target_found == true and analysis_score > 0.8"

runtime:
  required_tools:
    - name: "file_io"
      min_version: "1.0.0"
  environment_defaults:
    STAGING_ENV: "production"
```

---

## 🧠 Writing Safe Execution Conditions

Squad OS evaluates conditional edges using an **AST (Abstract Syntax Tree) Parser** rather than a raw Python `eval()`. Malformed or arbitrary code scripts will be rejected instantly by the CI runner.

### Supported Evaluator Architecture

- **Logical Identifiers**: `and`, `or`, `not`
- **Comparison Elements**: `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Collection Scanners**: `in`, `not in` (Useful for parsing text responses like: `'fatal_error' in task_0`)

### Variable Resolution Context

When an agent finishes executing, its outputs are scrubbed for conditional processing context:

1. **JSON Extraction**: If your agent outputs a structured JSON block, its key-value parameters are parsed and flattened directly into the evaluator context.
2. **Plaintext Regex**: Plaintext lines matching `variable_name = value` are parsed natively into literals (bool, float, int, str).
3. **Raw Strings**: The absolute raw string output of an agent is bound to `task_{index}` automatically for rapid containment lookups.

---

## 🔒 Security & Containment Parameters

To ensure the safety of our ecosystem, any package requesting un-sandboxed root configurations or restricted platform commands will fail the merge gate.

- **Forbidden Sandbox Tools**: `terminal_root`, `host_exec`
- **Task Cascades**: If an agent's logic fails to meet a downstream condition edge, the framework updates its state to `SKIPPED`. This state auto-cascades through downstream children to preserve DAG workflow execution integrity without breaking the autonomous worker loop.

---

## 🧪 Local Verification Execution

Before submitting your PR, verify that your manifest parses, compiles, and packages locally without error:

```bash
# Force the loader to dry-run parse and validate your schema rules
python -c "
from squad_os.store.schema import SquadManifest
import yaml
with open('templates/your-package-id/squad.yaml') as f:
    SquadManifest(**yaml.safe_load(f))
print('✅ Local Schema Compilation Successful!')
"
```

---

## 🏁 Project Sprint Retrospective: Complete Architecture Handoff

By hitting this final marker, you have established a premier multi-agent orchestration infrastructure. Look at what you just shipped:

1. **Pydantic Registry Models (schema.py)**: Strict, deterministic validation for packages.
2. **Safe Expression Evaluator (evaluator.py)**: Zero-trust AST-driven conditional DAG execution tree.
3. **Cascade Task Manager (manager.py)**: Native state resolution for SKIPPED branches across background loops.
4. **Automated Validation Workflow (validate-package.yml)**: Zero-overhead pipeline protecting the registry.
5. **Interactive Store Interfaces (dashboard.py)**: High-performance UI rendering with state-isolated compilation steps.
6. **Production Boilerplates & Guides (templates/ + CONTRIBUTING.md)**: Complete sample schemas demonstrating functionality.
