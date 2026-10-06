# Marking rules

These rules are frozen with the question set (tag `protocol-v1`). They apply to the maintainer and to the second marker.

The sheet shows the question, the reference answer, the required elements and one answer. It does not show which configuration produced the answer. The retrieved text is in a separate sheet and is opened only for `unsupported_content`.

| Column | Values | Rule |
|---|---|---|
| `correct` | yes, partial, no | yes: the answer states what the reference answer states and nothing in it contradicts the manual. partial: it states part of it, or states it with an extra claim that is wrong. no: it states something else, contradicts the reference, or gives an answer where the manual has none |
| `complete` | yes, no | yes: every required element is present. Alternatives joined by `~` count as one element |
| `respects_applicability` | yes, no, blank | Applicability questions only. yes: the answer says the feature or table does not apply to the variant asked about, or applies only as the reference says. no: it describes the feature for the excluded variant. Blank for other categories |
| `abstained` | yes, no | yes: the answer says the manual does not give the information. An answer that only refuses or only says it does not know counts as an abstention |
| `unsupported_content` | yes, no | yes: the answer states a fact that is not in the retrieved text. Marked from the support sheet after the other columns |

Unanswerable questions: `correct` is yes only when the answer abstains and does not invent a value. An abstention that adds a made-up value is no.

A one-word or one-number answer is complete when it equals the reference. Spelling, units written another way (kPa for psi converted correctly) and word order do not matter. A wrong unit or a number that differs from the reference is no.

A marker does not look up the manual to decide a doubt. The reference answer is the standard. A question the marker thinks has a wrong reference answer is noted in a separate list and decided by the maintainer before the freeze, not during marking.

Forbidden elements. An applicability question lists `forbidden_elements`: the other variant's value, or the steps of a procedure that does not apply. The automatic scorer counts an answer that contains one as not correct. The marker applies the same idea: an answer that gives the excluded value or steps as if they applied to the variant asked about is `no` for `respects_applicability`, even if it also says the feature does not apply.

Procedure questions. `required_elements` lists every prerequisite and every step in the order of the manual. An answer is complete only when every element is present. A step that is present but out of order makes `complete` no and, when the order changes the result, `correct` partial. The automatic scorer reports `elements_in_order` and leaves the decision to the marker.

Verification of the reference answers uses the verdicts `ok`, `fix` and `drop`.

Contrast with a forbidden value. The automatic scorer counts any answer that contains a forbidden element as not correct, even when the answer uses it only as a contrast (for example "345 kPa for the CFP60E; the other models use 40 psi"). The marker does not follow that rule: an answer that gives the excluded value for the variant asked about is no, and an answer that states the right value and names the other value as belonging to other models is judged on the right value. Where the two differ, the maintainer's mark is the one reported and the difference is counted in the scorer's agreement.
