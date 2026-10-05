# Manual candidates

The `manual-models-budget` workflow downloaded each candidate from its public URL on 2026-10-05 and recorded the file's checksum, page count and text. Run 37375097339, commit 05615c8. The table with the sizes and checksums is `results/run-37375097339-manual-models-budget/manuals.csv`. No manual is committed to the repository.

## Criteria

From `PROTOCOL.md` section 4. The manual is civilian. It covers industrial process or rotating equipment such as a compressor, generator set, engine or boiler. It has 100 pages or more. It has procedures with prerequisites and numbered steps, tables of limits or settings, and at least one passage that applies to some models and excludes others. It is publicly downloadable.

## Result

| Candidate | Pages | Extractable text | Passages that limit a statement to some models or variants |
|---|---|---|---|
| Fulton Endura XE (EXE) 399 to 6000 | 132 | 594,808 characters | 4 explicit passages found (below) |
| AERCO Benchmark 5000/6000 | 144 | 329,262 characters | 1 serial-number range on the cover; no explicit exclusion among the 4 matches |
| Cummins Onan HDKAG | 44 | 101,689 characters | Fails the 100-page criterion |
| TM 9-6115-464-12 (Army, fallback) | 365 | 767,295 characters | Several, for example the frequency rheostat that works on two of three models |

## Adopted provisionally: Fulton Endura XE (EXE)

- Source: `https://fulton.com/app/uploads/2024/10/EXE-399-6000-IOM-260706.pdf`, the Installation, Operation and Maintenance manual for the Endura XE boiler, capacities 399 to 6000 MBTU/hr. The file name carries the date 2026-07-06, and the PDF creation date is the same.
- Downloaded 2026-10-05. SHA-256 `567d20d51cca6e8230c950eb4f32325c2f8ebc1c67946d7f1acf74e3b68378ab`. 14,443,052 bytes.
- Terms: the pages carry "© Fulton Group N.A., Inc. 2026", and PDF page 132 contains the line "may be reproduced in any form or by any means without". The rest of that sentence was not captured. We read it as a prohibition on redistribution without permission, so the manual is fetched in the job and never committed. Short quotations with page numbers are used as evidence.

Passages that apply to some variants and exclude others. Page numbers are PDF page numbers, not the printed ones.

1. PDF p6: "For capacities 399 to 750 MBTU/hr, this manual applies only to the new style (MKII) with hinged front cabinet door."
2. PDF p68, note 6 to a table: "For capacities 399 to 750 MBTU/hr, this table applies only to the new style (MKII) with hinged front cabinet door."
3. PDF p85: "NOTE: The following instruction applies to direct spark ignition systems only."
4. PDF p86: "NOTE: The following instruction applies to interrupted pilot ignition systems only."

PDF p68 and p87 also hold tables of values (fuel input rates, torque values). Procedures with prerequisites and numbered steps, and the ones that cross a page boundary, are checked when the questions are written.

## Fallback: TM 9-6115-464-12

US Army manual for the 15 kW generator sets MEP-004A, MEP-103A and MEP-113A, from the mirror `https://manuals.chudov.com/Military-Generators/MEP-004A/TM-9-6115-464-12.pdf`. SHA-256 `41848ede74e77553d4c2c3fee373ea6a06d2f0bb699f26b5ea7aaf825f8d861c`. The cover pages (PDF p1, p2 and p4) carry "DISTRIBUTION STATEMENT A: Approved for public release; distribution is unlimited". PDF p29 says that the frequency adjust rheostat "is functional only on models MEP-103A and MEP-113A".
