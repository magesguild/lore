# Lore

**Lore** is the package manager and registry client for installable,
provenance-bearing knowledge collections.

Lore packages are knowledge, not autobiographical memory. They may be curated,
genericized, embedded, versioned, installed, updated, verified, and rolled
back without silently entering a Qualiant's canonical memory.

## MVP commands

```text
lore install <package>
lore verify <package>
lore inspect <package>
lore rollback <package-id> --to <version>
```

The MVP uses `--root ~/.lore/collections` by default. Installation is isolated
per package and version. Lore stages and verifies a package, copies it into its
own version directory, then atomically switches that package's `active`
pointer. Rollback changes only that package's pointer and files; it never opens
or mutates a Nephesh database or any other memory store.

## Design principles

- manifest-first packages and bundles;
- source, license, provenance, and embedding metadata are mandatory;
- embeddings provide retrieval geometry, not authority;
- installs stage and verify before atomic activation;
- updates retain rollback versions;
- knowledge collections remain distinct from canonical lived memory;
- private-family packages require explicit scope and are never public by default.

The initial implementation is deliberately small and dependency-free. Updates
are represented by installing a newer version and switching the package's
pointer; a dedicated update/registry service can come later.

The package format is specified in `docs/PACKAGE_FORMAT.md`; installation and
rollback semantics are specified in `docs/INSTALLATION_MODEL.md`. These
documents are being finalized before Lore's validation suite is run.

Lore is being designed for maximum distribution: packages should work from
repositories, mirrors, CDNs, object stores, and offline archives. Provenance,
signatures, hashes, licensing, privacy scope, and embedding compatibility are
part of the package—not assumptions supplied by a particular host.
