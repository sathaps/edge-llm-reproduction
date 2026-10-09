# E1 repeat 1: agreement of the automatic scorer with the maintainer's marks

Unit: the 237 distinct answers. The scorer ran without the retrieved text. `unsupported_content` is not marked and is not compared. Same mark = identical value. Kappa is Cohen's kappa over the values present.

| Field | Same mark | Same on yes versus not yes | Cohen's kappa | N |
|---|---|---|---|---|
| correct | 177 of 237 | 203 of 237 | 0.612 | 237 |
| complete | 217 of 237 | 217 of 237 | 0.804 | 237 |
| respects_applicability | 43 of 48 | 43 of 48 | 0.770 | 48 |
| abstained | 213 of 237 | 213 of 237 | 0.704 | 237 |

Scorer against maintainer for `correct` (rows scorer, columns maintainer):

| scorer \ maintainer | yes | partial | no |
|---|---|---|---|
| yes | 46 | 16 | 2 |
| partial | 6 | 47 | 10 |
| no | 10 | 16 | 84 |
