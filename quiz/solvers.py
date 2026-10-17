"""Deterministic solvers for the DSO 429 hourly quiz question templates.

Each solver takes the question text and returns either a computed value
(number or string) or None if the question doesn't match its template.
`pick_option` then maps the value to the closest option letter, and refuses
to answer if nothing is close enough, so an unexpected variation falls
through to the LLM instead of producing a confident wrong answer.
"""

import math
import re
from datetime import datetime, timedelta

NUM = r"\$?(-?[\d,]*\.?\d+)"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def num(s):
    return float(s.replace(",", "").replace("$", ""))


def parse_option(text):
    """Turn an option like '$1,234.50', '-15.1%', '667 units' into a float."""
    m = re.search(r"-?[\d,]*\.?\d+", text.replace("$", ""))
    return num(m.group(0)) if m else None


# --- solvers --------------------------------------------------------------

PERIODS = {"annually": 1, "yearly": 1, "semi-annually": 2, "semiannually": 2,
           "quarterly": 4, "monthly": 12, "weekly": 52, "daily": 365}


def compound_interest(q):
    m = re.search(rf"{NUM} grows at {NUM}% compounded ([\w-]+)\..*?after {NUM} years?", q)
    if not m:
        return None
    p, r, freq, t = num(m[1]), num(m[2]) / 100, m[3].lower(), num(m[4])
    if freq not in PERIODS:
        return None
    n = PERIODS[freq]
    return p * (1 + r / n) ** (n * t)


def simple_interest(q):
    m = re.search(rf"{NUM} (?:earns|grows at) {NUM}% simple interest.*?after {NUM} years?", q)
    if not m:
        return None
    p, r, t = num(m[1]), num(m[2]) / 100, num(m[3])
    return p * (1 + r * t)


def gross_margin(q):
    m = re.search(rf"generates {NUM} in revenue against {NUM} in cost of goods sold\..*gross margin", q)
    if not m:
        return None
    rev, cogs = num(m[1]), num(m[2])
    return (rev - cogs) / rev * 100


def next_in_series(q):
    m = re.search(r"series runs ([-\d.,\s]+?)\. If the pattern continues, what is the next value", q)
    if not m:
        return None
    xs = [float(x) for x in re.split(r",\s*", m[1].strip()) if x]
    if len(xs) < 3:
        return None
    diffs = {round(b - a, 9) for a, b in zip(xs, xs[1:])}
    if len(diffs) == 1:
        return xs[-1] + diffs.pop()
    if all(x != 0 for x in xs):
        ratios = {round(b / a, 9) for a, b in zip(xs, xs[1:])}
        if len(ratios) == 1:
            return xs[-1] * ratios.pop()
    # second differences constant (quadratic)
    d1 = [b - a for a, b in zip(xs, xs[1:])]
    d2 = {round(b - a, 9) for a, b in zip(d1, d1[1:])}
    if len(d2) == 1:
        return xs[-1] + d1[-1] + d2.pop()
    return None


def discount(q):
    m = re.search(rf"listed at {NUM} is (discounted|marked up) by {NUM}%\..*(sale|new|final) price", q)
    if not m:
        return None
    price, pct = num(m[1]), num(m[3]) / 100
    return price * (1 - pct) if m[2] == "discounted" else price * (1 + pct)


def percent_change(q):
    m = re.search(rf"moved from {NUM} to {NUM}\..*percentage change", q)
    if not m:
        return None
    a, b = num(m[1]), num(m[2])
    return (b - a) / a * 100


