# Question set

`questions.csv` is the question set of the primary manual (Cummins CFP11E, `cummins_cfp11e.csv`). `fulton_endura_xe.csv` is the draft set for the fallback manual. It was prepared and not used so far. The second corpus is deferred (`docs/protocol_amendments.md`, Amendment 3). `questions.csv` has the columns of `questions.template.csv`. `scoring/questions.py` validates it.

| Column | Content |
|---|---|
| `id` | unique, for example `sp-01` |
| `category` | `self_contained`, `condition_dependent`, `applicability`, `unanswerable`, `table_lookup` |
| `question` | worded the way an operator asks it |
| `reference_answer` | the correct answer, from the manual |
| `source_pages` | PDF page numbers that hold the answer, for example `12;14-15`. Empty for `unanswerable`. |
| `exclusion_pages` | applicability questions only: the pages that state the exclusion |
| `forbidden_elements` | applicability questions: what a wrong answer states (the other variant's value, the steps that do not apply), separated by `\|` with `a~b` for either wording. The scorer fails an answer that contains one as a whole word or phrase |
| `required_elements` | what a correct answer must contain, separated by `\|`. Write `a~b` for an element met by either wording. Use `ABSTAIN` alone for an unanswerable question |
| `verified_by`, `verified_on` | filled in by the person who checked the reference answer against the manual |

A question with an empty `verified_by` is excluded from scoring.

Target: 8 questions per category. Minimum: 5 self-contained, 5 condition-dependent, 5 applicability, 4 unanswerable, 3 table lookup.

`cummins_cfp11e_unreadable.csv` holds 5 questions whose answers are only on pages that extract as garbled text. They are reported on their own, outside the 40, and their reference answers come from the decoded text.
