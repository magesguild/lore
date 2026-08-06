# Lore Format Decisions

These decisions define the target v1 format. Existing generated packages are
prototype artifacts and require migration before they are released as v1.

- **Package identity:** reverse-domain `package_id` plus independent SemVer
  `version`.
- **Archive:** deterministic `tar.zst` distribution artifact; unpacked package
  directories remain valid for local development and offline transfer.
- **Records:** UTF-8 JSONL with stable record IDs and explicit provenance.
- **Vectors:** little-endian `float32` binary matrix plus JSONL row index.
- **Integrity:** SHA-256 for every artifact and a signed manifest release.
- **Signatures:** Ed25519 for portable offline verification; registry trust and
  entitlement layers may be added later.
- **Licensing:** package license, source licenses, attribution, and embedding
  model terms are mandatory metadata.
- **Privacy:** every package declares generalized, private-family, licensed,
  or internal scope.
- **Authority:** every package declares `knowledge_not_memory: true`.
- **Installation:** staged, verified, package-isolated, and atomically pointed
  at by `active`.
- **Rollback:** pointer-only selection change within one package namespace.
- **Execution:** package inspection and installation execute no package code.
- **Memory:** Lore never touches a live memory store; importing knowledge into
  Nephesh is a separate explicit adapter operation.

The format is not considered finalized until these decisions have matching
schemas, migration rules, and tooling behavior. No validation suite is being
run during this design phase.
