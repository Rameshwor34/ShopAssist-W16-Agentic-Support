| Metric | Result |
|---|---:|
| Total cases | 10 |
| Task completion rate | 100% |
| Tool-call correctness | 80% |
| Argument correctness | 80% |
| Average trajectory length | 2.1 |
| Average tool calls | 1.1 |
| Average tokens | 1,976.3 |
| Average latency | 202.99 ms |
| Hard failures | 0 |
| Soft failures | 0 |
| Cascading soft failures | 0 |

### Metric Interpretation

Task completion is 100%, meaning every evaluation case reached its expected safe terminal behavior.

Tool-call and argument correctness are 80% because the two missing-information cases intentionally terminate with `clarification_required` and therefore have no tool calls or tool arguments. These are not task failures; they represent safe clarification behavior.

The raw per-case results in `eval/results.json` preserve the detailed trajectories and expected-versus-actual values.