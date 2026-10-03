# Release and hosting

CI builds offline wheel bundles for macOS arm64/x86_64, Linux arm64/x86_64, and
Windows x86_64 on Python 3.11, 3.12 and 3.13. A tag such as `v0.1.0` must match
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
releases/0.1.0/manifest.json
releases/0.1.0/SHA256SUMS
releases/0.1.0/install.sh
releases/0.1.0/install.ps1
releases/0.1.0/clef-use-0.1.0-<platform>-<architecture>-py<minor>.zip
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
