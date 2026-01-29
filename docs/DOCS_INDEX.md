# PMOVES-DoX Documentation Index

Welcome to the **PMOVES-DoX** documentation hub. This index serves as the central navigation point for all technical, architectural, and user-facing documentation.

## Getting Started

*   **[README.md](../README.md)**: High-level overview, quick start guide, and features.
*   **[USER_GUIDE.md](USER_GUIDE.md)**: Comprehensive user manual, workflows, and best practices.
*   **[DEMOS.md](DEMOS.md)**: Interactive demos and examples (Quick Start, Financial Analysis, etc.).
*   **[DEPLOYMENT.md](DEPLOYMENT.md)**: Deployment guide for standalone and docked modes.

## Architecture & Integrations

*   **[ARCHITECTURE.md](ARCHITECTURE.md)**: System design, data flow, component breakdown, and **Cipher** integration details.
*   **[PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)**: Directory layout and codebase orientation.
*   **[DOCKING_GUIDE.md](DOCKING_GUIDE.md)**: Integration with parent PMOVES.AI ecosystem.
*   **[PsyFeR Integration](../README.md#%F0%9F%A7%A0-byterover-cipher-integration)**: Details on the **Cipher** memory layer and `PsyFeR_reference` submodule.
*   **[PMOVES_INTEGRATION_PATTERNS.md](PMOVES_INTEGRATION_PATTERNS.md)**: Patterns for integrating with the PMOVES.AI ecosystem.

## Technical Reference

*   **[API_REFERENCE.md](API_REFERENCE.md)**: Complete REST API documentation, including the new **Cipher** and **A2UI** endpoints.
*   **[COOKBOOKS.md](COOKBOOKS.md)**: Specialized recipes for advanced use cases (Financial Analysis, Log Analysis, etc.).
*   **[tensorzero.md](tensorzero.md)**: TensorZero LLM gateway configuration and usage reference.
*   **[GEOMETRIC_INTELLIGENCE.md](GEOMETRIC_INTELLIGENCE.md)**: Geometric visualization and CHIT protocol documentation.
*   **[GEOMETRY_BUS_INTEGRATION.md](GEOMETRY_BUS_INTEGRATION.md)**: NATS-based geometry message bus integration.

## Agent Integration

*   **[AGENT_GUIDE.md](AGENT_GUIDE.md)**: Agent Zero integration and configuration guide.
*   **[agents/](agents/)**: Agent-specific documentation and prompts.

## Implementation Status

*   **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)**: Current status of PMOVESCHIT and Geometric Intelligence features.

## Knowledge Graph

*   **Neo4j Usage**: Knowledge graph is available at `http://localhost:17474` (standalone) or via parent Neo4j in docked mode.
*   See [DEPLOYMENT.md](DEPLOYMENT.md) for Neo4j environment variables (`NEO4J_LOCAL_PASSWORD`, `NEO4J_PARENT_PASSWORD`).

## Troubleshooting

Common issues and solutions are documented in:
*   **[DEPLOYMENT.md#troubleshooting](DEPLOYMENT.md#troubleshooting)**: Port conflicts, service startup issues, network connectivity.
*   **[../CLAUDE.md](../CLAUDE.md)**: Developer-specific gotchas and common issues.

## Experiments & Research

*   **[Understanding the HRM Model](Understanding%20the%20HRM%20Model_%20A%20Simple%20Guide.md)**: Guide to the Hierarchical Reasoning Module (HRM).
*   **[HRM Transformer Sidecar](HRM_Transformer_Sidecar_Colab.ipynb)**: Jupyter notebook prototype for HRM.
*   **[K-Furthest Neighbors](K_Furthest_Neighbors_(KFN).ipynb)**: Research notebook on KFN algorithms.

---

*Documentation last updated: January 2026*
