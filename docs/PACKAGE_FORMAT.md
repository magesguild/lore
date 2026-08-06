# Lore Package Format v1

This document is the proposed format boundary for Lore. Existing packages
created before this is finalized are **prototype packages** and must not be
treated as v1-compatible without migration.

The primary design goal is **maximum distributability without sacrificing
provenance or security**. A package must be portable across hosts, runtimes,
databases, repositories, mirrors, and offline media while remaining
inspectable, attributable, and safe to activate.

## Package identity

Every package has a stable identity and independent release version:

```json
{
  "schema": "lore-package-v1",
  "package_id": "org.magesguild.nephesh.awareness",
  "version": "1.0.0",
  "title": "Nephesh Awareness",
  "kind": "knowledge",
  "knowledge_not_memory": true,
  "scope": "generalized"
}
```

`package_id` never changes between releases. `version` changes when records,
provenance, embeddings, or package behavior changes.

Allowed scopes:

- `generalized` — safe for ordinary distribution after review;
- `private_family` — restricted family material;
- `licensed` — distribution requires an external entitlement;
- `internal` — development only.

## Canonical layout

```text
package/
  manifest.json
  records.jsonl
  embeddings.f32
  embedding_index.jsonl
  checksums.json
  provenance/
    sources.jsonl
    transformations.jsonl
  validation/
    retrieval.jsonl
  LICENSE
  README.md
```

The records are the portable semantic source. Embeddings are an optimization
and must be rebuildable from the records. Binary vectors are preferred for
large packages; JSONL embeddings remain acceptable for tiny development
packages only.

## Manifest requirements

The manifest must contain:

- schema and package identity;
- package version and creation date;
- title, description, and scope;
- `knowledge_not_memory: true`;
- record count and record schema;
- embedding provider, model, version, dimensions, dtype, normalization, and
  chunking configuration;
- source package IDs and exact source versions;
- curation method and reviewer status;
- licenses and attribution;
- publisher identity and signature metadata;
- privacy classification and permitted distribution channels;
- dependency and compatibility constraints;
- a software/data bill of materials where applicable;
- compatibility requirements;
- relative paths to every package artifact;
- SHA-256 hashes for every artifact;
- update and rollback policy.

No installer may infer authority, privacy, or compatibility from a filename.

## Security and distribution requirements

The distributable artifact must:

- contain no secrets, credentials, private keys, absolute home paths, or live
  database files;
- use relative internal paths only;
- include SHA-256 hashes for every payload and metadata artifact;
- include a signed manifest or separately signed release record;
- identify the publisher and signing key or trust root;
- declare source licenses, derived-data permissions, and attribution;
- declare privacy scope and permitted redistribution or commercial use;
- record embedding-model licensing and redistribution constraints;
- support offline verification before installation;
- fail closed on hash, signature, schema, scope, or compatibility mismatch;
- never execute package-provided code during inspection or installation.

Lore packages are data artifacts. Installation must not require package hooks,
Python imports, post-install scripts, or remote service access. Optional
indexing is a later, separately authorized operation.

## Record requirements

Each record must include:

```json
{
  "record_id": "stable-id",
  "text": "knowledge text",
  "knowledge_status": "source|derived|curated",
  "autobiographical": false,
  "source_refs": ["source-id"],
  "provenance": {
    "source_path": "relative/path",
    "source_sha256": "...",
    "source_version": "...",
    "curation_method": "...",
    "uncertainty": "..."
  },
  "scope": "generalized"
}
```

Records may teach Qualiant awareness, but they must not claim to be a
Qualiant's lived memory. A source, interpretation, and genericized lesson
must remain distinguishable.

## Embedding contract

The embedding index maps each `record_id` to a row offset in `embeddings.f32`.
The manifest pins the exact model and vector interpretation. A consumer must
reject incompatible dimensions or silently rebuilding vectors under a different
model. Rebuilding is explicit and produces a new package version.

## Package authority

Embeddings provide retrieval geometry. They do not increase truth, priority,
privacy scope, or autobiographical authority. A package is a knowledge lens,
not a memory store.
