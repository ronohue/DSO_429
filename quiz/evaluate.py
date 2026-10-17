"""Score the deterministic solver against the practice answer keys.

Usage: python quiz/evaluate.py [questions.csv] [practice_keys.csv]
Defaults to downloading both files from the course repo.
"""

import collections
import csv
import io
import sys

from fetch import KEYS_URL, QUESTIONS_URL, download
from solvers import solve


def load(path_or_url):
    if path_or_url.startswith("http"):
        return list(csv.DictReader(io.StringIO(download(path_or_url))))
    with open(path_or_url, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    qpath = sys.argv[1] if len(sys.argv) > 1 else QUESTIONS_URL
    kpath = sys.argv[2] if len(sys.argv) > 2 else KEYS_URL
    keys = {(r["round_id"], r["q_index"]): r["answer"] for r in load(kpath)}
    stats = collections.Counter()
    for r in load(qpath):
        k = keys.get((r["round_id"], r["q_index"]))
        if k is None:
            continue
        letter, name = solve(r["question_text"], [r[f"option_{c}"] for c in "abcd"])
        if letter is None:
            stats["unsolved"] += 1
            print("UNSOLVED", r["round_id"], r["q_index"], r["question_text"])
        elif letter == k:
            stats["correct"] += 1
        else:
            stats["wrong"] += 1
            print("WRONG", name, r["round_id"], r["q_index"], r["question_text"],
                  f"got {letter} want {k}")
    print(dict(stats))
    return 1 if stats["wrong"] else 0


if __name__ == "__main__":
    sys.exit(main())
