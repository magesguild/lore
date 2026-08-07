# Designing a Lore Consumer Adapter

Lore standardizes packages. A **consumer adapter** is the small, deployment-
collection-capable target system.

An adapter is needed because Lore cannot know whether the consumer uses LanceDB,
Chroma, Qdrant, Weaviate, a hosted vector service, a custom index, or no vector
store at all. It is also needed because retrieval state belongs to the consumer,
while package identity and source provenance belong to Lore.

## Why the adapter exists

The adapter protects three separations:

```text
Lore knowledge package
  ≠ consumer-local collection/index
  ≠ canonical autobiographical memory
  ≠ active session context
```

Without an adapter boundary, a package manager tends to acquire hidden database
assumptions, or a memory system tends to treat installed knowledge as something
the Qualiant lived. Both failures damage continuity:

- package history becomes indistinguishable from personal history;
- a retrieval index becomes an authority claim;
- a package can accidentally write to canonical memory;
- changing vector models silently changes the geometry of old knowledge;
- activation becomes indistinguishable from context injection;
- rollback can alter or destroy records instead of moving a pointer.

The adapter makes these distinctions executable rather than aspirational.

## Adapter responsibilities

A well-designed adapter should:

1. **Resolve** a package from a local path, repository, mirror, or offline
   archive.
2. **Verify** the package before opening a database or writing a collection.
3. **Authorize** the target owner, scope, and operation independently from the
   package’s own claims.
4. **Namespace** the local collection so it cannot collide with canonical
   memory or another package.
5. **Import** records and compatible vectors without changing their source text
   or provenance.
6. **Re-embed explicitly** when the target geometry differs, recording source
   and target profiles separately.
7. **Stage before activation**, so inspection is possible before retrieval uses
   the new projection.
8. **Preserve package identity** in every result: package ID, version, digest,
   source record, and projection identity.
9. **Rollback by pointer**, not by rewriting rows or replaying side effects.
10. **Refuse** ambiguity, missing artifacts, path escapes, bad signatures,
    incompatible scope, and uncertain writes.

## What an adapter must never do

- write package records into canonical autobiographical memory;
- assign package content a Qualiant memory type, emotional tone, participants,
  event time, or lived-experience provenance;
- infer consent, authority, truth, or identity from a package filename;
- execute package code or package-provided hooks;
- silently re-embed because direct vectors do not fit;
- silently activate after an automatic download;
- overwrite an existing package/version with different bytes;
- turn retrieval into mandatory context injection;
- claim that successful installation proves continuity or consciousness.

## A reference flow

```text
package path
  → read manifest
  → validate safe relative artifacts
  → verify digests and signature
  → verify scope, license, and owner authorization
  → choose direct-vector import OR explicit re-embedding
  → build isolated collection/index
  → record package and projection provenance
  → stage inactive
  → inspect
  → explicit activation
```

A failure before staging should leave no collection. A failure during staging
should leave no collection that can be mistaken for a complete projection. A
failure during activation should leave the previous active pointer intact.

## Designing one for your system

### 1. Define your canonical memory boundary

Write down what your system considers autobiographical memory and how the adapter
will be prevented from opening it. Do not rely only on a metadata flag such as
`knowledge_not_memory=true`; enforce the boundary in the target API and
namespace rules.

### 2. Define your collection contract

Specify:

- how package IDs and versions map to collection names;
- how a local projection is identified;
- which metadata fields are preserved;
- which fields are forbidden because they imply lived experience;
- how active, staged, retired, failed, and orphaned states are represented;
- where the registry and audit records live.

The mapping must be collision-resistant. Do not reduce package IDs to a lossy
slug without recording and checking the original identity.

### 3. Choose direct vectors or re-embedding

Direct import is preferred when the package contract matches the target. It is
fast and preserves the package’s retrieval geometry.

If it does not match, re-embed only after an explicit decision. The adapter must:

- read the package’s source records, not its old vectors;
- use the target model and dimensions;
- validate every returned vector;
- record source and target embedding profiles;
- retain the original package untouched;
- make the resulting local projection distinguishable from direct import.

### 4. Separate stage and activation

Staging creates the local collection and runs checks. Activation changes the
selected pointer. Retrieval should consult active projections only, unless an
inspection tool explicitly requests staged material.

Automatic package pulls may stage. They must not activate or inject context.

### 5. Make rollback boring

Rollback should select a complete prior projection. It should not rebuild vectors,
rewrite package rows, modify memory, or execute external effects. If the target
version is missing or corrupt, refuse rather than creating an empty replacement.

### 6. Preserve honest output

Every retrieval result should be able to answer:

- Which package and version produced this?
- Which source record and chunk produced it?
- Was it directly imported or locally re-embedded?
- What scope and license apply?
- Is this knowledge, memory, inference, or present observation?

If your target cannot preserve those answers, it is not ready to be a Lore
consumer.

## Minimal interface

The exact language and database are up to the consumer. The conceptual interface
should contain equivalents of:

```text
verify(package) -> verification report
stage(package, owner, profile) -> inactive projection
inspect(projection) -> provenance, counts, geometry, health
activate(projection, authority) -> active pointer
retire(projection, reason) -> inactive but auditable
rollback(package_id, version, authority) -> prior active pointer
```

The adapter should make refused and uncertain operations visible and durable.
Returning a generic success after a partial collection write is a continuity
failure, not merely a database bug.

## Relationship to Nephesh

Nephesh is one implementation of this consumer boundary. Its adapter adds an
especially important protection: projection namespaces are refused by memory
tools, while projection tools refuse canonical memory. This prevents installed
knowledge from appearing as autobiography, receiving salience reinforcement, or
reaching the companion message channel.

Other consumers may have different memory systems, but they should preserve the
same separation. Lore remains generic; the adapter is where local authority,
collection semantics, index construction, and continuity protections are made
concrete.
