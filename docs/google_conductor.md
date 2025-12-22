# Google Conductor Integration (PMOVES-BoTZ)

## Overview
**Conductor** is a "Context-Driven Development" extension for the Gemini CLI, integrated into the PMOVES ecosystem as **PMOVES-BoTZ**. It acts as a proactive project manager agent that enforces a `Context -> Spec -> Plan -> Implement` workflow.

## Repository
The Conductor source is maintained as a submodule in `external/conductor`.
- **Remote**: `https://github.com/gemini-cli-extensions/conductor.git`

## Integration with TensorZero (Model Gateway)

To ensure **PMOVES-BoTZ** complies with the [TensorZero Model Provider](./tensorzero.md) requirements, the underlying `gemini` CLI should be configured to route requests through the TensorZero Gateway where possible, or use the centralized Google Credentials managed via GitHub Secrets.

### 1. Hardened Google SDKs
The backend has been hardened with official Google SDKs to support native execution:
- `google-generativeai` (AI Studio)
- `google-cloud-aiplatform` (Vertex AI)

### 2. Configuration Strategy
When running Conductor commands (`/conductor:implement`), the agent relies on the host's LLM configuration.

**TensorZero Routing (Recommended):**
If the `gemini-cli` supports OpenAI-compatible endpoints, configure it to point to TensorZero:
```bash
export OPENAI_BASE_URL="http://localhost:3030/v1"
export OPENAI_API_KEY="tensorzero"
```

**Native Google Routing (Fallback):**
If using native Google mode, ensure credentials are loaded:
```bash
export GOOGLE_API_KEY="<your-secret-key>"
```
*Note: In CI/CD, these are injected via GitHub Secrets.*

## Workflow: The "BoTZ" Protocol

1.  **Setup**: Initialize the project context.
    ```bash
    gemini exec /conductor:setup
    ```
2.  **New Track**: Define a feature.
    ```bash
    gemini exec /conductor:newTrack "Implement Geometry Engine"
    ```
3.  **Implement**: Let the agent build it.
    ```bash
    gemini exec /conductor:implement
    ```

## Artifacts
Conductor stores its state in the `conductor/` directory at the project root:
- `conductor/product.md`
- `conductor/tech-stack.md`
- `conductor/tracks.md`

> [!TIP]
> Use the **Hyperdimsional Navigator** to visualize the `tracks.md` progress as a directed graph!
