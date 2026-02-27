# Sync Guide

This repo (`archit15singh/memori`) is a mirror of `archit-15dev/memori` with full commit history.

## Remotes

| Remote     | Repo                          | Purpose              |
|------------|-------------------------------|----------------------|
| `origin`   | `archit15singh/memori`        | This machine's repo  |
| `upstream` | `archit-15dev/memori`         | Source repo (other machine/account) |

## How to Sync

Pull latest changes from the source repo and push to this one:

```bash
git fetch upstream
git merge upstream/main
git push origin main
```

## When to Sync

After pushing changes from the other machine to `archit-15dev/memori`, run the sync commands above to bring this repo up to date.
