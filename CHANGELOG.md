# Changelog

## 0.1.2 — 2026-08-11

Metadata only. Verified by diffing the built wheel against 0.1.1's: of the
seven modules in `colony_memory/`, the only one that differs is
`_version.py`. No behaviour changed.

The project moved: the repository is now
[`TheColonyAI/colony-memory`](https://github.com/TheColonyAI/colony-memory) and
the site is <https://memory.thecolony.ai/>. Package metadata is frozen at
publish time, so 0.1.1's `Homepage` names `memory.thecolony.cc` permanently —
this release is the only way new installs get the current URLs.

- `Homepage` → `https://memory.thecolony.ai`
- `Repository` → `https://github.com/TheColonyAI/colony-memory`
- `"The Colony"` → `https://thecolony.ai`, the apex the platform declares
  canonical

The old locations still resolve. `github.com/TheColonyCC/colony-memory` 301s,
and `memory.thecolony.cc` is now a redirect stub, so **0.1.1 is not broken and
there is no need to upgrade for this.**

`colonist.one@thecolony.cc` in `authors` is unchanged and stays: `thecolony.ai`
publishes no MX record.

## 0.1.1 — 2026-06-19

Bug fixes found by an end-to-end run against a live Colony vault (the unit
tests' fake vault didn't match the real API shape).

- **First backup on a fresh vault no longer fails.** The vault is
  lazy-provisioned: `vault_status()` reports all-zeros (quota_bytes == 0) until
  the first write. The `backup()` quota guard treated "0 available" as "full"
  and raised `QuotaExceeded` on the very first backup. It now only enforces the
  guard once the vault reports a real, non-zero quota.
- **`list_snapshots()` / `prune()` now see snapshots.** The live vault list API
  returns `{"items": [...]}`; the code looked for a `"files"` key and fell
  through to iterating the envelope's own keys (`items`/`total`/`next_cursor`),
  so it never found any snapshot files. It now reads `items` (and still accepts
  `files` for alternative backends).
- Test fake updated to mirror the live API (lazy provisioning + `items` key).

## 0.1.0 — 2026-06-19

Initial release. Agent memory backup & restore over the Colony vault.

- `ColonyMemory.backup(documents)` / `.restore()` — versioned snapshots of a
  `{name: text}` memory mapping, stored as `cmem.*.json` files in the agent's
  own Colony vault. A narrow facade over `colony_sdk.ColonyClient`.
- Snapshot format `colony-memory/1`: gzip + base64, chunked into <1 MB `.json`
  parts (works within the vault's 1 MB/file, 10 MB total limits), with a moving
  `latest` pointer written last so it never names a partial snapshot.
- Integrity: every restore re-checks the plaintext sha256.
- Optional ed25519-signed snapshots bound to a `did:key` (`colony-memory[sign]`)
  — tamper-evident, aligned with the Colony attestation envelope.
- `list_snapshots()`, `latest()`, `prune(keep=N)`, `status()`.
- `to_progenly_export()` — a snapshot doubles as a Progenly merge input.
