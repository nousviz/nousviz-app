#!/usr/bin/env bash
# NousViz — PR hygiene: refuse a branch that carries commits already on its base.
#
# Usage:
#   scripts/ci/check-pr-commits.sh <base-ref> [<head-ref>]      # head defaults to HEAD
#
# `git cherry` compares patch ids, so it finds commits whose change is already
# on the base under a different hash: the signature of a branch cut from a
# rewritten or stale copy of the base. Merging such a branch duplicates those
# commits in the base's history, and GitHub still reports it as mergeable.
#
# P211. Background: PR #14 (2026-10-03) was merged from a branch cut off a
# rewritten copy of main and brought 31 duplicate commits into main.
#
# Exit codes: 0 clean, 1 duplicates found, 2 usage or repository problem.
set -euo pipefail

BASE="${1:-}"
HEAD_REF="${2:-HEAD}"
if [ -z "$BASE" ]; then
    echo "usage: check-pr-commits.sh <base-ref> [<head-ref>]" >&2
    exit 2
fi
if [ "$(git rev-parse --is-shallow-repository)" = "true" ]; then
    echo "error: shallow clone. This check needs full history (fetch-depth: 0)." >&2
    exit 2
fi
for ref in "$BASE" "$HEAD_REF"; do
    if ! git rev-parse --verify --quiet "${ref}^{commit}" >/dev/null; then
        echo "error: ref '${ref}' not found." >&2
        exit 2
    fi
done

total=$(git rev-list --count "${BASE}..${HEAD_REF}")
cherry=$(git cherry -v "$BASE" "$HEAD_REF")
dupes=$(printf '%s\n' "$cherry" | grep -c '^- ' || true)
fresh=$(printf '%s\n' "$cherry" | grep -c '^+ ' || true)

echo "Commits on ${HEAD_REF} that are not on ${BASE}: ${total}"
echo "  new changes:                          ${fresh}"
echo "  already on ${BASE} under another hash: ${dupes}"
echo "  (merge commits are not compared)"

if [ "$dupes" -gt 0 ]; then
    echo
    echo "FAIL: ${dupes} commit(s) on this branch repeat changes that are already on ${BASE}."
    echo "The branch was probably cut from a rewritten or out-of-date copy of ${BASE}."
    echo "Merging it would put those commits into ${BASE}'s history a second time."
    echo
    printf '%s\n' "$cherry" | grep '^- ' | head -25 | sed 's/^- /    /'
    if [ "$dupes" -gt 25 ]; then
        echo "    ... and $((dupes - 25)) more"
    fi
    echo
    echo "Fix:  git fetch origin && git rebase origin/<base-branch>"
    echo "      The repeated commits drop out and only your own remain."
    exit 1
fi
echo "OK"
