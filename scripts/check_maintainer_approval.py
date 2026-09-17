#!/usr/bin/env python3
"""Fail closed unless a write/admin maintainer explicitly approves the exact PR head.

This gate is designed for solo-maintainer repositories. It does not claim or
simulate independent human review. Approval is an explicit PR conversation
attestation bound to the exact current head SHA.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

APPROVE_PREFIX = "RESIDUAL-MAINTAINER-APPROVAL:"
REVOKE_PREFIX = "RESIDUAL-MAINTAINER-REVOKE:"
WRITE_PERMISSIONS = {"admin", "write"}
COMMENTS_PER_PAGE = 100
MAX_COMMENT_PAGES = 100


def _command(body: str) -> tuple[str, str] | None:
    text = body.strip()
    for action, prefix in (("approve", APPROVE_PREFIX), ("revoke", REVOKE_PREFIX)):
        if text.startswith(prefix):
            sha = text[len(prefix):].strip()
            if sha and " " not in sha and "\n" not in sha and "\t" not in sha:
                return action, sha
    return None


def current_head_approvers(
    head_sha: str,
    comments: Iterable[dict[str, Any]],
    permissions: dict[str, str],
) -> list[str]:
    """Return write/admin humans whose latest exact-head command is approval."""
    latest: dict[str, tuple[int, str]] = {}
    for comment in comments:
        user = comment.get("user") or {}
        login = str(user.get("login") or "")
        if not login:
            continue
        if str(user.get("type") or "User").lower() == "bot" or login.endswith("[bot]"):
            continue
        parsed = _command(str(comment.get("body") or ""))
        if parsed is None:
            continue
        action, sha = parsed
        if sha != head_sha:
            continue
        if str(permissions.get(login) or "none").lower() not in WRITE_PERMISSIONS:
            continue
        comment_id = int(comment.get("id") or 0)
        previous = latest.get(login)
        if previous is None or comment_id >= previous[0]:
            latest[login] = (comment_id, action)
    return sorted(login for login, (_, action) in latest.items() if action == "approve")


def evaluate(
    head_sha: str,
    comments: list[dict[str, Any]],
    permissions: dict[str, str],
) -> tuple[bool, str]:
    if not head_sha:
        return False, "missing pull-request current head SHA"
    approvers = current_head_approvers(head_sha, comments, permissions)
    if not approvers:
        return False, (
            "no exact-head maintainer attestation from a write/admin human; "
            f"add a PR comment exactly: {APPROVE_PREFIX} {head_sha}"
        )
    return True, f"exact-head maintainer approval: {', '.join(approvers)}"


def _github_json(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "residual-maintainer-approval-gate",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API HTTP {exc.code} for {url}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read GitHub data: {exc}") from exc


def github_pr(repository: str, pr_number: int, token: str) -> dict[str, Any]:
    data = _github_json(
        f"https://api.github.com/repos/{repository}/pulls/{pr_number}", token
    )
    if not isinstance(data, dict):
        raise RuntimeError("GitHub pull-request response is not an object")
    return data


def github_comments(repository: str, pr_number: int, token: str) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for page in range(1, MAX_COMMENT_PAGES + 1):
        data = _github_json(
            f"https://api.github.com/repos/{repository}/issues/{pr_number}/comments"
            f"?per_page={COMMENTS_PER_PAGE}&page={page}",
            token,
        )
        if not isinstance(data, list):
            raise RuntimeError(f"GitHub comments response page {page} is not a list")
        if not all(isinstance(comment, dict) for comment in data):
            raise RuntimeError(f"GitHub comments response page {page} contains a non-object")
        comments.extend(data)
        if len(data) < COMMENTS_PER_PAGE:
            return comments
    raise RuntimeError(
        f"GitHub comment pagination exceeded {MAX_COMMENT_PAGES} pages; "
        "maintainer approval cannot be established"
    )


def github_permission(repository: str, login: str, token: str) -> str:
    safe_login = urllib.parse.quote(login, safe="")
    url = f"https://api.github.com/repos/{repository}/collaborators/{safe_login}/permission"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "residual-maintainer-approval-gate",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "none"
        raise RuntimeError(f"could not read maintainer permission for {login}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read maintainer permission for {login}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"permission response for {login} is not an object")
    permission = str(data.get("permission") or "none").lower()
    if permission not in {"admin", "write", "read", "none"}:
        raise RuntimeError(f"unknown repository permission for {login}: {permission}")
    return permission


def candidate_logins(comments: Iterable[dict[str, Any]], head_sha: str) -> list[str]:
    logins: set[str] = set()
    for comment in comments:
        parsed = _command(str(comment.get("body") or ""))
        if parsed is None or parsed[1] != head_sha:
            continue
        user = comment.get("user") or {}
        login = str(user.get("login") or "")
        if login and str(user.get("type") or "User").lower() != "bot" and not login.endswith("[bot]"):
            logins.add(login)
    return sorted(logins)


def _event_pr_number(payload: dict[str, Any]) -> int:
    pr = payload.get("pull_request") or {}
    if pr.get("number"):
        return int(pr["number"])
    issue = payload.get("issue") or {}
    if issue.get("number") and issue.get("pull_request"):
        return int(issue["number"])
    number = payload.get("number")
    if number:
        return int(number)
    raise RuntimeError("event payload does not identify a pull request")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--comments-json", help="offline comments instead of GitHub API")
    parser.add_argument("--permissions-json", help="offline login->permission mapping")
    parser.add_argument("--head-sha", help="offline/current head override")
    args = parser.parse_args(argv)

    if not args.event:
        print("BLOCKED: event payload path is required", file=sys.stderr)
        return 2
    try:
        with open(args.event, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        repository = str((payload.get("repository") or {}).get("full_name") or os.environ.get("GITHUB_REPOSITORY") or "")
        pr_number = _event_pr_number(payload)
        token = os.environ.get("GITHUB_TOKEN", "")

        if args.comments_json:
            with open(args.comments_json, "r", encoding="utf-8") as fh:
                comments = json.load(fh)
            pr = payload.get("pull_request") or {}
        else:
            if not repository or not token:
                raise RuntimeError("repository and GITHUB_TOKEN are required")
            pr = github_pr(repository, pr_number, token)
            comments = github_comments(repository, pr_number, token)

        if not isinstance(comments, list) or not all(isinstance(c, dict) for c in comments):
            raise RuntimeError("comments input must be a list of objects")
        head_sha = str(args.head_sha or (pr.get("head") or {}).get("sha") or "")

        if args.permissions_json:
            with open(args.permissions_json, "r", encoding="utf-8") as fh:
                permissions = json.load(fh)
        else:
            if not repository or not token:
                raise RuntimeError("repository and GITHUB_TOKEN are required")
            permissions = {
                login: github_permission(repository, login, token)
                for login in candidate_logins(comments, head_sha)
            }
        if not isinstance(permissions, dict):
            raise RuntimeError("permissions input must be an object")

        ok, detail = evaluate(head_sha, comments, {str(k): str(v) for k, v in permissions.items()})
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2

    if not ok:
        print(f"BLOCKED: {detail}", file=sys.stderr)
        return 1
    print(f"PASS: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
