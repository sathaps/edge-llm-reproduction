# Manual candidates

Status: the manuals below are proposed, not yet verified. We verify page count, checksum, licence wording and applicability passages in a job that downloads each PDF from its public URL. Results are recorded here after the job runs. No manual is committed to the repository.

## Criteria

From `PROTOCOL.md` section 4. The manual is civilian. It covers industrial process or rotating equipment such as a compressor, generator set, engine or boiler. It has 100 pages or more. It has procedures with prerequisites and numbered steps, tables of limits or settings, and at least one passage that applies to some models and excludes others. It is publicly downloadable.

## Civilian candidates

| # | Manual | URL | Equipment | Models covered |
|---|---|---|---|---|
| 1 | AERCO Benchmark 5000/6000 Boiler, Installation, Operation and Maintenance manual | https://www.aerco.com/dfsmedia/0533dbba17714b1ab581ab07a4cbb521/82016-source/638235481930000000/benchmark-5000-6000-iom-manual-omm-0124-gf-208-n-19-0001-and-above.pdf | Boiler | Benchmark 5000 and 6000; the title restricts it to a serial range |
| 2 | Fulton Endura XE (EXE) Installation, Operation and Maintenance manual | https://fulton.com/app/uploads/2024/10/EXE-399-6000-IOM-260706.pdf | Boiler | EXE sizes 399 to 6000 |
| 3 | Cummins Onan Operator Manual, Commercial Mobile Generator Set HDKAG (Spec A to K) | https://www.cummins.com/sites/default/files/2024-10/0981-0149-i12-hdkag-ops-manual.pdf | Generator set | Spec letters A to K |

Page counts and applicability wording for these three are not yet known to us. Candidate 3 may fall under 100 pages. The terms of use for each manual are read from the PDF in the verification job.

## Fallback

TM 9-6115-464-12, Operator and Unit Maintenance Manual, 15 kW diesel generator sets MEP-004A, MEP-103A and MEP-113A. This is a US Army manual with a public-release distribution statement according to secondary sources. It is a fallback only. The `manual-models-budget` workflow fetches it with the civilian candidates.

## Verification record

To be filled in from the job output: source URL, sha256, page count, cover or licence wording, and two quoted applicability passages with page numbers per manual.
