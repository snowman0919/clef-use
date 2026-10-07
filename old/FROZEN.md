# FROZEN — legacy implementation (V1 + partial hybrid-V2 WIP)

- Frozen at commit a2e677f (tag freeze-2026-10-08), 2026-10-08, per GOAL §1.
- This tree is NOT the design baseline for V2. Do not layer changes here.
- Selective porting rule: a module may be lifted from here into V2 only if
  (1) its tests pass unchanged against the ported copy, (2) the port is its own
  commit stating what was reviewed and what was intentionally left behind.
- Proven-priority ports: schema/config/interfaces (stable contracts),
  backends/windows_input/activity_* (input correctness, regression-tested),
  grounding/router/candidates (V2 intent, WIP — verify, do not trust).
- Everything else stays legacy: installer/maintenance/service/cli are re-derived
  from the frozen release pipeline contracts, not by continuing to edit them here.
