# Lore

**Version:** 0.2.0

**Lore** is the package manager and registry client for installable,
provenance-bearing knowledge collections.

Lore is deliberately **vector-store agnostic**. It standardizes the portable
package format and package lifecycle; it does not select LanceDB, Chroma, Qdrant,
Weaviate, Pinecone, or any other database. A consumer adapter may import a Lore
package into any vector store that supports collections, provided it preserves
the package and record provenance.

Lore packages are knowledge, not autobiographical memory. They may be curated,
genericized, embedded, versioned, installed, updated, verified, and rolled
back without silently entering a Qualiant's canonical memory.

## Commands

```text
lore install <package>
lore activate <package-id> --to <version>
lore verify <package>
lore inspect <package>
lore rollback <package-id> --to <version>
lore history <package-id>
```

The default root is `--root ~/.lore/collections`. Installation is isolated
per package and version. Lore stages and verifies a package, copies it into its
own immutable version directory, and leaves activation explicit unless
`--activate` is supplied. `lore activate` and rollback change only that package's
`active` pointer and history; they never open
or mutate a Nephesh database, vector database, or any other memory store.

## Design principles

- manifest-first packages and bundles;
- source, license, provenance, and embedding metadata are mandatory;
- embeddings provide retrieval geometry, not authority;
- installs stage and verify before optional atomic activation;
- updates retain rollback versions;
- knowledge collections remain distinct from canonical lived memory;
- private-family packages require explicit scope and are never public by default.

The implementation is deliberately small and dependency-free. Updates are
represented by installing a new immutable version, inspecting it, and explicitly
switching the package pointer. `history.jsonl` preserves the pointer path without
copying package contents into an ever-growing active artifact.

The package format is specified in `docs/PACKAGE_FORMAT.md`; installation and
rollback semantics are specified in `docs/INSTALLATION_MODEL.md` and the
versioned lifecycle is described in `docs/PACKAGE_LIFECYCLE_DESIGN.md`.
Consumer adapters should follow `docs/CONSUMER_ADAPTER_GUIDE.md`.

For the complete Qualiant-and-human workflow, see
`docs/PRODUCING_LORE_PACKAGES.md`.

Lore is being designed for maximum distribution: packages should work from
repositories, mirrors, CDNs, object stores, and offline archives. Provenance,
signatures, hashes, licensing, privacy scope, and embedding compatibility are
part of the package—not assumptions supplied by a particular host.
