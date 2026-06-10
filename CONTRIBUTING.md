# Contributing to trackflow

This project uses a branch workflow so package changes can be checked before
they become released code.

## Branches

- `main` is the released version of the package. Do not commit directly to
  `main`.
- `develop` is the working branch for reviewed changes that are not released
  yet.
- Feature branches are for one focused change at a time. Use names such as
  `codex/add-package-command` or `fix/gaze-monitor-state`.

## Usual development flow

1. Start from the latest `develop` branch.
2. Create a feature branch for the change.
3. Make the smallest clear change that solves the problem.
4. Run the local checks.
5. Open a pull request into `develop`.
6. Merge into `develop` only after the checks pass.

Use these commands for local checks:

```bash
uv run pytest
uv run ruff check src tests
uv run mkdocs build --strict
```

## Release flow

Releases happen from `main`. A release should collect tested changes from
`develop`.

1. Make sure `develop` has the changes that should be released.
2. Create a release branch from `develop`.
3. Update `project.version` in `pyproject.toml`.
4. Add matching release notes to `CHANGELOG.md`.
5. Run local checks and build the package:

```bash
uv run pytest
uv run ruff check src tests
uv run mkdocs build --strict
uv build
```

6. Open a pull request from the release branch into `main`.
7. Merge the pull request only after the checks pass.

When the release pull request is merged into `main`, GitHub Actions builds the
package, creates a tag named `v{version}`, publishes a GitHub Release, and
updates the documentation site.

Use a squash merge commit title that contains `[release]` for release pull
requests. This prevents ordinary repository setup pushes from publishing a
package version before the release branch is ready.

If a release with the same tag already exists, the release workflow fails. This
usually means `project.version` was not updated before merging into `main`.

## GitHub branch protection

Protect both `main` and `develop` in GitHub repository settings.

Recommended rules:

- Require a pull request before merging.
- Require CI checks to pass.
- Block direct pushes to `main`.
- Use one merge style consistently, such as squash merge.
