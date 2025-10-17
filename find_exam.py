#!/usr/bin/env python3
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://drive.switch.ch/index.php/s/BnL19x4G1Xk0Ran"

# Your file list
with open("files.json", "r", encoding="utf-8") as f:
    FILES = json.load(f)


def filter_by_year(files, year):
    """Return only the paths matching the selected year."""
    prefix = {
        1: "1ere/",
        2: "2eme/",
        3: "3eme/",
    }.get(year)
    if not prefix:
        raise ValueError("Year must be 1, 2, or 3.")
    return [p for p in files if p.startswith(prefix)]


def build_url(path: str) -> str:
    """Convert a relative file path to a public Switch Drive URL."""
    from urllib.parse import quote

    # The path must be URL-encoded, starting with / and ending with #pdfviewer
    encoded = quote("/" + path)
    return f"{BASE_URL}?path={encoded}#pdfviewer"


def find_exam(query, year=None):
    """Send query + filtered paths to LLM and return best path(s)."""
    candidates = FILES
    if year:
        candidates = filter_by_year(FILES, year)

    # Build prompt
    prompt = (
        f"The user asked for: {query}\n"
        "Choose the most relevant file path(s) from the list below.\n"
        "Only respond with one or several exact paths (one per line) from the list.\n\n"
        + "\n".join(candidates)
    )

    # Query LLM
    client = OpenAI()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    result = resp.choices[0].message.content.strip()
    return result


if __name__ == "__main__":
    query = input("Search for exam: ")
    year = int(input("Year (1, 2, or 3): "))
    matches = find_exam(query, year)

    print("\nBest match(es):")
    for line in matches.splitlines():
        path = line.strip()
        if not path:
            continue
        url = build_url(path)
        print(f"- {path}")
        print(f"  → {url}")
