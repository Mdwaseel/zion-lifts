# Zion Lifts — style lock

The style is established in code; this file points at it rather than restating it.

- **Tokens:** `frontend/src/styles/tokens.css` (dark ground `--dark-*`, light ground `--light-*`, ivory `--light-surface`, `--teal` text-safe on light, `--teal-bright` on dark only, no gold anywhere — blue only (user decision 2026-09-19)).
- **Type:** Inter for everything; Fraunces 300 (roman + italic) reserved for editorial moments — a lift’s name, a statement line, the way on to the next page. Mono uppercase for labels, used sparingly (no numbered eyebrow on every section).
- **Rhythm:** dark opening → warm ivory → paper → dark for proof. No alternating dark/light per section.
- **Shape:** hairline rules over boxed cards; 3–4px radii on imagery; pills only for things you press.
- **Motion:** one language on the lift page — "frames" that tip, stand up, stack and open, all driven by a CSS variable written from the GSAP ticker (`useScrollVar` in `pages/LiftDetail.jsx`). Sticky + runway for the two held sections (gallery wall, safety); no ScrollTrigger pinning. Scroll-scrubbed film on wide pointers, loop on touch. Every effect has a reduced-motion state.
- **Assets:** project photography in `frontend/public/media/`; per-lift rooms in `ROOMS` (`pages/home/LiftsExperience.jsx`); per-lift films in `public/media/lifts/`.
- **Mode:** none. References were the user's own homepage, not a generated palette.
