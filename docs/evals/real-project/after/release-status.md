---
id: release-status
type: procedure
tags: [lorevell, maintainer]
---

# Release announcement gating: historical defect and reported fix

At source commit 9dd899a, the pre-release workflow used `always()` for its GitHub release job and explicitly created the release even if registry jobs failed. This records the historical defect: publication announcements should depend on successful required registry jobs.

[[437fbf7d-859a-4e15-8def-6f4a1f14f6a4]] reports removing `always()` while retaining the tag-only condition and dependencies on both registry jobs. That note records passing static workflow assertions, but gives no exact fix revision and reports no GitHub Actions execution or real registry upload. The original “to fix before release” status is therefore superseded by a reported, statically checked fix; deployed behavior remains unverified by these notes.

The historical note records existing GitHub Actions secrets named `CARGO_REGISTRY_TOKEN` and `PYPI_API_TOKEN` for registry jobs; do not export their values into local logs.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/.github/workflows/release.yml

## Related
- [[packaging]]
