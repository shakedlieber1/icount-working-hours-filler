# Semantic Release Design

Date: 2026-07-26
Status: Approved for implementation planning

## Goal

Add automated semantic version releases that are visible in GitHub for this
repository.

The release system should create versioned Git tags and GitHub Releases such as
`v1.2.3`. It should not publish a package to PyPI or npm.

## Current Context

The repository is a small Python 3.12 automation project. It has:

- Python scripts at the repository root.
- Dependencies in `requirements.txt`.
- Unit tests under `tests/`.
- An existing GitHub Actions CI workflow at `.github/workflows/ci.yml`.
- No package metadata such as `pyproject.toml`, `setup.py`, or `package.json`.
- No existing release tags or changelog convention.

Because the project is not currently packaged for distribution, release
automation should focus on GitHub Releases rather than package publishing.

## Chosen Approach

Use semantic-release to create GitHub releases and version tags only.

The implementation should add:

- A semantic-release configuration file.
- A GitHub Actions release workflow.
- Minimal npm development metadata if needed to install/pin semantic-release
  tooling.

The release workflow should run only for pushes to release branches, expected to
be `main` and `master`.

## Release Behavior

semantic-release will inspect commit messages since the previous release tag and
decide the next version:

- `fix:` commits create a patch release.
- `feat:` commits create a minor release.
- Breaking changes create a major release.
- Commits that do not affect release notes or versioning do not create a
  release.

When a release is needed, semantic-release should:

- Create a Git tag using the default `vX.Y.Z` format.
- Publish a GitHub Release for that tag.
- Generate release notes in the GitHub Release.

The release version will be visible through GitHub's Releases page and tag list.

## Non-Goals

The first release automation pass will not:

- Publish to PyPI.
- Publish to npm.
- Add Python packaging metadata.
- Commit a generated `CHANGELOG.md`.
- Commit version bumps back to the repository.

Avoiding committed changelog and version files keeps the pipeline simple and
reduces branch permission complexity. GitHub Releases provide the version
history and release notes.

## GitHub Actions Design

The release workflow should:

- Trigger on pushes to `main` and `master`.
- Check out the full git history and tags so semantic-release can find prior
  releases.
- Set up Python 3.12.
- Install Python dependencies from `requirements.txt`.
- Run the same verification used by CI:
  - `python -m unittest`
  - `python -m compileall -q .`
- Set up Node.js.
- Install semantic-release and its required plugins.
- Run `semantic-release`.

The workflow should request only the permissions needed to create GitHub tags
and releases:

- `contents: write`
- `issues: write`
- `pull-requests: write`

The GitHub plugin may comment on released issues and pull requests. If the
implementation explicitly disables that behavior, the issue and pull request
permissions can be removed.

No external publishing token should be required. The built-in `GITHUB_TOKEN`
should be sufficient for GitHub releases.

## Components

### semantic-release configuration

Defines release branches and plugins.

Expected branches:

- `main`
- `master`

Expected plugins:

- `@semantic-release/commit-analyzer`
- `@semantic-release/release-notes-generator`
- `@semantic-release/github`

The npm publishing plugin should not be enabled.

### release workflow

Owns the CI-gated release execution.

It should be independent from the existing CI workflow so the CI workflow can
continue serving pull requests while release automation runs only after changes
land on a release branch.

### package metadata for tooling

If implementation uses a local `package.json`, it should exist only to pin and
run release tooling. It should mark the project private so npm publishing is not
accidentally enabled.

## Error Handling

If tests or compile checks fail, the release job must stop before invoking
semantic-release.

If semantic-release cannot determine a release branch or cannot create the
GitHub release, the workflow should fail visibly in GitHub Actions. The fix
should be made in repository configuration or branch permissions rather than by
adding package publishing tokens.

If there are no release-worthy commits, semantic-release should complete without
creating a new release.

## Testing

Implementation verification should include:

- Running the Python unit tests locally.
- Running the Python compile check locally.
- Validating that the semantic-release configuration is syntactically valid.
- Optionally running semantic-release in dry-run mode locally if dependencies
  are available and GitHub authentication is not required.

After merge, the first real validation is the GitHub Actions release workflow on
`main` or `master`. If there are no conventional commits that trigger a release,
that outcome is acceptable and should be visible in the workflow logs.

## Success Criteria

The work is complete when:

- The repository has a semantic-release configuration.
- The repository has a GitHub Actions release workflow.
- Release automation does not publish to PyPI or npm.
- Future qualifying commits on `main` or `master` create GitHub version tags and
  GitHub Releases.
- The Python test and compile checks gate the release job.
