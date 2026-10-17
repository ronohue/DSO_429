"""Fetch questions.csv and write answers/round-NNNN.json for every round.

Rounds already answered are left alone once they're more than three hours
old (graded versions lock at that point). Newer rounds are re-solved each
run, so a round first answered from a partially published CSV, or with LLM
guesses, gets corrected while corrections still count.
"""

import csv
import io
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import llm
from fetch import QUESTIONS_URL, download
from solvers import solve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSWERS = os.path.join(ROOT, "answers")
EDIT_WINDOW = timedelta(hours=3)


def released(rows):
    try:
        return datetime.fromisoformat(rows[0]["released_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None


def solve_round(round_id, rows):
    answers, unsolved = {}, []
    for r in rows:
        qid = f"q{int(r['q_index'])}"
        opts = [r[f"option_{c}"] for c in "abcd"]
        letter, _ = solve(r["question_text"], opts)
        if letter:
            answers[qid] = letter
        else:
            unsolved.append((qid, r["question_text"], opts))
    if unsolved:
        print(f"round {round_id}: {len(unsolved)} question(s) sent to Claude")
        answers.update(llm.answer(unsolved))
    for i in range(1, 26):
        # Never leave a blank: a guess beats a guaranteed zero.
        answers.setdefault(f"q{i}", "A")
    return {"round_id": round_id,
            "answers": {f"q{i}": answers[f"q{i}"] for i in range(1, 26)}}


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else QUESTIONS_URL
    if source.startswith("http"):
        text = download(source)
    else:
        with open(source, encoding="utf-8") as f:
            text = f.read()
    rounds = defaultdict(list)
    for r in csv.DictReader(io.StringIO(text)):
        rounds[int(r["round_id"])].append(r)

    os.makedirs(ANSWERS, exist_ok=True)
    now = datetime.now(timezone.utc)
    written = []
    for round_id in sorted(rounds):
        rows = rounds[round_id]
        path = os.path.join(ANSWERS, f"round-{round_id:04d}.json")
        when = released(rows)
        fresh = when is None or now - when < EDIT_WINDOW
        if os.path.exists(path) and not fresh:
            continue
        content = json.dumps(solve_round(round_id, rows), indent=2) + "\n"
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                if f.read() == content:
                    continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(round_id)
    print(f"wrote rounds: {written}" if written else "nothing new")


if __name__ == "__main__":
    main()
