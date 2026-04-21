# ADR 003 — Two-track retrieval: facts vs. tone

- Status: accepted
- Date: 2026-04-20
- Milestone: M11

## Context

`docs/requirements.md` §7 defines `transcricao` as **synthesized call
transcripts for few-shot / tone reference** — not policy and not fact. Until
M11, every ingested chunk lived in the same Qdrant collection and was
retrieved by the same cosine query, meaning transcripts could (and did) end
up as citable sources in `/ask` answers. That is epistemically wrong: the
atendente's lines in a transcript are LLM-generated dialog, not regulation.

## Decision

Split retrieval into **two concurrent passes inside the same retrieve
node**, using Qdrant's `must` / `must_not` filters against the shared
`knowledge` collection:

- **Factual pass** — `must_not: category == transcricao` (or `must: <user
  category>` if the caller pinned one). Its hits populate `sources` and are
  cited as `[n]` in the answer.
- **Stylistic pass** — `must: category == transcricao`, top-K controlled by
  `OPENCALL_STYLE_TOP_K` (default 2). Its hits are injected into the system
  prompt as lettered `(A), (B)` snippets with an explicit instruction: use
  for register only, do not cite. They never appear in `sources`.

The style pass is skipped when the caller supplies an explicit
`category_filter` (debugging/scoping contexts) and when `style_top_k=0`
(evaluation harness — see below).

## Alternatives considered

1. **Separate Qdrant collection for transcripts.** Cleaner data model, but
   the current bottleneck is architecture, not storage. Deferred: revisit
   when we introduce the post-MVP fine-tuning pipeline, which will want
   transcripts as a first-class asset anyway.
2. **Drop transcripts entirely.** Cheapest path to correctness, but
   discards the asset the requirements explicitly asked for. Would also
   make a post-MVP fine-tuning corpus harder to reconstruct.
3. **Exclude transcripts only from citations (post-filter).** Rejected —
   transcript chunks would still consume retrieval slots and suppress
   citable hits below the score threshold, silently reducing recall.

## Consequences

- `/ask` citations can no longer reference synthesized dialog — resolves
  the epistemic gap flagged against the M9 surface.
- Answer register should stay aligned with the transcript corpus as the
  model now sees exemplars on every synthesis turn (modulo the style-off
  paths below).
- The eval harness forces `style_top_k=0` via `Settings.model_copy` so the
  gold set measures retrieval recall against factual sources alone. Without
  this, transcript phrasing could inflate `must_contain` coverage without
  proving the citable retrieval worked.
- Gold rows that previously required `transcricao_*.txt` in `must_cite` were
  corrected as part of M11 — those questions are really about policy/FAQ
  content; the transcripts were cosmetic.
- `STYLE_CATEGORY = "transcricao"` is a module constant in `agent.graph`.
  Adding another tone-only category (e.g., `chat_exemplo`) means extending
  that constant to a set and widening `_factual_filter` / `_style_filter`
  accordingly.

## Follow-ups

- When the post-MVP fine-tuning item lands, promote transcripts to a
  dedicated collection and retire the same-collection filter approach.
- If style examples start nudging the model into quoting transcript
  phrasing verbatim, shrink `OPENCALL_STYLE_TOP_K` or tighten the "do not
  cite" instruction in `STYLE_BLOCK_HEADER`.
