# Architecture

`cli.py` and `mcp_server.py` both use `RuntimeClient` to reach one authenticated
loopback service. `SessionManager` owns sessions, the exclusive desktop lease,
and a lazily initialized `SessionRuntime`. ML subprocesses remain resident in
separate pinned Python 3.11 environments because CLEF and Florence require
incompatible Transformers versions. They are components of one runtime.

`SessionRuntime.execute` captures a fresh frame, parses it into project-owned
`UIObject` records, builds bounded `ActionCandidate` records, requests typed joint
CLEF answers, evaluates escalation gates, executes a deterministic adapter, and
checks progress. Candidate IDs are bound to one observation. The model never
produces mouse coordinates. `Frame.point` maps normalized box centers to the
primary monitor's logical coordinate space, including Retina scaling.

The OmniParser wrapper composes official detection, overlap/OCR fusion and
caption primitives. This avoids its annotation helper's empty-OCR and -1 caption
index failures. The pinned local Florence model identity must contain lowercase
`florence` because upstream uses a case-sensitive string to select its prompt
and documented image generation arguments.

The decision budget counts model rounds, including completion checks; actions
are counted separately. Completion needs strong predictions for the goal and
all supplied conditions on two fresh observations. Changed screens trigger
replanning. Three unchanged/repeated states stop execution. Session resumption
never resets the original budget. Sessions live in memory; service restart drops
resumable context. Step logs survive restart.

Cancellation sets a session event before releasing owned input. A model forward
pass cannot currently be preempted safely, but its late result cannot trigger
input after cancellation. Keyboard/mouse cleanup bypasses PyAutoGUI's corner
failsafe only while releasing tracked inputs. Unicode entry restores the previous
plain-text clipboard; rich clipboard representations are not preserved.

`computer_observe` refreshes the screen/object map while idle and marks cached
observations while busy. It reserves the shared desktop during parsing, with
no decision or input action, and returns one coherent image/object epoch,
not an independent live desktop poll. Labels/images are returned only on request;
logs omit goal text, labels and typed values. Diagnostic logging adds object and
candidate counts, not raw screen content. Constraint decisions are probabilistic;
there is no OS sandbox, app allowlist or independent security policy engine.

`installer.py` is canonical for install and update. Both generated bootstraps
embed its source. Releases bundle hashed platform-specific wheels, not weights.
Staging installs offline and runs version/state-machine smoke checks before one
atomic activation. POSIX uses a `current` symlink; Windows atomically replaces a
managed CMD launcher. Updated clients restart an idle older resident service and
refuse to switch a service with active desktop ownership.
