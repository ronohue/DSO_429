import time
import urllib.request

BASE = "https://raw.githubusercontent.com/FaisalXL/dso429-hourly-quiz/main/"
QUESTIONS_URL = BASE + "questions.csv"
KEYS_URL = BASE + "practice_keys.csv"


def download(url, attempts=4):
    # Cache-bust so we never get a stale CDN copy of questions.csv.
    sep = "&" if "?" in url else "?"
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                f"{url}{sep}t={int(time.time())}",
                headers={"Cache-Control": "no-cache", "User-Agent": "dso429-quiz-bot"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(2 ** (i + 1))
