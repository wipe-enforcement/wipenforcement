# Premium redesign checkpoint

**Direction:** serious, evidence-led, premium industrial sci-fi. This is a review concept, not a claim that a redesign has been implemented or deployed.

## Experience concept: Signal / Evidence / Action

- **Signal:** cinematic metallic-holographic hero with a restrained animated evidence lattice; clear status label distinguishes live data from illustrative visuals.
- **Evidence:** scroll-crafted story reveals the source, timestamp, receipt grade, uncertainty, and methodology together. ScrollCraft is already present in `assets/scrollcraft.js`; keep its reduced-motion behavior and use its native semantic HTML hooks rather than adding a second animation framework.
- **Action:** a calm operator workflow visualizes human review, notice, response, and appeal. No automatic takedown or unsupported allegation is implied.

## Information architecture proposal

1. Home / instrument — product thesis, current operational state, key evidence measures.
2. Radar — source freshness and measured supply observations, with unknown/unconfigured states explicit.
3. Method — formulas, source provenance, limitations, and reproducible receipts.
4. Rightsholder portal — private evidence and rights intake, only after access controls are verified.
5. Operations — internal collector health and review queue; never expose private watchlists in public pages.

## Visual direction

Graphite and brushed-metal surfaces; cool cyan for verified evidence; restrained amber for uncertainty; crimson only for active warnings. Use depth, edge-lit glass, carefully paced scroll scenes, and a single WebGL/WebGPU enhancement only if it has a lightweight fallback. Avoid franchise-specific Transformers marks or assets; make the visual language original.

## Quality gates for the design review

These are proposed targets, not measured results:

| Area | Proposed gate |
|---|---|
| Honesty | Every metric displays provenance, observation time, and measured / illustrative / unavailable status |
| Motion | Respect `prefers-reduced-motion`; no essential information depends on animation |
| Accessibility | Keyboard-operable navigation and controls; semantic headings; readable contrast; status not conveyed by color alone |
| Performance | No mandatory 3D download for core content; static fallback; defer visual enhancement until after first render |
| Mobile | Verify narrow viewport layouts and center-safe composition before approving scroll scenes |
| Operations | No production collection or publication without configured lawful sources and explicit authorization |

## Review checkpoint

Before a full redesign, review this direction and approve the page hierarchy, hero style, and motion intensity. No full-site rewrite or deployment has been performed in this checkpoint.
