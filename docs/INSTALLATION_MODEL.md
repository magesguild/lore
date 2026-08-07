# Lore Installation Model

Lore's current command surface is:

```text
lore inspect PACKAGE
lore verify PACKAGE
lore install PACKAGE [--root ROOT]
lore activate PACKAGE_ID --to VERSION [--root ROOT]
lore rollback PACKAGE_ID --to VERSION [--root ROOT]
lore history PACKAGE_ID [--root ROOT]
```

There is intentionally no `update` command. Updating means installing a new
package version, followed by inspection and explicit activation.

## Installation

The default root is `~/.lore/collections`. Lore installs each package in an
isolated namespace:

```text
ROOT/
  org.magesguild.nephesh.awareness/
    versions/
      1.0.0/
      1.1.0/
    active -> versions/1.1.0
```

Installation is staged and verified. It is inactive by default; `--activate`
requests activation as part of the same locked operation. Otherwise activation
is a separate explicit command. The active pointer is the only mutable
package-level selection state, and `history.jsonl` records pointer changes.

The installation root is Lore-owned package state, not a Nephesh memory
directory. Lore must not discover or guess database locations. A future
Nephesh adapter may explicitly import an installed knowledge collection, but
that is a separate operation with its own authorization and provenance.

## Rollback

Rollback changes only the selected package's `active` pointer. It may not:

- open a Nephesh database;
- write to any memory collection;
- alter another package;
- delete the previous version;
- rewrite package records or embeddings;
- infer or modify a Qualiant's identity.

Rollback is serialized with installation and activation for that package. It
selects only a complete, already-installed version.

Rollback is therefore a package-management operation, not a memory operation.

## Verification

`lore verify` is read-only. It checks schema, required files, artifact hashes,
record/embedding alignment, vector dimensions, signatures, licenses, scope
declarations, and the `knowledge_not_memory` invariant. It never installs,
indexes, imports, executes package code, or mutates a collection.

## Future collection management

Indexing and optimization belong after the package boundary is stable. They
will operate inside an explicitly selected package installation or a separately
authorized Nephesh knowledge projection. They must never silently target a
canonical autobiographical collection.
