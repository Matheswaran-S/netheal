# Audit report

Scope: self-review of the code as delivered. Items marked **verified** were executed;

## What was and was not executed
- **Verified:** 35 pytest-style tests pass against the engine. They were run with a *local stand-in* for SimPy
  (Environment / process / timeout / run) and a minimal pytest runner, because the build sandbox had no network.
- **Verified:** scenario runs, CSV export and the dashboard control flow (executed against stubbed Streamlit/Plotly).The real `streamlit run app.py` UI, real Plotly rendering and real SimPy. Run them locally first.

## Findings

| # | Severity | File | Problem | Why it matters | Fix / status |
|---|---|---|---|---|---|
| 1 | HIGH | whole project | Real SimPy/Streamlit/Plotly not executed during the build | A version-specific API mismatch could appear only on first local run | Run `pip install -r requirements.txt && pytest && streamlit run app.py`; fix anything that surfaces |
| 2 | MEDIUM | core/simulation.py | One shared seeded RNG: after a failure, runs with/without recovery consume draws differently | The two runs are not perfectly paired samples (same seed, same failures, different loss draws) | Documented; per-packet RNG streams would pair them exactly |
| 3 | MEDIUM | core/simulation.py | Recovery time is the configured detection + compute delay (25 ms), not emergent | Must not be presented as a measurement of a real protocol | Documented in README/viva docs |
| 4 | MEDIUM | core/simulation.py | No queueing or bandwidth contention; `bandwidth_mbps` is informational | Throughput equals delivery rate, not a capacity effect | Documented as a limitation |
| 5 | LOW | core/simulation.py | Rerouted packets can backtrack (e.g. A>B>A>C>E>F) | Looks odd but is correct hop-by-hop behaviour when B's only other link is dead | Explained in docs |
| 6 | LOW | visualization/dashboard.py | Results are from the last run; sidebar edits do not auto-rerun | Could show stale numbers | Fixed: warning banner when config differs from last run |
| 7 | LOW | scenarios | Scenario failure times assume the default 20 s duration | Other durations shift the story | Documented; times are editable in the Failure tab |

Fixed during development: initial defaults (100 s, 50 ms detection) produced zero rerouted packets; defaults were
retuned (20 s, 20 ms + 5 ms) so in-flight rerouting is actually exercised and covered by a dense-traffic test.
