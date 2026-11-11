---
id: release-status
type: procedure
tags: [lorevell, maintainer]
---

# Do not announce a successful release after publishing failure

The pre-release workflow at source commit 9dd899a uses always() for its GitHub release job and explicitly creates the release even if registry jobs fail. This is a verified project limitation to fix before release: gate publication announcements on successful required registry jobs. This note records a defect, not recommended current behavior. GitHub Actions stores existing CARGO_REGISTRY_TOKEN and PYPI_API_TOKEN secrets for registry jobs; do not export their values into local logs.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/.github/workflows/release.yml

## Related
- [[packaging]]
