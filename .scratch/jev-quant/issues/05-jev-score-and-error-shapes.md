# Jev score and error response shapes

Type: task
Status: wontfix
Blocked by: 

## Question

The guide documents `choice` and `noul` answers but not the `score` answer, or the error bodies for 401 / 404 / 429 / 5xx / invalid schema. Make a few live calls (free model `jev-1.13-free`) and record the exact shapes, plus latency and whether a JSON object `state` works. AFK if `OPENCODE_API_KEY` is set in the environment; otherwise HITL: the user exports the key or runs the calls.
