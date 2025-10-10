"""Push the branches and open the pull requests, issues and discussion on GitHub.

build_history.sh makes the git history. This makes the part that only exists on
GitHub: pull requests with real bodies, the draft state on PAY-3, labels, issues
mirroring the Jira work items, and the comment thread where the cause of the
PAY-3 overrun is actually discussed.

That thread is the point. A margin detector can see 95h against a 40h estimate
with nothing merged; it cannot see that the bank withdrew an SCA exemption seven
days after the estimate was signed off. That lives here.

Usage:

    python simulation/seed_github.py --repo owner/name --dry-run
    python simulation/seed_github.py --repo owner/name --reset-remote

Needs GITHUB_TOKEN with `repo` scope (or a fine-grained token with read/write on
contents, pull requests and issues). The repository must already exist.

--reset-remote closes every open pull request and deletes every branch except
the default one before pushing. Use it when the repository already has scaffold
content in it. It cannot delete pull requests -- GitHub has no such API -- so
already-closed ones stay in the list and keep their numbers.

Everything this creates is fictional: a made-up client, a made-up bank, made-up
colleagues. Nothing here describes a real project or a real person.
"""

import argparse
import json
import os
import subprocess
import sys
import time

API = "https://api.github.com"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DEFAULT_BRANCH = "main"
BRANCHES = [
    DEFAULT_BRANCH,
    "feature/PAY-1-module-skeleton",
    "feature/PAY-2-bank-api",
    "feature/PAY-3-payment-gateway",
    "feature/PAY-4-order-backend",
    "feature/PAY-5-checkout-frontend",
    "feature/PAY-6-test-suite",
]

# Pull requests in the order they were opened. A work item whose state is
# "merged" has its branch already in main, so there is nothing left to diff and
# GitHub will not open a pull request for it -- those get filed as closed issues
# instead, so the reasoning is still on the repository under the same key.
PULL_REQUESTS = ["PAY-1", "PAY-2", "PAY-4", "PAY-3", "PAY-5", "PAY-6"]


class GitHub:
    def __init__(self, repo, token, dry_run=False):
        import requests

        self.repo = repo
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get(self, path, params=None):
        response = self.session.get(f"{API}{path}", params=params, timeout=30)
        if response.status_code >= 400:
            sys.exit(f"GET {path} failed: {response.status_code} {response.text}")
        return response.json()

    def post(self, path, payload):
        if self.dry_run:
            print(f"POST {path}")
            print(json.dumps(payload, indent=2, ensure_ascii=False)[:600])
            print()
            return {"number": 0, "html_url": "(dry run)"}

        response = self.session.post(f"{API}{path}", json=payload, timeout=30)
        if response.status_code >= 400:
            sys.exit(f"POST {path} failed: {response.status_code} {response.text}")
        time.sleep(1)  # stay well clear of the secondary rate limit
        return response.json()

    def patch(self, path, payload):
        if self.dry_run:
            print(f"PATCH {path} {payload}")
            return {}
        response = self.session.patch(f"{API}{path}", json=payload, timeout=30)
        if response.status_code >= 400:
            sys.exit(f"PATCH {path} failed: {response.status_code} {response.text}")
        time.sleep(1)
        return response.json()

    def delete(self, path):
        if self.dry_run:
            print(f"DELETE {path}")
            return
        response = self.session.delete(f"{API}{path}", timeout=30)
        if response.status_code >= 400 and response.status_code != 404:
            sys.exit(f"DELETE {path} failed: {response.status_code} {response.text}")
        time.sleep(1)


def read_front_matter(path):
    """Split a `---` header off the top of a markdown file.

    Deliberately not a YAML parser -- the headers here are flat key: value pairs
    plus one list, and a dependency for that would be silly.
    """
    with open(path, encoding="utf-8") as handle:
        text = handle.read()

    if not text.startswith("---"):
        return {}, text

    _, header, body = text.split("---", 2)
    meta = {}
    for line in header.strip().splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            value = [item.strip() for item in inner.split(",")] if inner else []
        elif value in ("true", "false"):
            value = value == "true"
        else:
            value = value.strip('"')
        meta[key.strip()] = value
    return meta, body.strip()


def reset_remote(api, repo):
    """Close open pull requests and delete every branch but the default one."""
    print("== clearing what is already there ==")

    open_prs = api.get(f"/repos/{repo}/pulls", {"state": "open", "per_page": 100})
    for pull in open_prs:
        api.patch(f"/repos/{repo}/pulls/{pull['number']}", {"state": "closed"})
        print(f"  closed PR #{pull['number']}  {pull['title']}")
    if not open_prs:
        print("  no open pull requests")

    branches = api.get(f"/repos/{repo}/branches", {"per_page": 100})
    removed = 0
    for branch in branches:
        if branch["name"] == DEFAULT_BRANCH:
            continue
        api.delete(f"/repos/{repo}/git/refs/heads/{branch['name']}")
        print(f"  deleted branch {branch['name']}")
        removed += 1
    if not removed:
        print("  no branches to delete")
    print()


# Feeds the token to git without ever putting it on a command line. The helper
# script below is what appears in argv and in any error message; it names the
# environment variable, it does not contain its value. Do not go back to
# embedding the token in the remote URL -- git echoes the full URL on failure,
# and a token printed once is a token that has to be revoked.
CREDENTIAL_HELPER = (
    '!f() { echo "username=x-access-token"; echo "password=$GITHUB_TOKEN"; }; f'
)


