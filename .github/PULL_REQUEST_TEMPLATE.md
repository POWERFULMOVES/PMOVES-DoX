## Summary

Briefly describe the change. Link to issues if applicable.

## Highlights

- [ ] Feature 1
- [ ] Feature 2

## Breaking Changes

- [ ] None

## How To Test

Backend smoke (Docker CPU):

```bash
python smoke/run_smoke_docker.py
```

UI smoke (Docker + Playwright):

```bash
npm run smoke:ui
```

Manual:

1. Start backend (`uvicorn app.main:app`)
2. Start frontend (`npm run dev`)
3. Upload sample(s), verify Logs/API/Tags, run Export POML (all variants)

## Screenshots / Artifacts

Attach screenshots, POML artifacts, or logs as needed.

## Checklist

- [ ] Docs updated (README/NEXT_STEPS)
- [ ] Smoke tests passing locally
- [ ] No secrets committed

