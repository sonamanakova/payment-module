# simulation/

Scaffolding that builds this repository, kept in the repository so the demo is
reproducible.

Everything in here is fiction: Fictional Bank a.s. is invented, the five people
are invented, the sandbox behaviour is invented. No real project, client or
person is described.

## What is where

| | |
|---|---|
| `build_history.sh` | Builds the git history: six branches, backdated commits, three merged into main. |
| `seed_github.py` | Pushes the branches and creates the pull requests, issues and comment threads on GitHub. |
| `prs/*.md` | Pull request bodies, with a `---` header carrying branch, state, dates and labels. |
| `comments.json` | The discussion threads. This is where the cause of the PAY-3 overrun is actually explained. |
| `issues.json` | Issues mirroring the Jira work items, plus the commercial change request. |
| `history/*.py` | Earlier versions of files that were later rewritten — the synchronous gateway, the v2.0 webhook parser, the PAY-1 config. They exist so the rewrite shows up as a real diff. |

## Rebuilding from scratch

```bash
bash simulation/build_history.sh
```

The final content of every file is snapshotted into
`../margin-guardian-demo.sources` on the first run and read from there
afterwards. The script writes into the repository and replaces `.git`; it never
deletes the working tree. Pass `--resnapshot` after editing files to refresh the
sources.

```bash
python simulation/seed_github.py --repo owner/name --dry-run
```

Then drop `--dry-run` to actually create everything. Needs `GITHUB_TOKEN` with
`repo` scope, and a repository that already exists and is empty.

## What the AI layer is meant to find here

The detector sees the arithmetic: PAY-3 at 95h against a 40h estimate, −19%
margin, nothing merged, spend running 12 → 25 → 30 → 28 across four weeks. It
cannot see *why*. The why is in this repository, in four places:

1. **`docs/scope.md`** — the five assumptions the 40h estimate was built on,
   written down before the work started.
2. **`docs/adr/0002` superseded by `docs/adr/0003`** — the moment those
   assumptions died, dated, with the consequences spelled out including the
   sentence that matters: *not re-estimated in Jira*.
3. **`docs/bank-api-notes.md` and the commit history** — the sandbox requiring
   SCA on 2025-09-26, the bank confirming it is permanent on 2025-09-29, two
   forced rewrites, and the fixture amount that kept CI green while nothing
   worked.
4. **The comment thread on the PAY-3 pull request** — a developer, a reviewer and a PM working
   out in the open that this is a changed requirement rather than a delivery
   failure, and that under a fixed-price contract nobody has had the commercial
   conversation yet.

The control group matters as much: PAY-2 is the same developer at the same
seniority on a *larger* estimate, and it merged 8h over. Whatever went wrong on
PAY-3, it is not the person doing the work.
