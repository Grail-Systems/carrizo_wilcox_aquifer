# Updating the Records Requests page

When something happens on a request, add an event to frontend/records.json
and update that request's "clock" block too:

| Event | Clock change |
|---|---|
| An agency gives a ready date | add "certified": "YYYY-MM-DD" |
| An agency goes to the Attorney General | add "ag_requested": "YYYY-MM-DD" |
| ETLC answers an agency's clarification questions | set "start" to that date and "start_note" to what happened |
| A request is finished | set "state": "done"; the clock stops |

The nightly job (data-engine/pia_deadlines.py) recalculates every deadline,
shows it on the Records page, and opens a GitHub issue (which emails Fawn)
when one passes. Deadlines skip weekends and Texas state holidays and are estimates.
