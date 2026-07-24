# Audience-Aware Story Routing

Read this before storyboarding. Audience affects slide order, evidence timing, terminology, visible definitions, and presenter notes, not only tone.

## Build the audience model

Create a compact internal table before ordering slides:

| Audience | Why they are here | Decision or action | Existing knowledge | Detail tolerance | Likely objection |
|---|---|---|---|---|---|

Identify the decision owner, implementation owner, operational user, and any audience that can block the proposal. One person may hold several roles. Do not ask another question when the user already supplied enough context; infer reasonable jobs and record uncertainty in notes.

If no audience was supplied, ask for it in the same opening message as the validation-mode question. Offer a short set of useful examples and allow `청중은 알아서 해줘`. That delegation selects a general company-wide concept-sharing audience with mixed domain familiarity. Ask once only; do not reopen the question after storyboarding begins.

## Decide which terms need visible help

Judge terminology semantically from the audience model. Do not run a keyword, acronym, capitalization, or frequency parser.

Add a compact visible note at the first meaningful occurrence only when all of these are true:

1. the term is necessary to understand the current claim or decision;
2. the intended audience is unlikely to know it reliably;
3. the visible copy does not already explain it;
4. one short plain-language line can remove the ambiguity.

Good candidates include unfamiliar external organizations, market names, regulatory instruments, product abbreviations, or internal shorthand that a mixed audience cannot infer. For example, a company-wide STO overview may briefly identify `NXT컨소시엄` and `KDX` as candidates for a trust-beneficiary-certificate over-the-counter market, while an STO domain-team status update may omit those notes. Definitions must be grounded in the same research as the slide and must not invent an acronym expansion.

Do not annotate common language, every acronym, incidental source names, or terms the named audience shares. Do not repeat the same definition on every slide. Executive audiences usually need the consequence or decision role, not a dictionary entry.

Use a short form such as `용어 — 이 발표에서 뜻하는 역할` and mark it with `data-term-note`. Place it beside the first meaningful use or in a compact micro-note rail. It should look like a quiet caption, not another content block: no large white card, tall padding, full-width glossary band, or oversized border. Keep it inside the content-safe area, visually subordinate but readable, and physically separate from `data-source-citation` and navigation. One or two notes on a slide is normally enough. When more are necessary, simplify the slide, stage the concepts across several slides, or move secondary definitions to presenter notes. A dense glossary footer is a failure, not thoroughness.

Do not place a term note in the persistent navigation exclusion zone at the lower right. Prefer an inline note beside the term. When a footer rail is necessary, use the runtime shell's `.nav-safe-note` helper or reserve at least the documented navigation width and height manually. A long note must wrap or move upward inside the content composition; it must never continue behind the controls.

## Separate authoring instructions from audience copy

Classify prompt details as either audience-facing content or private production constraints before writing visible copy. Validation mode, slide count, file format, requested workflow, image quantity, design direction, delivery time, and phrases such as `개념 강의 + 팀 활동` normally guide production rather than appear verbatim in the presentation. Show them only when they are genuine course, event, or operational logistics that the intended audience needs. Do not turn leftover prompt wording into cover eyebrows, badges, footer metadata, section labels, or decorative chips.

## Choose the attention order

Sequence information by the room's shared decision path:

1. Establish the subject and the outcome this room cares about.
2. Give the least technical shared context needed to understand the stakes.
3. Show the contrast, evidence, experience, or mechanism that makes the recommendation credible.
4. State the decision, recommendation, or next action before specialist attention becomes fragmented.
5. Place implementation detail, architecture, edge cases, and source-heavy proof after the common decision spine unless those details are themselves the decision.
6. Close by resolving the opening promise for every named audience, not only the most technical group.

This is a reasoning framework, not a fixed `AS-IS → TO-BE` template. Use the information order that best earns attention and supports the requested outcome.

## Mixed-audience routing

For executives, business teams, and developers in the same room, normally lead with common stakes and decision contrast, then move from business effect to delivery confidence and finally technical depth. For example, an `AS-IS / TO-BE` contrast may move early because it gives every group a shared mental model, while architecture, protocol, API, deployment, and edge-case slides move into a later technical chapter.

Change that order when the room's actual decision demands it:

- Architecture review: constraints, system context, tradeoffs, and failure modes may need to come before the recommendation.
- Budget or executive approval: impact, alternatives, risk, cost, and the ask should appear before implementation mechanics.
- Client or sales presentation: pain, desired outcome, product experience, proof, and adoption confidence usually precede internal architecture.
- Training or onboarding: mental model, demonstration, guided practice, and exceptions usually work better than a proposal arc.
- Incident review: impact, timeline, root cause, containment, corrective action, and prevention form the decision path.

## Storyboard contract

For every slide, add these internal fields to the slide-role table:

- `primary_audience`: who most needs this slide;
- `secondary_audience`: who must remain oriented;
- `audience_question`: the question answered now;
- `decision_job`: how this slide advances understanding, confidence, or action;
- `detail_level`: common, decision, operational, or specialist;
- `why_now`: why this information belongs at this point rather than earlier or later.

No audience should sit through a long specialist section before understanding why it matters. Conversely, do not remove technical evidence merely to simplify the deck; defer it to the point where it answers an earned question.

## Presenter notes

Use notes to bridge audience layers. Signal when a technical section begins, explain why it matters to non-specialists, and tell the room when implementation detail is being deferred. Do not say that a section is optional when it contains evidence required for the decision.

## Review questions

- Can each named audience explain the problem and proposed outcome before the first specialist deep dive?
- Does the decision owner see the ask early enough to evaluate the remaining evidence?
- Are implementation owners given enough detail to trust feasibility?
- Does every specialist slide answer a question established earlier?
- Would moving any slide earlier or later reduce confusion or attention loss?
- Does the closing give each audience a clear implication or next action?
- Can the least familiar intended audience follow every decision-critical acronym or entity without turning the slide into a glossary?
- Were familiar or incidental terms left unannotated so notes remain sparse?