def settlement_date(q):
    m = re.search(r"signed on (\d{1,2}) (\w+) (\d{4}) has an? (\d+)-day settlement period", q)
    if not m or m[2] not in MONTHS:
        return None
    d = datetime(int(m[3]), MONTHS.index(m[2]) + 1, int(m[1])) + timedelta(days=int(m[4]))
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def break_even(q):
    m = re.search(rf"Fixed costs are {NUM}\. Each unit sells for {NUM} with a variable cost of {NUM}\..*break even", q)
    if not m:
        return None
    fixed, price, var = num(m[1]), num(m[2]), num(m[3])
    if price <= var:
        return None
    units = fixed / (price - var)
    if "nearest unit" in q:
        return float(math.floor(units + 0.5))
    return float(math.ceil(units))


ORDINAL = {"first": 0, "second": 1, "third": 2, "fourth": 3}


def ratio_split(q):
    m = re.search(rf"A {NUM} [\w\s]*?budget is split between \w+ \w+ in the ratio ([\d:]+)\. What does the (\w+) \w+ receive", q)
    if not m:
        return None
    total = num(m[1])
    parts = [float(x) for x in m[2].split(":")]
    idx = ORDINAL.get(m[3].lower())
    if idx is None or idx >= len(parts):
        return None
    return total * parts[idx] / sum(parts)


def weighted_average(q):
    m = re.search(rf"had (\d+) orders averaging {NUM}; region \w+ had (\d+) orders averaging {NUM}\..*overall average", q)
    if not m:
        return None
    n1, a1, n2, a2 = num(m[1]), num(m[2]), num(m[3]), num(m[4])
    return (n1 * a1 + n2 * a2) / (n1 + n2)


def currency(q):
    m = re.search(rf"for {NUM} is converted to (\w+) at {NUM} (\w+) per ([\w\s.]+?)\. How many", q)
    if not m:
        return None
    amount, target, rate, per = num(m[1]), m[2].lower(), num(m[3]), m[5].lower()
    # "converted to euros at R euros per US dollar" -> multiply;
    # "converted to euros at R US dollars per euro" -> divide.
    if target.rstrip("s") in per:
        return amount / rate
    return amount * rate


def probability(q):
    m = re.search(r"holds (.+?)\. If one is drawn at random, what is the probability it is (not )?an? (\w+) ticket", q)
    if not m:
        return None
    counts = {k.lower(): int(n) for n, k in re.findall(r"(\d+) (\w+) tickets?", m[1])}
    target = m[3].lower()
    if target not in counts:
        return None
    total = sum(counts.values())
    p = counts[target] / total
    if m[2]:
        p = 1 - p
    return p * 100


def total_revenue(q):
    m = re.search(rf"sells ([\d,]+) units at {NUM} each\..*total revenue", q)
    if not m:
        return None
    return num(m[1]) * num(m[2])


SOLVERS = [compound_interest, simple_interest, gross_margin, next_in_series,
           discount, percent_change, settlement_date, break_even, ratio_split,
           weighted_average, currency, probability, total_revenue]


def decimals(text):
    m = re.search(r"\.(\d+)", text)
    return len(m.group(1)) if m else 0


def pick_option(value, options):
    """Return the letter whose option matches `value`, or None if unsure.

    An option matches when it equals `value` rounded to the option's own
    precision (with a little slack for float error and half-up rounding).
    Exactly one option must match.
    """
    letters = "ABCD"
    if isinstance(value, str):
        hits = [l for l, o in zip(letters, options) if o.strip().lower() == value.lower()]
        return hits[0] if len(hits) == 1 else None
    hits = []
    for letter, opt in zip(letters, options):
        p = parse_option(opt)
        if p is None:
            continue
        tol = 0.5 * 10 ** -decimals(opt) * 1.02 + 1e-9
        if abs(p - value) <= tol:
            hits.append(letter)
    return hits[0] if len(hits) == 1 else None


def solve(question, options):
    """Return (letter, solver_name) or (None, None)."""
    for solver in SOLVERS:
        try:
            value = solver(question)
        except (ValueError, ZeroDivisionError, OverflowError):
            value = None
        if value is None:
            continue
        letter = pick_option(value, options)
        if letter:
            return letter, solver.__name__
    return None, None
