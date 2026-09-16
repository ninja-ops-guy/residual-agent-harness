#!/usr/bin/env python3
"""Fail closed unless a pull request has a current-head authorized independent human approval."""
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

MEANINGFUL_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
WRITE_REVIEW_PERMISSIONS = {"admin", "write"}
REVIEWS_PER_PAGE = 100
MAX_REVIEW_PAGES = 100


def current_head_human_approvals(
    pr_author: str,
    head_sha: str,
    reviews: Iterable[dict[str, Any]],
) -> list[str]:
    """Return non-author human reviewers whose latest meaningful current-head review is APPROVED."""
    latest: dict[str, tuple[str, str]] = {}
    for review in reviews:
        state = str(review.get("state") or "").upper()
        if state not in MEANINGFUL_STATES:
            continue
        if review.get("commit_id") != head_sha:
            continue
        user = review.get("user") or review.get("author") or {}
        login = str(user.get("login") or "")
        if not login or login == pr_author:
            continue
        if str(user.get("type") or "User").lower() == "bot" or login.endswith("[bot]"):
            continue
        submitted_at = str(review.get("submitted_at") or "")
        previous = latest.get(login)
        if previous is None or submitted_at >= previous[0]:
            latest[login] = (submitted_at, state)
    return sorted(login for login, (_, state) in latest.items() if state == "APPROVED")


def qualifying_reviewers(
    pr_author: str,
    head_sha: str,
    reviews: Iterable[dict[str, Any]],
    permissions: dict[str, str],
) -> list[str]:
    """Return current-head approvers whose repository permission can satisfy required review policy."""
    candidates = current_head_human_approvals(pr_author, head_sha, reviews)
    return sorted(
        login for login in candidates
        if str(permissions.get(login) or "none").lower() in WRITE_REVIEW_PERMISSIONS
    )


def evaluate(
    payload: dict[str, Any],
    reviews: list[dict[str, Any]],
    permissions: dict[str, str],
) -> tuple[bool, str]:
    pr = payload.get("pull_request") or {}
    author = str((pr.get("user") or {}).get("login") or "")
    head_sha = str((pr.get("head") or {}).get("sha") or "")
    if not author or not head_sha:
        return False, "missing pull-request author or current head SHA"
    reviewers = qualifying_reviewers(author, head_sha, reviews, permissions)
    if not reviewers:
        return False, (
            "no independent human APPROVED review from a write-authorized reviewer "
            f"is bound to current head {head_sha}"
        )
    return True, f"independent current-head approval: {', '.join(reviewers)}"


def _github_json(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "residual-independent-review-gate",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read GitHub review authority: {exc}") from exc


def github_reviews(repository: str, pr_number: int, token: str) -> list[dict[str, Any]]:
    """Fetch every review page, failing closed if the bounded traversal cannot finish."""
    reviews: list[dict[str, Any]] = []
    for page in range(1, MAX_REVIEW_PAGES + 1):
        data = _github_json(
            "https://api.github.com/repos/"
            f"{repository}/pulls/{pr_number}/reviews"
            f"?per_page={REVIEWS_PER_PAGE}&page={page}",
            token,
        )
        if not isinstance(data, list):
            raise RuntimeError(f"GitHub reviews response page {page} is not a list")
        if not all(isinstance(review, dict) for review in data):
            raise RuntimeError(f"GitHub reviews response page {page} contains a non-object review")
        reviews.extend(data)
        if len(data) < REVIEWS_PER_PAGE:
            return reviews
    raise RuntimeError(
        f"GitHub reviews pagination exceeded {MAX_REVIEW_PAGES} pages; "
        "independent review cannot be established"
    )


def github_reviewer_permission(repository: str, login: str, token: str) -> str:
    safe_login = urllib.parse.quote(login, safe="")
    url = f"https://api.github.com/repos/{repository}/collaborators/{safe_login}/permission"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "residual-independent-review-gate",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "none"
        raise RuntimeError(f"could not read reviewer permission for {login}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read reviewer permission for {login}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"reviewer permission response for {login} is not an object")
    permission = str(data.get("permission") or "none").lower()
    if permission not in {"admin", "write", "read", "none"}:
        raise RuntimeError(f"unknown repository permission for reviewer {login}: {permission}")
    return permission


def github_reviewer_permissions(
    repository: str,
    reviewers: Iterable[str],
    token: str,
) -> dict[str, str]:
    return {login: github_reviewer_permission(repository, login, token) for login in reviewers}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--reviews-json", help="offline review input instead of GitHub API")
    parser.add_argument("--permissions-json", help="offline reviewer-permission mapping")
    args = parser.parse_args(argv)
    if not args.event:
        print("BLOCKED: event payload path is required", file=sys.stderr)
        return 2
    try:
        with open(args.event, encoding="utf-8") as handle:
            payload = json.load(handle)
        pr = payload.get("pull_request") or {}
        author = str((pr.get("user") or {}).get("login") or "")
        head_sha = str((pr.get("head") or {}).get("sha") or "")
        if not author or not head_sha:
            raise RuntimeError("pull-request author and current head SHA are required")
        if args.reviews_json:
            if not args.permissions_json:
                raise RuntimeError("--permissions-json is required with --reviews-json")
            with open(args.reviews_json, encoding="utf-8") as handle:
                reviews = json.load(handle)
            with open(args.permissions_json, encoding="utf-8") as handle:
                permissions = json.load(handle)
        else:
            repository = str((payload.get("repository") or {}).get("full_name") or os.environ.get("GITHUB_REPOSITORY") or "")
            pr_number = int(pr.get("number") or payload.get("number") or 0)
            token = os.environ.get("GITHUB_TOKEN", "")
            if not repository or not pr_number or not token:
                raise RuntimeError("repository, pull-request number, and GITHUB_TOKEN are required")
            reviews = github_reviews(repository, pr_number, token)
            candidates = current_head_human_approvals(author, head_sha, reviews)
            permissions = github_reviewer_permissions(repository, candidates, token)
        if not isinstance(reviews, list):
            raise RuntimeError("reviews input is not a list")
        if not isinstance(permissions, dict) or not all(
            isinstance(login, str) and isinstance(permission, str)
            for login, permission in permissions.items()
        ):
            raise RuntimeError("reviewer permissions input is not a string mapping")
        ok, detail = evaluate(payload, reviews, permissions)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: independent review could not be established: {exc}", file=sys.stderr)
        return 2
    if not ok:
        print(f"BLOCKED: {detail}", file=sys.stderr)
        return 1
    print(f"PASS: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
