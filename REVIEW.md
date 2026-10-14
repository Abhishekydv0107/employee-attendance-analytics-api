# REVIEW.md

## Confirmed implementation findings

| # | Where (function / line) | What is wrong | How you'd notice it (test, input, or symptom) | How you fixed it |
|---|---|---|---|---|
| 1 | `punch_in()` and startup indexes | Duplicate punch-in requests for the same employee and attendance date must not create duplicate records. | Send two punch-in requests for the same employee and date; the second request should return HTTP 409. | Added a unique compound index on `(emp_code, date)` and handled `DuplicateKeyError` as HTTP 409. |
| 2 | `regularize_attendance()` | Concurrent corrections must not silently overwrite another correction's history. | Two corrections based on the same previous record should not both overwrite its history. | The update matches the existing history and returns HTTP 409 if the record changed concurrently. |
| 3 | `regularize_attendance()` | Attendance corrections must keep derived values and the audit trail consistent with the corrected record. | Correct punch times or status and verify derived fields and history. | Recomputes derived fields, records actual changes, and appends an audit entry. |

## Tests run

- `python -m py_compile app\main.py` passed.
- Employee listing returned HTTP 200.
- Attendance listing and combined employee, status, and date filters returned HTTP 200.
- Department summary and late leaderboard returned HTTP 200.
- The late-leaderboard explain endpoint returned HTTP 200 and showed an index scan.

## Reviewed behavior

- The attendance helpers contain explicit logic for overnight shifts, late minutes, work hours, and overtime.
- The current tests do not establish that every original starter defect has been found.
- The items above describe implemented protections; compare with the original starter before claiming they were all defects in that version.