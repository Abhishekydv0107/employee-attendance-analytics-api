# DECISIONS.md

1. **Indexes.** I create a unique index on `employees.emp_code` so employee codes cannot be duplicated. I also create a compound index on `employees.department` and `joined_on` for department and employment-date queries. On attendance logs, a unique compound index on `(emp_code, date)` guarantees one record per employee per attendance day. I also create indexes on `(date DESC, emp_code ASC)` for attendance listing and `(emp_code, date, status)` for employee attendance lookups. I would review query plans on the grader-sized dataset before deciding whether every index is necessary.

2. **Punch-in race.** Two identical punch-in requests may both pass the employee lookup and build a record. The unique `(emp_code, date)` index allows only one insert for that employee and day. The losing insert raises `DuplicateKeyError`, which the endpoint converts to HTTP 409.

3. **Ties.** The leaderboard sorts by total late minutes descending and employee code ascending. Employees with equal totals receive the same competition rank. The limit is applied to rank, so tied employees at the cutoff can all be included.

4. **Headcount.** Department headcount is based on employees and their joining dates, not only employees with attendance logs. This allows employees with zero logs to be counted.

5. **100x data.** I would benchmark the aggregation pipelines against a larger dataset, inspect explain plans, and adjust indexes or aggregation stages based on the measured bottlenecks.