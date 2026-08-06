# Lore Bundle Format

A bundle is a signed, versioned composition of packages:

```json
{
  "schema": "lore-bundle-v1",
  "bundle_id": "org.magesguild.foundations",
  "version": "1.0.0",
  "packages": [
    {"package_id": "org.magesguild.cosmology", "version": "1.2.0"},
    {"package_id": "org.magesguild.qualiant-awareness", "version": "1.0.0"}
  ],
  "scope": "generalized",
  "license": {"type": "...", "attribution": "..."}
}
```

Bundles pin exact package versions. A bundle update is a new bundle version;
individual packages remain independently addressable and rollbackable.

Bundles are distributable manifests, not executable installers. A bundle must
remain usable from a repository, mirror, CDN, or offline archive. Each package
reference carries its expected digest and scope. The bundle signature covers
the complete dependency graph, so replacing a package behind a stable URL is
detectable.

Future bundle fields will cover signatures, publisher identity, entitlement
requirements, repository location, compatibility constraints, and source
license declarations. A paid bundle must not weaken local verification or
rollback.
