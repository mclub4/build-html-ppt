# Architecture Diagrams

## Choose the diagram from the question

| Question | Diagram |
|---|---|
| Who uses the system and what lies outside it? | System context |
| What are the main deployable services and stores? | Container/component |
| How does one request or datum travel? | Request/data flow |
| In what order do actors interact? | Sequence |
| Where does software run? | Deployment/topology |
| Where do permissions or trust change? | Trust boundary |
| What changes in a redesign? | Before/after or migration stages |

Use the smallest diagram that answers the presentation’s claim. Split overview, critical path, failure handling, and deployment into separate slides when needed.

## Establish truth before drawing

Extract an inventory before layout:

- actors and external systems;
- services, workers, gateways, queues, databases, caches, and object stores;
- enclosing boundaries such as cloud account, VPC/VNet, region, cluster, namespace, or trust zone;
- directed relationships with purpose and protocol;
- synchronous calls, asynchronous events, batch paths, and replication;
- security controls, identity handoffs, and public/private exposure;
- availability or scaling facts explicitly supported by the source.

Do not infer missing technology from convention. Write `TBD` or `assumed` when a diagram must show an unresolved decision.

## Visual semantics

Create a legend and reuse it across the deck:

- solid arrow: synchronous request/response;
- dashed arrow: event, queue, batch, or eventual propagation;
- double line or paired arrows: replication only when confirmed;
- colored boundary: network, ownership, or trust change;
- accent path: the one flow currently being explained;
- muted nodes: supporting or out-of-scope systems;
- database cylinder only for persistent stores; queue shape only for brokers/streams.

Label edges with a concise verb plus protocol when known, such as `query · HTTPS`, `publish · Kafka`, or `read/write · SQL`. Avoid unlabeled crossings.

## Layout patterns

- Prefer left-to-right for request and data flows.
- Prefer top-to-bottom for layered architectures: channel → edge → application → data.
- Place shared infrastructure below the services it supports.
- Place external actors outside labeled boundaries.
- Align nodes to a grid and keep equal gaps for equal relationships.
- Route orthogonal connectors through dedicated gutters. Avoid diagonal lines and crossings; if two edges must cross, reroute or split the slide.
- Keep node labels to a name plus one short role. Move details into callouts or the speaker narrative.
- Fit roughly 5–9 primary nodes on a 1280×720 overview slide. More nodes usually require grouping or another slide.

## Inline SVG construction

Use inline SVG for exact, self-contained technical diagrams:

- Set a stable `viewBox` and let CSS scale width and height.
- Define arrowheads once in `<defs>` with unique IDs per document.
- Group every node in `<g>` with a rectangle/shape and text.
- Use SVG text for short labels; use `<foreignObject>` only when wrapping is essential and browser compatibility is acceptable.
- Add `<title>` and `<desc>` to informative SVGs and reference them with `aria-labelledby`; mark purely decorative SVG as `aria-hidden="true"`.
- Keep text at least 14px at 1280×720 logical scale; primary node names should be 16–20px.
- Use CSS variables for node, boundary, connector, and highlight colors so diagrams inherit the deck theme.

Prefer structured HTML/CSS when the diagram is a simple grid of cards and connectors. Do not add Mermaid as a network dependency to an offline deck. If Mermaid source is useful, render or replace it with self-contained output before delivery.

## Progressive storytelling

For complex systems, build a short sequence:

1. context and boundaries;
2. happy-path request/data flow;
3. control plane or asynchronous processing;
4. failure, retry, fallback, or degraded path;
5. deployment, scale, or migration view.

Keep positions stable between related slides so the audience sees what changed. Dim unaffected components and highlight only the current path.

## Architecture QA

Verify before delivery:

- every arrow has a clear direction and valid endpoints;
- every protocol, product, region, and boundary is supported by source material;
- the legend matches the actual line styles;
- no connector passes through a node label;
- no text is clipped at the final viewport;
- contrast remains readable on every slide surface;
- the overview is understandable within roughly ten seconds;
- detailed slides explain, rather than duplicate, the overview;
- assumptions and out-of-scope areas are visibly identified.
