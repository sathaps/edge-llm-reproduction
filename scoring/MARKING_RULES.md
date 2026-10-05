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
