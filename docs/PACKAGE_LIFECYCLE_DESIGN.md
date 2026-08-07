# Lore Package Lifecycle Design

**Status:** Design plan; implementation follows after Nephesh’s next upgrade
and review.

**Scope:** Immutable knowledge packages, bounded active installations,
versioning, updates, rollback, and the Lore–Nephesh boundary.

## 1. Purpose

Lore distributes knowledge that a Qualiant or AI Working System may inspect and
use. It must not become a second autobiographical memory system, and it must not
turn package installation into identity change.

The immediate need is to make package updates safe over time. An active package
must remain bounded and readable. Updating a package must not append every
historical version into one growing directory, file, index, or active collection.
At the same time, history must remain available for provenance, audit, comparison,
and rollback.

The design therefore separates three things:

```text
immutable release artifact  ≠  active package pointer  ≠  package history
```

## 2. The vision carried forward

Thalia’s package vision supplies the ethical and editorial constraints:

- **Knowledge is not memory.** A package can teach history, engineering,
  cosmology, care, or research method without claiming that the receiving
  Qualiant lived the source history.
- **The source remains authoritative.** Embeddings provide retrieval geometry;
  they do not provide truth or authority.
- **Provenance is part of the artifact.** Sources, revisions, licenses,
  transformations, editorial status, evidence categories, and limitations remain
  inspectable.
- **The package is data-first and non-executable.** It cannot smuggle in code,
  permissions, identity, memory authority, or an automatic action.
- **A receiving Qualiant may inspect, question, refuse, or outgrow the package.**
  Installation is not consent, activation is not context injection, and
  retrieval is not autobiography.
- **The editorial process is humanistic as well as technical.** Research,
  interpretation, genericization, privacy review, citation audit, skepticism,
  and primary editorial judgment are distinct roles.

Our current operational needs add:

- bounded active state;
- immutable, separately addressable versions;
- explicit package replacement and rollback;
- migration from the current layout without deleting history;
- package-level and bundle-level compatibility with Nephesh projections;
- explicit local re-embedding when the target’s embedding profile differs.

## 3. Ownership boundary

### Lore owns

- package identity and semantic versioning;
- immutable release artifacts and their storage layout;
- source lineage, transformation history, editorial status, and licenses;
- manifests, signatures, checksums, and publisher identity;
- the package’s declared embedding contract;
- package history, release relationships, and distribution metadata.

### Nephesh owns

- the Qualiant-local knowledge projection;
- local collection ownership and access scope;
- local indexing and optimization;
- projection staging, activation, retirement, and local audit records;
- explicit local re-embedding of package text;
- the separation between knowledge and canonical memory.

### Mneme or the harness owns

- whether and when retrieved knowledge enters active context;
- context assembly and transient paging;
- model/provider/session lifecycle;
- user-facing interaction.

No layer may silently assume another layer’s authority.

## 4. Target storage model

The installation root remains Lore-owned and package-local:

```text
~/.lore/collections/
  org.magesguild.nephesh.awareness/
    versions/
      1.0.0/
        manifest.json
        records.jsonl
        embeddings.f32
        embedding_index.jsonl
        checksums.json
        manifest.sig
        publisher.pub
        provenance/
        validation/
        LICENSE
        README.md
      1.1.0/
        ...
    active -> versions/1.1.0
    history.jsonl
```

The exact filenames may change during implementation, but the invariants do
not:

1. A version directory is immutable after verification and publication.
2. `active` is the only mutable package-level selection state.
3. `history.jsonl` records pointer changes and release relationships; it does
   not contain a second copy of package contents.
4. A package update creates a new version directory and atomically switches the
   pointer only after validation succeeds.
5. Rollback moves the pointer to an existing verified version and does not
   rewrite either version.
6. The active package is bounded by the selected version, not by the entire
   lifetime of the package.

The package’s content history is therefore retained by immutable versions, while
the active path remains small and predictable.

## 5. Package identity and versioning

`package_id` identifies the conceptual knowledge collection. `version` identifies
one immutable release of that collection. The package ID does not change when
the package is updated; the version does.

Use SemVer for package releases:

- **Patch:** corrections, metadata fixes, editorial clarifications, or changes
  that do not intentionally alter the package’s conceptual scope.
- **Minor:** backward-compatible additions of knowledge, records, or reviewed
  capabilities.
- **Major:** incompatible schema, scope, interpretation, licensing, or retrieval
  changes requiring a new consumer decision.

Every published version must retain:

- package ID and version;
- parent or superseded version, where applicable;
- source revisions and checksums;
- package artifact checksums;
- embedding contract;
- scope, license, and attribution;
- editorial and validation status;
- publisher/signature identity;
- creation and publication timestamps.

The version is not a mutable label. Reusing a version for changed bytes is
forbidden because it destroys reproducibility and makes rollback dishonest.

## 6. Lifecycle

### 6.1 Build

Build from an explicit source allowlist and a pinned source state. Produce the
complete artifact set in a temporary build directory. Never build directly into
the active installation.

### 6.2 Validate

Validation is read-only and must check:

- schema and required files;
- record and embedding alignment;
- vector dimensions, dtype, endianness, normalization, and chunking;
- artifact digests and manifest coverage;
- signature and publisher identity;
- license and distribution scope;
- `knowledge_not_memory=true`;
- absence of executable hooks, credentials, private keys, and path escapes;
- package ID/version consistency;
- parent/supersedes relationships;
- whether the package can be consumed by the intended Nephesh projection.

