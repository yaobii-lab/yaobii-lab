#!/usr/bin/env python3
"""Refresh the generated upstream-contributions section in the profile README."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERNAME = os.environ.get("GITHUB_USERNAME", "yaobii-lab")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = Path(__file__).resolve().parents[1] / "README.md"
START = "<!-- AUTO:CONTRIBUTIONS:START -->"
END = "<!-- AUTO:CONTRIBUTIONS:END -->"
LIMIT = int(os.environ.get("CONTRIBUTIONS_LIMIT", "6"))


def github_json(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{USERNAME}-profile-contributions",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def search(status: str) -> list[dict]:
    if status == "merged":
        q = f"is:pr author:{USERNAME} is:merged"
    elif status == "open":
        q = f"is:pr author:{USERNAME} is:open"
    else:
        raise ValueError(status)

    params = urlencode({"q": q, "sort": "updated", "order": "desc", "per_page": 100})
    data = github_json(f"https://api.github.com/search/issues?{params}")
    items = []
    for item in data.get("items", []):
        repo = item.get("repository_url", "").rstrip("/").split("/repos/")[-1]
        if not repo or repo.split("/", 1)[0].lower() == USERNAME.lower():
            continue
        items.append(
            {
                "repo": repo,
                "number": item["number"],
                "title": " ".join(item.get("title", "").split()),
                "url": item["html_url"],
                "updated_at": item.get("updated_at", ""),
                "status": status,
            }
        )
    return items


def collect() -> list[dict]:
    by_url: dict[str, dict] = {}
    for item in search("merged") + search("open"):
        by_url[item["url"]] = item
    return sorted(by_url.values(), key=lambda x: x["updated_at"], reverse=True)[:LIMIT]


def render(items: list[dict]) -> str:
    if not items:
        return "_No public upstream pull requests found yet._"

    lines = []
    for item in items:
        status = "merged" if item["status"] == "merged" else "open"
        lines.append(
            f"- **{item['repo']}** · [#{item['number']} {item['title']}]({item['url']}) · `{status}`"
        )
    return "\n".join(lines)


def update_readme(block: str) -> bool:
    text = README.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError("README contribution markers are missing or duplicated")
    before, tail = text.split(START, 1)
    _, after = tail.split(END, 1)
    new_text = f"{before}{START}\n{block}\n{END}{after}"
    if new_text == text:
        return False
    README.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    items = collect()
    changed = update_readme(render(items))
    print(f"contributions={len(items)} changed={str(changed).lower()}")


if __name__ == "__main__":
    main()
