# 0006 - Topics taxonomy v0

Issue: #6    Role: C3    Spec: specs/thematic.md

## Goal
A first topics taxonomy in `config/topics.yaml` that covers every theme in Q16-Q21, with a
one-line definition per topic, ready for keyword tagging (`tag_topics`) and C1 review.

## Files to change
- `config/topics.yaml` (new) - the taxonomy: id, label, parent, definition, linked questions,
  seed keywords. Shape matches the `topics` table (topic_id, label, parent_id).
- `config/entities.yaml` - `themes:` keeps its 7 seed IDs unchanged (S1 will match on them),
  adds advisor_selection; one comment pointing to `config/topics.yaml` as the full taxonomy.
- `docs/PROGRESS.md` - not edited by hand; the PR's Progress line is copied in by the bot.

## Steps
1. Keep the 7 seed top-level topics and their IDs: advice_future, ai_advice, fees_pricing,
   younger_investors, wealth_transfer, advisor_recruiting, mass_affluent.
2. Add sub-topics only where a Q16-Q21 question needs a finer cut:
   - advice_future > advice_delivery_models, advice_regulation              -> Q16 (Q18)
   - ai_advice > ai_advisor_tools (deployed) vs ai_strategy_claims (aspiration) -> Q17
   - fees_pricing > fee_disclosures, fee_regulation, fee_industry_trends     -> Q18
   - younger_investors > younger_investor_preferences, younger_investor_offerings -> Q19, Q20
   - advisor_selection as its own top-level topic (surveys cover all ages)   -> Q20
     (also added to `themes:` in config/entities.yaml)
   - wealth_transfer > transfer_estimates vs transfer_firm_preparation       -> Q21
3. Write a one-line, neutral (non-normative) definition per topic.
4. Add seed keywords per topic for future keyword tagging (no tagging code this task), plus
   the tagging rules in the file header: whole-word matching; a sub-topic's keywords count
   only when its parent also matches; no keyword shared across topics unless declared.
5. Coverage table Q16-Q21 -> topic ids in the file header.
6. Validate: YAML loads; ids unique; every parent exists; every topic has a definition and
   keywords; top-level ids equal the `themes:` seed list; Q16-Q21 each map to >= 1 topic;
   every linked question ID exists in `evals/questions.yaml`.

Unsure / for review:
- Whether advisor_selection should stay top-level (C1 to confirm in review).
- advisor_recruiting and mass_affluent have no sub-topics yet (not in Q16-Q21).
- Keywords contain no figures or entity facts (ground rule 4).

## Acceptance
- [x] Linked questions: Q16, Q17, Q18, Q19, Q20, Q21 each map to >= 1 topic
- [x] Every topic has a one-line definition
- [x] Check: validation script in step 6 -> `OK: 19 topics (8 top-level), Q16-Q21 covered`; no duplicate keywords
- [ ] Reviewed by C1 (fjingran) on the PR

## Progress log
- 2026-10-15 10:09 - plan written; branch c3/6-topics-taxonomy created
- 2026-10-15 10:10 - config/topics.yaml written (19 topics, 7 top-level); validation passed;
  pointer comment added in config/entities.yaml. Dropped a year-specific keyword from
  transfer_estimates (ground rule 4). PROGRESS.md left to the bot per CLAUDE.md.
- 2026-10-15 10:21 - review changes: tagging rules in header (whole-word match; sub-topic
  keywords only with a parent hit; generic words listed); removed duplicate keywords
  ("next generation" now only wealth_transfer, "heirs" only parent, "cash sweep" only
  fee_disclosures; "best interest" overlap kept and declared); advisor_selection moved to
  top level and added to entities.yaml themes. Validation passed, no duplicate keywords.
- 2026-10-15 10:24 - verify-cee: ask-answer, open-citation, gap-path, invalid-chunk PASS;
  download-document UNREACHABLE (raw file not in data/raw/ locally, unrelated). pytest 68 passed.
  No code reads topics.yaml yet, so Q16-Q21 retrieval is unchanged until tagging lands.
