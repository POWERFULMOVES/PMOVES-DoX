# PMOVES-DoX Branding Alignment Tasks

## Context
A repository-wide audit was performed to remove the remaining “meeting app” references and to refresh the visible product copy with the PMOVES-DoX positioning (“The ultimate document structured data extraction and analysis tool…”). The items below capture the next pieces of work needed to finish the branding transition.

## Backlog
- **Frontend assets**
  - Replace the default Next.js favicon / app icons with PMOVES-DoX artwork so browser tabs and PWA installs pick up the new branding.
  - Add OpenGraph/Twitter metadata (title, description, preview image) that mirrors the new tagline for richer link unfurls.
  - Review empty states, toasts, and settings copy for residual LMS- or meeting-specific wording and update to the PMOVES-DoX voice.
- **Backend & services**
  - Standardize structured log prefixes and telemetry emitted from the FastAPI app so dashboards show “PMOVES-DoX” consistently.
  - Update any scheduled jobs or Celery task names (e.g., when Celery is re-enabled) to drop legacy identifiers.
- **Docs & onboarding**
  - Refresh the Windows `setup.ps1` prompts and README screenshots once new logos/artifacts exist.
  - Produce a quickstart Loom/screencast that walks through the PMOVES-DoX UI and features (references in `docs/NEXT_STEPS.md`).
- **Distribution**
  - Verify Docker image tags, Supabase project metadata, and future release notes use the PMOVES-DoX name for marketplace publishing.

## Notes
Keep this checklist updated as new surfaces are branded so the next pass can verify the rename is complete end-to-end.
