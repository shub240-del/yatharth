# Reproduce V0.2

From the project root with Python 3.12:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
python -m app.evaluation.run
python -m evaluation.v02.benchmark --out evaluation/v02/results-reproduced
pytest -q
```

Expected frozen run: 198 passed, 24 skipped, 98 xfailed. Xfails are unresolved provisional binary decision gaps, not fixes. Original 46 tests are preserved and hashes enforced. Data and engine hashes are emitted with results. Tests use isolated SQLite by default; use a disposable PostgreSQL database only when explicitly configuring that test path.

The default benchmark is offline and uses no provider. Source proposals can be regenerated with `python -m evaluation.v02.author_cases`; do not overwrite human-reviewed data. PROTOCOL.md defines labels before evaluation. Reports are explanatory snapshots of results/metrics.json, not new labels.

## Independent review

```sh
python -m evaluation.v02.review export --out evaluation/v02/new-review-packets
# Two different qualified humans independently complete their own packets.
python -m evaluation.v02.review merge --reviewer-1 completed-1.jsonl --reviewer-2 completed-2.jsonl --out evaluation/v02/reviewed
python -m evaluation.v02.benchmark --dataset evaluation/v02/reviewed/reviewed-cases.json --labels human --out evaluation/v02/results-human
```

No reviewers have completed these packets. Fill the identity/timestamp/attestation and annotation fields; for partial batches include only completed records. Actual identity/independence must be verified by the operator. Any label disagreement becomes AMBIGUOUS. Read docs/V0.2-DATASET.md before distribution. Do not expose proposals/predictions to reviewers.

```sh
python -m evaluation.v02.benchmark --labels human --out evaluation/v02/results-human-pending
```

On the supplied unreviewed set this produces zero evaluable human-labeled cases, with undefined metrics, not a substitute success result.

## Optional live model evaluation

Only after configuring an authorized HTTPS LLM_URL, LLM_API_KEY, and LLM_MODEL, pass `--ai` and a separate `--out` directory to the benchmark. This explicitly transmits the synthetic examples to that provider and may incur cost. The CLI rejects non-synthetic datasets in this path. Partial/fallback results are marked incomplete, not comparable AI performance. No live run was performed for the included report.

## Evidence map

- baseline/: original hashes, original46 SQLite tests, old100-case evaluation, environment blockers.
- results/: current metrics, all predictions, every model's binary failures, regression log.
- results/human-pending/: zero-ground-truth evaluation.
- known-gaps.json:98 frozen unresolved binary decision mismatches used by strict xfail tests.
- review-packets/: blank prediction-blind human packets.
- ../../docs/V0.2-*.md: conclusions, methodology, comparison and full Yatharth failure appendix.

Top-level app modules remain independently runnable and do not import evaluation/v02 or OpenWorker by default.

The historical docs/source-manifest.json describes V0.1. The package-level docs/V0.2-ARTIFACT-MANIFEST.json records the current files (excluding itself and runtime caches/databases).
