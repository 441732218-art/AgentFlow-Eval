# AgentFlow Intelligence — Brand Guide

## Brand name

| Form | Usage |
|------|--------|
| **AgentFlow Intelligence** | Product full name, browser title, docs H1 |
| **AgentFlow** | Short lockup, sidebar wordmark |
| **AgentFlow-Eval** | GitHub repo / package path (legacy) |

**Tagline:** Agent Observability & Evaluation Platform  
**Positioning:** Enterprise SaaS command center for AI agents (LangSmith × Datadog energy).

---

## Logo system

Primary assets live in:

```
frontend/public/assets/logo/
├── logo.svg              # App mark (icon tile)
├── logo-dark.svg         # Full wordmark — dark UI
├── logo-light.svg        # Full wordmark — light UI
├── favicon.svg           # Browser favicon
└── logo-animation.json   # Motion / pulse spec
```

Mirrored for docs: `docs/brand/` · Legacy aliases: `frontend/public/brand/`.

### Concept

- **Central AI core** — hex + radiant disk (not brain / robot / face)
- **Neural nodes** — six orbit points linked as agent network
- **Data stream** — cyan → purple → gold flow (workflow + observability)
- **Gold eval tick** — quality / monitoring signal

### Color

| Token | Hex | Role |
|-------|-----|------|
| Navy | `#050816` | Background / tile |
| Cyan | `#00D4FF` | Primary neon / streams |
| Purple | `#8B5CF6` | AI accent / nodes |
| Gold | `#FFC857` | Evaluation / premium accent |

Keep contrast AA on dark panels; use `logo-light.svg` on white surfaces.

---

## Usage rules

| Context | Asset |
|---------|--------|
| Sidebar collapsed | `logo.svg` mark 34px |
| Sidebar expanded | lockup via `BrandLogo variant="lockup"` |
| Login / splash / loading | mark animated (`afi-logo--animated`) |
| README / docs banner | `logo-dark.svg` |
| Light marketing | `logo-light.svg` |
| Favicon / PWA | `favicon.svg` |
| Docker / terminal banner | mark + text "AgentFlow Intelligence" |

### Do

- Prefer SVG over raster for product UI
- Keep clear space ≈ 1/5 mark height around the icon
- Use pulse animation only on splash / loading, not dense dashboards

### Don’t

- Recolor core gradients arbitrarily
- Add robot / human / brain illustrations
- Stretch the mark or use low-res screenshots as source

---

## Frontend integration

```tsx
import { BrandLogo, BRAND } from "@/components/brand/BrandLogo";

<BrandLogo variant="mark" size={34} />
<BrandLogo variant="lockup" size={34} />
<BrandLogo variant="full" size={40} colorScheme="dark" />
```

Wired into: `Sidebar`, `BootSplash`, `Loading`, `PageSkeleton`, `NotFound`, `index.html` title/favicon.

---

## Motion

See `logo-animation.json` — CSS class `afi-logo--animated` applies core pulse (2.4s loop).

---

## Version

Brand kit v1.0 · aligned with Intelligence Center UI tokens (`theme/tokens.ts`).
