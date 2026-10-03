# Release and hosting

CI builds offline wheel bundles for macOS arm64/x86_64, Linux arm64/x86_64, and
Windows x86_64 on Python 3.11, 3.12 and 3.13. A tag such as `v0.1.3` must match
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
releases/0.1.3/manifest.json
releases/0.1.3/SHA256SUMS
releases/0.1.3/install.sh
releases/0.1.3/install.ps1
releases/0.1.3/clef-use-0.1.3-<platform>-<architecture>-py<minor>.zip
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

Public bootstrap scripts were HTTP 200, but latest manifest/SHA256SUMS were HTTP
404. A full public install remains unverified until the deployment route uploads
complete metadata and archives. GUI acceptance is also explicitly deferred by
the operator; these gates prevent a release-ready claim or final version tag.
