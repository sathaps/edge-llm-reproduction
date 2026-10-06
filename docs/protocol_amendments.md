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

## Amendment 3, 2026-10-06: the second corpus is deferred

What. The second corpus named in the protocol is not run now. Whether to run it is decided by Sathappan after E1, E2, E3 and E4 are complete. If it is run then, it is reported as added after the main results were seen. Until the decision, we do not scan for a second manual and we write no questions for one. Results are reported for one manual, the Cummins CFP11E manual, and the article states this as a limit. The Fulton files stay in the repository unchanged and are marked in the README as prepared and not used so far. The entries for a second corpus in `PROTOCOL.md` and `manuals/corpora.txt` describe the earlier plan and are not run now.

Why. The article is aimed at a magazine. A second corpus would cost two more marking sittings for a result that the article does not depend on.

State when decided. No E1 answer had been collected or read. `results/e1/` did not exist. The file is outside the manifest and no frozen file changed. An earlier version of this entry said the second corpus was dropped. That was corrected the same day.

What stands. E1 with three repeats, E2 with the period-window cell of Amendment 1, E3, E4, the blind marking of all E1 repeat 1 answers by Sathappan, and the second marker's sample of 60.

## Amendment 4, 2026-10-06: `unsupported_content` is not marked in E1 repeat 1

What. The marking field `unsupported_content` is not marked in E1 repeat 1. It needs the retrieved text, and the blind sheet may not show retrieved pages, so it is not on the sheet and no second sitting is prepared for it. Whether to mark it, on all answers or on a sample, is decided by Sathappan after E1 to E4 are complete, together with the decision on the second corpus. Until then no claim in the results rests on it. The three other fields and the sheet layout follow the frozen marking rules. The sheet adds the reading columns `required_elements` and `forbidden_elements`, because the frozen rules define `complete` and `respects_applicability` against them. `respects_applicability` is greyed and blank outside applicability questions.

State when decided. No marks exist. The file is outside the manifest.

## Amendment 5, 2026-10-06: the five unreadable-page questions run as a separate small run

What. The five questions of `questions/cummins_cfp11e_unreadable.csv` are not in E1 and not on the marking sheet. They run on the six E1 cells, three repeats, with the same pipelines and settings as E1, from `experiments/e1_unreadable.json` and `.github/workflows/e1-unreadable.yml`, both outside the manifest. Results go to `results/e1_unreadable/`. They are scored by the automatic scorer only and are labelled that way in every table. A second tab on the marking sheet is built only if the paper session asks.

Each run answers the five questions in one conversation, so the conversation history differs from the 40-question E1 run. Their answers are not paired with the E1 answers.

State when decided. No E1 answer had been marked.