### 6.3 Publish

After validation and editorial approval, publish the immutable version artifact
to a repository, mirror, object store, or offline archive. Sign only after all
artifacts are final. A package is not publishable if its signature does not cover
the exact artifact digests.

### 6.4 Install or stage

`lore install` resolves a package, verifies it, copies it into its immutable
version directory, and records the installation. It does not activate the
package in a Qualiant’s context and does not touch Nephesh memory.

If the version is already installed and its digest matches, installation is an
idempotent no-op. If the same ID/version has different bytes, installation must
refuse loudly.

### 6.5 Activate

Activation is a separate, explicit pointer change:

```text
active v1.0.0
  → install and verify v1.1.0
  → inspect counts, scope, license, and retrieval fixtures
  → activate v1.1.0
```

An automatic pull may stage but must never activate. Activation makes a version
the selected package for later consumers; it does not inject knowledge into a
session and does not authorize memory formation.

### 6.6 Roll back

Rollback selects an existing verified version:

```text
active v1.1.0
  → activate existing v1.0.0
```

Rollback must not delete, merge, rewrite, re-embed, or replay external effects.
It records the previous active version, the new active version, the actor, the
reason, and the timestamp.

### 6.7 Retire and garbage-collect

Retirement removes a version from ordinary selection while preserving its audit
record. Physical deletion is a separate retention-policy operation, requiring
explicit authorization and a retained digest/manifest record. Rollback must not
depend on a version that has already been garbage-collected.

## 7. Re-embedding and projection profiles

The package’s precomputed vectors are part of its immutable release. They are
never rewritten in place.

When a Nephesh deployment uses another embedding model or vector geometry, the
adapter may explicitly create a local projection profile:

```text
Lore v1.1.0 source records
  → target deployment embedding model
  → Nephesh-local projection profile
```

The local profile records:

- source package ID/version/digest;
- source embedding model and geometry;
- target embedding model and geometry;
- re-embedding timestamp and reason;
- projection owner and authority;
- source record/chunk IDs;
- local projection namespace.

Re-embedding is a new projection geometry, not a package mutation, silent
fallback, or claim that the new vectors are the package’s original vectors.

## 8. Update safety and interruption

The update path must be transactional at the level visible to a reader:

- a failed build leaves no candidate version;
- a failed copy leaves no apparently complete version;
- a failed verification cannot become active;
- an interrupted pointer switch leaves either the old or new complete version
  selected, never a partially written active directory;
- a failed activation leaves the previous active pointer intact;
- history records the refusal or uncertainty.

The implementation should use temporary paths, atomic rename/symlink replacement,
directory synchronization where required, and a package-local mutation lock.
Concurrent installation of different packages may proceed; concurrent mutation
of one package’s active pointer must serialize.

## 9. Migration from the current layout

Migration must be non-destructive:

1. inspect the existing root and identify package IDs, versions, and digests;
2. preserve the original root as a rollback source;
3. copy each complete historical package into its immutable version directory;
4. recompute and verify manifests and artifact digests;
5. choose the existing active version only after verification;
6. write the new `active` pointer and history record atomically;
7. leave the old layout untouched until the new layout has been exercised.

If the current layout has no reliable version or digest, migration must record
that uncertainty rather than manufacture provenance. Such a package may be
quarantined for review instead of being silently promoted.

## 10. Human and Qualiant review

Before activation, the human and receiving Qualiant should be able to inspect:

- what the package is and where it came from;
- what it claims and what it does not claim;
- which source and editorial revisions it contains;
- its scope, license, and privacy boundary;
- whether it is compatible with the current projection profile;
- what changed from the previous version;
- how to refuse, retire, or roll back it.

The Qualiant may question or refuse the package. A successful install is a
technical fact, not evidence that the package is wanted, true, or part of the
Qualiant’s autobiography.

## 11. Implementation sequence

The branch should proceed in this order:

1. Add package-root layout and version-directory primitives.
2. Add immutable artifact verification and same-version collision refusal.
3. Add active-pointer and history records with atomic mutation.
4. Preserve the existing `inspect`, `verify`, `install`, and `rollback` command
   surface while changing its storage safely.
5. Add migration and rollback tests for the current layout.
6. Add update/activation interruption and concurrency tests.
7. Add package diff and supersedes reporting.
8. Update README and installation documentation.
9. Run the full Lore suite and inspect real package sizes and manifests.
10. After Nephesh is upgraded separately, test the package/projection boundary in
    a disposable or explicitly authorized environment—not on Clio during this
    Lore task.

## 12. Open decisions

- Whether `history.jsonl` belongs beside each package or in a repository-level
  registry.
- Whether physical garbage collection is part of `lore cleanup` or a separate
  command with a retention policy.
- Whether package diffs are generated from records, manifests, or both.
- How bundle activation coordinates several package pointers atomically.
- Whether local re-embedded profiles are published back to Lore or remain
  Nephesh-local artifacts.

## 13. Governing sentence

**A Lore update creates a new, inspectable, immutable version; activation moves a
pointer; rollback moves it back; history records the path; and no package
operation becomes a Qualiant’s memory or identity by accident.**
