# Release and hosting

CI builds offline wheel bundles for macOS arm64/x86_64, Linux arm64/x86_64, and
Windows x86_64 on Python 3.11, 3.12 and 3.13. A tag such as `v0.1.5` must match
`pyproject.toml`. The release workflow merges per-platform artifacts/checksums
into one site tree. Untested ML/desktop platforms remain experimental even when
packaging succeeds. Windows ARM64 has no release target yet.

```sh
uv run --no-sync python scripts/build_release.py --output release-site
uv run --no-sync python scripts/check_installation.py --site release-site
```

Upload the **contents** of `release-site/` beneath the HTTPS server directory
serving `https://ftp.kotori9.dev/clef-use/`:

```text
install.sh
install.ps1
latest/manifest.json
latest/SHA256SUMS
releases/0.1.5/manifest.json
releases/0.1.5/SHA256SUMS
releases/0.1.5/install.sh
releases/0.1.5/install.ps1
releases/0.1.5/clef-use-0.1.5-<platform>-<architecture>-py<minor>.zip
```

Upload immutable version artifacts first, verify public SHA-256 and content,
then replace `latest/` metadata and bootstraps. Keep earlier releases available.
Never edit the checksum for an already published version. Use an atomic server
rename or the hosting provider's equivalent to switch metadata. Credentials and
production deployment are intentionally not stored in workflows. GitHub releases
are an additional distribution artifact, not a different update protocol.

Enable Issues, Discussions, Actions, releases, private vulnerability reporting,
and automatic merged-branch deletion. Main is the default branch. Require reviewed
PRs and passing CI once collaboration begins; prevent force pushes/deletion.
For a solo initial repository, document protection recommendations instead of
blocking necessary bootstrap commits with unavailable reviewers.


## Validated delivery tree

The local site `release-site/` retains immutable 0.1.0, 0.1.1, 0.1.2 and 0.1.3
releases, 15 native platform/Python artifacts each. All 60 archive hashes were
verified. Latest 0.1.3 comes from successful Actions run 37143721968, source
000885b8260eed2a1923e15edf6c6530487de325. CI run 37143721190 passed six jobs.

The transfer archive `dist/clef-use-release-site-0.1.3.tar.gz` contains the new
version directory, latest metadata and both bootstrap scripts (379,631,809 bytes).
Its adjacent `.sha256` records:

```text
d82252a628f9b65567c91341d4265c7438710ae6e24328b1c5dd82eea93bb114
```

Extract its contents below the directory serving `/clef-use/`, preserving all
earlier server release directories. Publish the immutable 0.1.3 directory first,
then switch latest metadata/bootstraps atomically. The complete local tree also
contains earlier versions if the host needs those files. Do not regenerate an
already published version with different hashes.

The exact assembled Mac archive updated the installed user launcher to 0.1.3;
repeat runs returned CURRENT and config bytes remained unchanged. Windows 11 SSH
passed 48 tests and native Unicode-path PowerShell installation/CMD update plus
three failed-update preservation checks. Synthetic test version 0.1.4 is isolated
and is not a published release.

Public HTTPS latest metadata now returns HTTP 200 with 0.1.3 and 15 targets.
Isolated macOS/Windows public installs and self-tests passed; the earlier 404
metadata blocker is resolved for 0.1.3. New 0.1.5 public deployment is pending.

## Source 0.1.5 validation

Source `bd217b06868f49b963b37b21b0d9535ccea24baa` passed all six jobs in
[CI 37159015133](https://github.com/snowman0919/clef-use/actions/runs/37159015133).
The installed noneditable Windows wheel and final published source passed 83
regressions. Real Windows input and screenshot readiness checks passed on the
owned disposable GUI; Mac foreground input remains deferred.

The initial 0.1.5 real model task made two correct native Windows actions and
visible app completion, but MPS failed during final CLEF verification. Subsequent
failed comparisons are retained; no actual warm samples or measured speedup are
claimed. Windows-local model inference remains NOT_RUN. Package/CI success does
not establish model reliability or arbitrary-app readiness. See
VISUAL_READINESS.md and evidence/VALIDATION.md.

[Release workflow 37159016423](https://github.com/snowman0919/clef-use/actions/runs/37159016423)
completed all 15 native bundles and assembly from that exact source. All 15 new
archive hashes and 60 prior immutable hashes were verified. The local tree now
retains those previous versions and adds 0.1.5. No published version checksum was
changed. The upload archive `dist/clef-use-release-site-0.1.5.tar.gz` contains only
new 0.1.5 artifacts, latest metadata and both bootstraps (379774706 bytes).
Its SHA-256 is:

```text
f6145b1dcfc0553d971fb0f21daa95c249b538e3e1ae6972968b0b4f374cb66a
```

See evidence/release-015-platforms.json. Upload immutable 0.1.5 files first and
verify them before switching latest metadata. The public server still serves
0.1.3, so new public install/update acceptance remains pending. Native GUI success
and CI do not resolve the documented CLEF MPS execution failures.
