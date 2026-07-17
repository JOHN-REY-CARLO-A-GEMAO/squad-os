# AI SaaS Launch Pipeline

A multi-agent workflow package for SquadOS that helps founders validate and prepare SaaS products for launch.

## Features

- SaaS idea structuring
- Competitor research
- Technical feasibility analysis
- Marketing copy generation
- Investor readiness analysis
- Launch checklist creation

## DAG Overview

```text
                intake-agent
                 /        \
                /          \
 market-research-agent   technical-feasibility-agent
          |                        |
          |                        |
   marketing-agent         launch-planner-agent
          |
          |
 investor-readiness-agent (conditional)
```

## Conditional Logic

The investor readiness branch only runs if the intake output contains:
- "b2b" or "B2B"
- "enterprise" or "Enterprise"

## Build

```bash
python -m squad_os.store.cli build ./squad.yaml --verbose
```
