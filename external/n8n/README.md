# PMOVES-BoTZ n8n Integration

This directory integrates [n8n](https://n8n.io/) workflows to power PMOVES Cookbooks.

## Setup
In a production environment, this should be a submodule:
```bash
git submodule add https://github.com/pmoves-ai/n8n external/n8n
```

## Workflows
The workflows here orchestrate:
1.  **Document Ingestion Pipelines**
2.  **Hybrid AI Routing (via TensorZero)**
3.  **Automated Reporting**

## Cookbooks
These workflows are exposed via the `frontend/app/cookbooks` interface.
