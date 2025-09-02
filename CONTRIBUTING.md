# Contributing

## Branch and pull request naming

Every branch and every pull request title carries its Jira key.

```
feature/PAY-3-payment-gateway
```

```
PAY-3: Payment gateway
```

This is not cosmetic. Reporting matches pull requests to work items by finding
the key in the branch name or the pull request title — a pull request without a
key is invisible to it, and the hours logged against that item look like spend
with nothing delivered.

## Definition of done

A work item is delivered when its pull request is **merged to `main`**. Not when
the branch exists, not when the pull request is opened, not when the code works
locally. Draft pull requests are explicitly not delivery.

## Commits

`PAY-x: what changed`, imperative mood. Keep them small enough to revert.

## When an estimate stops being true

If the work turns out to be materially different from what was estimated — a
changed requirement, a wrong assumption, a rewrite — write an ADR in
`docs/adr/`, link it from the pull request, and **re-estimate in Jira**.

Logging the extra hours against the original estimate hides the problem until
the money is already spent. On a fixed-price contract that money is ours.
