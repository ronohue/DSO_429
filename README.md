# DSO 429 Homework 3 — The Hourly Quiz

Answers to the hourly quiz from
[FaisalXL/dso429-hourly-quiz](https://github.com/FaisalXL/dso429-hourly-quiz),
one file per round in [`answers/`](answers/).

## How it works

A GitHub Actions workflow (`.github/workflows/answer-quiz.yml`) ran every
five minutes while the quiz was live. The homework is finished, so the workflow
has been removed; it is still in the git history if it's ever needed again.

1. `quiz/run.py` downloads `questions.csv` and groups it by round.
2. Each question is matched against deterministic solvers in
   `quiz/solvers.py` (compound interest, gross margin, sequences, discounts,
   percentage change, settlement dates, break-even, ratio splits, weighted
   averages, currency conversion, probability, revenue). A solver's answer is
   used only if it matches exactly one option at that option's precision.
3. Anything the solvers don't recognise goes to Claude (`quiz/llm.py`),
   if an `ANTHROPIC_API_KEY` repository secret is set.
4. New or changed answer files are committed and pushed to `main`.

Rounds younger than three hours were re-solved on each run (corrections still
count then); older rounds that already had a file were never touched.

## Checking accuracy

```
python quiz/evaluate.py      # scores the solvers against practice_keys.csv
```

The solvers answer all 1,200 practice questions correctly.
