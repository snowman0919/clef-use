# Failure taxonomy and next evidence

| Class | Check next | Do not do |
|---|---|---|
| INSTALL/MODIFIED | managed hash, profile, existing edits | overwrite user files |
| NOT_DISCOVERED | effective provider root, toggles, duplicates | assume all hosts scan the same tree |
| NOT_LOADED | fresh harness trace, actual body read | accept filename echo as proof |
| SCHEMA_MISMATCH | installed live schemas and guide compatibility | call proposed APIs |
| TARGET_ABSENT | independent target presence and coverage@K | choose the least bad unrelated target |
| AMBIGUOUS | competing targets, state, original resolution | reduce confidence threshold |
| STALE | frame/state/window/editor version | reauthorize the old point with a new hash |
| WRONG_CONTEXT | mode, text focus, keymap, modal state | blindly retry a shortcut |
| INPUT_UNSUPPORTED | actual input capabilities and OS permission | bypass through hidden shell execution |
| NO_EFFECT | independent postcondition/readback | equate mouse delivery with success |
| FALSE_COMPLETION | fresh goal/condition evidence | use cached data as final proof |
| DEADLINE_MISS | queue/model/parser/input timeline | report quick failure as useful reaction |

Do not retry a timeout by starting the same task blindly. Check whether the
original session is still running. A request ID, task ID, and session ID should
remain traceable through retries.

For releases, compare the executable actually launched by the harness with the
expected active release. A source checkout test does not validate the installed
launcher, managed skills, or cached running worker.
