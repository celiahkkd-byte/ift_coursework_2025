# Project Issues and Status

This file tracks current actionable issues only. Historical role assignment text has been retired to avoid drift from implementation.

## Resolved

- [x] Source A and Source B integrated under `Main.py` extractor switch (`--enabled-extractors`).
- [x] Raw Source B news persisted in MinIO as monthly JSONL objects.
- [x] Pipeline audit migrated to PostgreSQL `systematic_equity.pipeline_runs` (JSONL kept as debug mirror).
- [x] Final-factor transform stage added (`modules/transform/factors.py`) and wired into pipeline.
- [x] CLI parser refactored into `modules/utils/args_parser.py`.

## Open

- [ ] Expand/validate end-to-end tests for final factors against fixed fixtures (especially `sentiment_30d_avg`).
- [ ] Add more explicit Sphinx API pages for transform and audit modules.
- [x] Persist `article_count_30d` as a daily transformed factor in `systematic_equity.factor_observations`.

## Constraints

- Do not modify `000.Database` content.
- Do not change teacher-provided root docker parameters for submission.
- Commit coursework deliverables under `team_Pearson/coursework_one/`.
