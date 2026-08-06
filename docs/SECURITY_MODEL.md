# Lore Security Model

Lore is a data-package tool. Its default trust boundary is deliberately small:
it verifies and installs immutable data; it does not execute package code or
operate on a Qualiant's memory service.

## Trust layers

1. **Transport integrity** — the archive arrives intact.
2. **Artifact integrity** — every file matches `checksums.json`.
3. **Publisher authenticity** — the manifest or release record has a valid
   Ed25519 signature from a trusted publisher.
4. **Provenance** — every record identifies its source and transformation path.
5. **Distribution authorization** — scope, license, entitlement, and locality
   permit the requested installation.
6. **Runtime compatibility** — the consumer accepts the schema and embedding
   contract.

Failure at any layer is a verification failure, not a warning.

## Package threat model

Lore must defend against:

- tampered archives and substituted packages;
- stale or mismatched manifests;
- hidden executable payloads and install hooks;
- accidental private-data distribution;
- source-license and embedding-license violations;
- path traversal and writes outside the Lore root;
- package confusion and dependency substitution;
- embedding/model incompatibility;
- a package being mistaken for canonical memory.

Inspection and installation are offline-safe. The package may contain text,
metadata, vectors, signatures, licenses, and validation fixtures, but no
executable installation behavior.

## Memory isolation

Lore owns only its package installation root. It must not discover, open, scan,
index, mutate, or delete Nephesh databases or other memory stores. A future
explicit adapter may export a package into a named knowledge projection, but
that adapter is outside the package installer and must preserve package ID,
version, provenance, scope, and installation authority.