def push_branches(repo, token, dry_run):
    remote = f"https://github.com/{repo}.git"

    if dry_run:
        print(f"git push --force {remote} " + " ".join(BRANCHES))
        return

    print(f"Pushing {len(BRANCHES)} branches to {remote} ...")
    result = subprocess.run(
        [
            "git",
            "-c",
            f"credential.helper={CREDENTIAL_HELPER}",
            "push",
            "--force",
            remote,
            *BRANCHES,
        ],
        cwd=ROOT,
        env={**os.environ, "GITHUB_TOKEN": token, "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode != 0:
        sys.exit(
            "\ngit push failed (see above).\n"
            "If it mentions the 'workflow' scope, the token cannot write\n"
            ".github/workflows/ci.yml -- reissue it with that scope."
        )
    print()


def seed(repo, api):
    print("== issues ==")
    with open(os.path.join(HERE, "issues.json"), encoding="utf-8") as handle:
        issues = json.load(handle)["issues"]
    for issue in issues:
        created = api.post(
            f"/repos/{repo}/issues",
            {"title": issue["title"], "body": issue["body"], "labels": issue["labels"]},
        )
        print(f"  {issue['key']:>8}  {created.get('html_url')}")

    print("\n== pull requests ==")
    with open(os.path.join(HERE, "comments.json"), encoding="utf-8") as handle:
        comments = json.load(handle)

    numbers = {}
    for key in PULL_REQUESTS:
        meta, body = read_front_matter(os.path.join(HERE, "prs", f"{key}.md"))

        if meta["state"] == "merged":
            created = api.post(
                f"/repos/{repo}/issues",
                {
                    "title": f"{meta['title']} (merged {meta['merged']})",
                    "body": body,
                    "labels": ["work-item", "done"],
                },
            )
            api.patch(f"/repos/{repo}/issues/{created['number']}", {"state": "closed"})
            print(f"  {key:>8}  merged -> issue  {created.get('html_url')}")
            numbers[key] = created["number"]
            continue

        created = api.post(
            f"/repos/{repo}/pulls",
            {
                "title": meta["title"],
                "head": meta["branch"],
                "base": meta["base"],
                "body": body,
                "draft": bool(meta.get("draft")),
            },
        )
        numbers[key] = created["number"]
        state = "draft" if meta.get("draft") else "open"
        print(f"  {key:>8}  {state:>5}  {created.get('html_url')}")

        if meta.get("labels"):
            api.post(
                f"/repos/{repo}/issues/{created['number']}/labels",
                {"labels": meta["labels"]},
            )

    print("\n== discussion ==")
    for key, thread in comments.items():
        if key.startswith("_") or key not in numbers:
            continue
        for comment in thread:
            api.post(
                f"/repos/{repo}/issues/{numbers[key]}/comments", {"body": comment["body"]}
            )
        print(f"  {key:>8}  {len(thread)} comments")


def update_bodies(repo, api):
    """Rewrite the bodies of issues and pull requests that already exist.

    Issues and pull requests cannot be deleted on GitHub, so when the source
    text changes -- a name removed, a figure taken out -- the only way to fix
    what is already published is to patch it in place. Matching is by title,
    which is stable here because every title starts with its work item key.

    Comments are not touched: they carry their own text and there is no title
    to match them on. If a comment needs to change, edit it by hand or seed a
    fresh repository.
    """
    print("== updating existing issues and pull requests ==")

    existing = {}
    for state in ("open", "closed"):
        for item in api.get(
            f"/repos/{repo}/issues", {"state": state, "per_page": 100}
        ):
            existing[item["title"]] = item["number"]

    with open(os.path.join(HERE, "issues.json"), encoding="utf-8") as handle:
        for issue in json.load(handle)["issues"]:
            number = existing.get(issue["title"])
            if number is None:
                print(f"  {issue['key']:>8}  not found, skipped")
                continue
            api.patch(f"/repos/{repo}/issues/{number}", {"body": issue["body"]})
            print(f"  {issue['key']:>8}  patched #{number}")

    for key in PULL_REQUESTS:
        meta, body = read_front_matter(os.path.join(HERE, "prs", f"{key}.md"))
        title = (
            f"{meta['title']} (merged {meta['merged']})"
            if meta["state"] == "merged"
            else meta["title"]
        )
        number = existing.get(title)
        if number is None:
            print(f"  {key:>8}  not found, skipped")
            continue
        api.patch(f"/repos/{repo}/issues/{number}", {"body": body})
        print(f"  {key:>8}  patched #{number}")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument(
        "--dry-run", action="store_true", help="print every request instead of sending it"
    )
    parser.add_argument(
        "--reset-remote",
        action="store_true",
        help="close open pull requests and delete non-default branches first",
    )
    parser.add_argument(
        "--skip-push", action="store_true", help="branches are already pushed"
    )
    parser.add_argument(
        "--update-only",
        action="store_true",
        help="push, then rewrite the bodies of issues and pull requests that "
        "already exist instead of creating new ones",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token and not args.dry_run:
        sys.exit(
            "GITHUB_TOKEN is not set. Create a token with 'repo' scope at\n"
            "https://github.com/settings/tokens and export it, or run with\n"
            "--dry-run to see what this would do."
        )

    api = GitHub(args.repo, token, args.dry_run)

    if args.reset_remote and not args.dry_run:
        reset_remote(api, args.repo)
    if not args.skip_push:
        push_branches(args.repo, token, args.dry_run)
    if args.update_only:
        update_bodies(args.repo, api)
    else:
        seed(args.repo, api)

    print("\nDone.")
    if not args.dry_run:
        print(f"https://github.com/{args.repo}/pulls")


if __name__ == "__main__":
    main()
