# Release and hosting

CI builds offline wheel bundles for macOS arm64/x86_64, Linux arm64/x86_64, and
Windows x86_64 on Python 3.11, 3.12 and 3.13. A tag such as `v0.1.1` must match
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
releases/0.1.1/manifest.json
releases/0.1.1/SHA256SUMS
releases/0.1.1/install.sh
releases/0.1.1/install.ps1
releases/0.1.1/clef-use-0.1.1-<platform>-<architecture>-py<minor>.zip
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

The local final site is `release-site/`, assembled from native GitHub Actions
run 37137294737 at revision 7c734f1. Latest is 0.1.1, with 15 native offline
bundles; the verified earlier 0.1.0 tree is also retained. Every archive matches
its recorded SHA-256. Upload the entire contents, including both bootstrap files,
`latest/manifest.json`, `latest/SHA256SUMS` and the `releases/` directories.

A transfer bundle is available locally at
`dist/clef-use-release-site-0.1.1.tar.gz`, with adjacent `.sha256`. It is a hosting
site transfer archive, not an extra installer payload. Use the exact validated
archives; do not regenerate a previously published version with different hashes.
The site tree and transfer archive are generated outputs excluded from Git.

The currently served bootstrap scripts return HTTP 200 but predate the release
client User-Agent correction. `latest/manifest.json` and `latest/SHA256SUMS`
return 404. The public POSIX installer therefore still fails in an isolated test;
refresh the full tree before declaring public deployment ready.
