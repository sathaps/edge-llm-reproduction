# Protocol amendments

An amendment is added after the freeze of `protocol-v1`. It never changes a file in `protocol-v1.manifest`, and the tag does not move. Each entry gives the date, what is added, why, and the state of the results at the time.

## Amendment 1, 2026-10-06: E2 cell with the original window

What. One E2 cell is added: B on llama3 with `num_ctx` 2048, everything else as in E1 (same questions, same Cummins manual, settings of the B-llama3 cell (all-minilm embeddings), temperature 0, seed 42, 3 repeats). Name: E2k. Its planned comparison, number P17, is E2k against the B-llama3 baseline of E1, paired by question, McNemar exact test on the marked outcome, with the Holm correction applied over all planned comparisons including P17.

Why. On Ollama 0.3.14, the period of the original builds, llama3 ran with a 2048 window and the B prompt was cut to 1036 tokens from 3 pages up (run 37387498181, `results/notes.md`, check 3 addition). On 0.35.1 the window is 4096 and a B prompt of 5 pages can fit. E1 as frozen is therefore milder than the original on this point. E2k restores the original window on the current software.

State when added. No E1 answer had been collected or read. At this time the cells of run 37394227689 and of the A-mistral rerun 37395147521 were still running, and `results/e1/` held no files. The file `docs/protocol_amendments.md` is not in the manifest. `experiments/comparisons.json` and `experiments/e1.json` are in the manifest and are not changed. The cell is wired into `experiments/e2.json` and the comparison into a file outside the manifest only after E1 repeat 1 is collected.

Commit: recorded in `results/index.md` under `amendment-1`.

## Amendment 2, 2026-10-06: survival probe by token arithmetic

What. `scripts/check_survival_tail.py` and the workflow `survival-tail.yml` are added. The check sends the tail of the probe prompt alone and compares its `prompt_eval_count` with the tokens used by the full prompt. It also records where B's grounding instruction sits and which endpoint B calls. No frozen file is touched and no E1 cell is affected.

Why. A model that misses a code is weak evidence that the text was cut. The token count does not depend on what the model says.
