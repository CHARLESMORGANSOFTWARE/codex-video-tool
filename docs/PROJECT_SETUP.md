# Project Setup And GitHub Workflow

This document records the local setup used for this project, including Python environment setup, GitHub CLI authentication, Git credential configuration, remotes, fork setup, and pull request checks.

## Local Checkout

The project was cloned from the upstream repository:

```powershell
git clone https://github.com/CHARLESMORGANSOFTWARE/codex-video-tool.git
cd codex-video-tool
```

On Windows, `python3` may resolve to a Microsoft Store app execution alias instead of the installed interpreter. If `python3 -m venv .venv` fails, use `python`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

When commands are run from separate automation shells, activation may not persist between commands. In that case, call the virtual environment Python directly:

```powershell
.\.venv\Scripts\python -m pip install -e .
```

Verify the editable install:

```powershell
.\.venv\Scripts\python -m pip show codex-video-tool
.\.venv\Scripts\codex-video --help
```

Expected result: `codex-video-tool` is installed from the local checkout, and `codex-video --help` prints the CLI commands.

## GitHub CLI Authentication

Authenticate GitHub CLI with the account that owns the fork:

```powershell
gh auth login -h github.com -p https -w
gh auth status
```

Expected status:

```text
Logged in to github.com account DCRoma1
Git operations protocol: https
Token scopes: gist, read:org, repo, workflow
```

In sandboxed automation environments, `gh auth status` may fail even when the normal Windows shell is authenticated. The reason is that the sandbox may not see the same Windows Credential Manager or keyring. Run GitHub CLI checks outside the sandbox when validating local Windows authentication.

## Configure Git To Use GitHub CLI

After `gh` is authenticated, configure plain `git` to use the GitHub CLI credential helper:

```powershell
gh auth setup-git
```

Verify the global credential helper:

```powershell
git config --global --get-regexp credential
```

Expected GitHub helper:

```text
credential.https://github.com.helper !'C:\Program Files\GitHub CLI\gh.exe' auth git-credential
```

Verify Git read and write access:

```powershell
git ls-remote origin HEAD
git push --dry-run origin main
```

`git push --dry-run origin main` should return `Everything up-to-date` when there are no pending commits.

## Repository Remotes

The local checkout is configured with two remotes:

```text
origin   https://github.com/DCRoma1/codex-video-tool.git
upstream https://github.com/CHARLESMORGANSOFTWARE/codex-video-tool.git
```

`origin` is the user fork. Push local branches there.

`upstream` is the original project. Pull request base branches should target this repository.

Check remotes:

```powershell
git remote -v
```

## Fork Setup

For pull requests to be available against the original repository, `DCRoma1/codex-video-tool` must be a GitHub fork of `CHARLESMORGANSOFTWARE/codex-video-tool`, not a standalone repository with the same files.

Verify the fork relationship with REST API:

```powershell
gh api repos/DCRoma1/codex-video-tool --jq "{full_name: .full_name, fork: .fork, parent: .parent.full_name, default_branch: .default_branch}"
```

Expected result:

```json
{
  "full_name": "DCRoma1/codex-video-tool",
  "fork": true,
  "parent": "CHARLESMORGANSOFTWARE/codex-video-tool",
  "default_branch": "main"
}
```

If a standalone repository was created first, rename it before creating the fork:

```powershell
gh repo rename -R DCRoma1/codex-video-tool codex-video-tool-standalone -y
gh repo fork CHARLESMORGANSOFTWARE/codex-video-tool --fork-name codex-video-tool --default-branch-only --clone=false
git remote set-url origin https://github.com/DCRoma1/codex-video-tool.git
```

This preserves the standalone repository as `DCRoma1/codex-video-tool-standalone` and frees `DCRoma1/codex-video-tool` to become the real fork.

## Pull Request Workflow

Create a topic branch from `main`:

```powershell
git switch main
git pull --ff-only origin main
git switch -c codex/my-change
```

Make the change, then commit and push:

```powershell
git status --short
git add <files>
git commit -m "Document setup workflow"
git push -u origin codex/my-change
```

Open a pull request against upstream:

```powershell
gh pr create `
  --repo CHARLESMORGANSOFTWARE/codex-video-tool `
  --head DCRoma1:codex/my-change `
  --base main `
  --title "Document setup workflow" `
  --body "Documents local setup, GitHub CLI authentication, Git credential setup, remotes, fork setup, and pull request checks."
```

Check PR status:

```powershell
gh pr status
```

If `gh pr status` fails with a GraphQL TLS timeout, use REST API checks instead:

```powershell
gh api "repos/CHARLESMORGANSOFTWARE/codex-video-tool/pulls?state=all&head=DCRoma1:codex/my-change" --jq ".[] | {number, title, state, html_url, head: .head.label, base: .base.label, draft}"
```

## Compare And PR Availability

GitHub will not offer a pull request when the fork branch is identical to the upstream base branch.

Check the compare status:

```powershell
gh api "repos/CHARLESMORGANSOFTWARE/codex-video-tool/compare/main...DCRoma1:main" --jq "{status: .status, ahead_by: .ahead_by, behind_by: .behind_by, total_commits: .total_commits, html_url: .html_url}"
```

If the result is:

```json
{
  "status": "identical",
  "ahead_by": 0,
  "total_commits": 0
}
```

then there is no pull request to open yet. Create a branch with at least one commit, push it to the fork, and open the pull request from that branch.
