# UNFCU DocIntel Edition

Branded document intelligence edition for the **United Nations Federal Credit Union (UNFCU)**.

## Activation

```bash
# Local development
NEXT_PUBLIC_DOX_EDITION=unfcu npm run dev

# Docker
docker compose -f docker-compose.yml -f docker-compose.unfcu.yml up --build
```

## Color Mapping

| UNFCU Color          | Hex       | HSL              | DoX Variable            |
|----------------------|-----------|------------------|-------------------------|
| UN Blue (primary)    | `#226BDB` | `216 74% 50%`    | `--primary`, `--accent`  |
| Elite Navy           | `#1D3F59` | `206 50% 23%`    | `--card`, `--secondary`  |
| Peace Blue           | `#E3E9F0` | `212 27% 91%`    | `--primary-foreground`   |
| Financial Green      | `#2E766F` | `175 44% 32%`    | success token (future)   |
| Alert Red            | `#A01F45` | `343 67% 37%`    | `--destructive`          |
| Idealist Yellow      | `#F1B346` | `38 86% 61%`     | warning token (future)   |
| Legacy Purple        | `#7C548B` | `282 25% 44%`    | accent alternative       |
| Sustainability Green | `#BABC8E` | `62 24% 65%`     | subtle highlights        |
| Peace Cream          | `#F5F1EB` | `36 33% 94%`     | light mode (future)      |

## Asset Provenance

All brand assets sourced from the official UNFCU brand guidelines kit:

- **Logos**: Primary and secondary logos in white, UN Blue, Elite Navy, and black variants (PNG RGB)
- **Icons**: 10 curated SVG outline icons from the 28-icon brand set
- **Colors**: Extracted from `colors.css` / `colors.ase` in the brand kit

Total committed assets: ~247KB. Photography, video, and document templates are excluded.

## Files

```
frontend/themes/unfcu/
  theme.ts              # Theme definition (brand name, logo paths, glow colors)
  unfcu-overrides.css   # Corporate glassmorphism, scrollbar, grid tinting
  README.md             # This file

frontend/public/themes/unfcu/
  unfcu-logo-white.png  # Primary logo (white on transparent)
  unfcu-logo-blue.png   # Primary logo (UN Blue on transparent)
  unfcu-wordmark-white.png  # Secondary wordmark (collapsed sidebar)
  favicon.ico           # App favicon
  icons/                # Curated SVG icons
```
