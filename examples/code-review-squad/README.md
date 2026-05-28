# Code Review Squad 🛡️

This is a Gold Standard SquadOS package demonstrating the full feature set of the `.sqad` ecosystem.

## Features
- **Custom Tools:** Includes `github_tools.py` for repository interaction.
- **Custom Agent Personas:** Defines 4 specialized agents in `squad.yaml`.
- **Complex DAG:** Uses parallel waves and conditional edges.
- **External Dependencies:** Requires `httpx`.
- **Assets:** Bundles static resources for agents.

## Workflow
1. **GitHub Fetcher** grabs the PR diff.
2. **Security Reviewer** & **Architecture Reviewer** run in parallel.
3. **Critical Fixer** runs *only if* the Security Reviewer finds "CRITICAL" issues.

## Usage
```bash
python -m squad_os.store.cli build ./squad.yaml --verbose
```
