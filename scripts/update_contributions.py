#!/usr/bin/env python3
"""Refresh the generated upstream-contributions section and SVG card wall."""

from __future__ import annotations

import html
import json
import os
import textwrap
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERNAME = os.environ.get("GITHUB_USERNAME", "yaobii-lab")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ASSET = ROOT / "assets" / "open-source-contributions.svg"
START = "<!-- AUTO:CONTRIBUTIONS:START -->"
END = "<!-- AUTO:CONTRIBUTIONS:END -->"
LIMIT = int(os.environ.get("CONTRIBUTIONS_LIMIT", "6"))
EXCLUDED_REPOS = {
    "moonlin1213/cove-sensory-mcp",
}


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
    excluded = {name.lower() for name in EXCLUDED_REPOS}

    for item in data.get("items", []):
        repo = item.get("repository_url", "").rstrip("/").split("/repos/")[-1]
        if not repo:
            continue
        if repo.split("/", 1)[0].lower() == USERNAME.lower():
            continue
        if repo.lower() in excluded:
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


def date_iso(value: str) -> str:
    if not value:
        return "unknown"
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()


def date_pretty(value: str) -> str:
    if not value:
        return "Unknown"
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.strftime("%b %d, %Y").replace(" 0", " ")


def title_lines(title: str) -> list[str]:
    return textwrap.wrap(
        title,
        width=44,
        max_lines=2,
        placeholder="…",
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]


def render_details(items: list[dict]) -> str:
    if not items:
        return "_No public upstream pull requests found yet._"

    lines = [
        "![Recent upstream contributions](./assets/open-source-contributions.svg)",
        "",
        "<details>",
        "<summary>PR details</summary>",
        "",
    ]
    for item in items:
        lines.append(
            f"- \`{item['status'].upper()}\` **{item['repo']}** — "
            f"[#{item['number']} {item['title']}]({item['url']}) — "
            f"updated {date_iso(item['updated_at'])}"
        )
    lines.extend(["", "</details>"])
    return "\n".join(lines)


def render_svg(items: list[dict]) -> str:
    width, height = 1200, 576
    card_w, card_h = 570, 172
    gap_x, gap_y = 36, 12
    margin_x, margin_y = 12, 12

    cards: list[str] = []
    for index, item in enumerate(items[:6]):
        col = index % 2
        row = index // 2
        x = margin_x + col * (card_w + gap_x)
        y = margin_y + row * (card_h + gap_y)
        lines = title_lines(item["title"])
        status = item["status"].lower()
        status_label = status.upper()
        repo = html.escape(item["repo"], quote=False)
        line1 = html.escape(lines[0], quote=False)
        line2 = html.escape(lines[1], quote=False) if len(lines) > 1 else ""

        cards.append(
            f"""<g class="card-wrap">
  <rect class="card" x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="18"/>
  <text class="repo" x="{x + 24}" y="{y + 34}">{repo}</text>
  <rect class="pill {status}-pill" x="{x + card_w - 112}" y="{y + 18}" width="88" height="26" rx="13"/>
  <text class="pill-text {status}-text" x="{x + card_w - 68}" y="{y + 36}" text-anchor="middle">{status_label}</text>
  <text class="meta" x="{x + 24}" y="{y + 64}">PR #{item['number']}</text>
  <text class="title" x="{x + 24}" y="{y + 94}">{line1}</text>
  {f'<text class="title" x="{x + 24}" y="{y + 118}">{line2}</text>' if line2 else ''}
  <text class="date" x="{x + 24}" y="{y + 148}">Updated {date_pretty(item['updated_at'])}</text>
</g>"""
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">Recent open-source contributions</title>
<desc id="desc">Recent upstream pull requests by {html.escape(USERNAME, quote=False)}, shown as a two-column card wall.</desc>
<style>
  .card{{fill:#ffffff;stroke:#d0d7de;stroke-width:1}}
  .repo{{fill:#57606a;font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
  .meta,.date{{fill:#6e7781;font:500 13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
  .title{{fill:#24292f;font:600 18px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
  .pill{{stroke-width:1}}
  .pill-text{{font:700 11px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:.4px}}
  .merged-pill{{fill:#fbefff;stroke:#d8b9ff}}.merged-text{{fill:#8250df}}
  .open-pill{{fill:#dafbe1;stroke:#aceebb}}.open-text{{fill:#1a7f37}}
  @media (prefers-color-scheme: dark){{
    .card{{fill:#0d1117;stroke:#30363d}}
    .repo,.meta,.date{{fill:#8b949e}}
    .title{{fill:#f0f6fc}}
    .merged-pill{{fill:#2f153f;stroke:#6e40c9}}.merged-text{{fill:#d2a8ff}}
    .open-pill{{fill:#0f2d1c;stroke:#238636}}.open-text{{fill:#7ee787}}
  }}
</style>
{chr(10).join(cards)}
</svg>
"""


def write_if_changed(path: Path, content: str) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


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
    svg_changed = write_if_changed(ASSET, render_svg(items))
    readme_changed = update_readme(render_details(items))
    print(
        f"contributions={len(items)} "
        f"readme_changed={str(readme_changed).lower()} "
        f"svg_changed={str(svg_changed).lower()}"
    )


if __name__ == "__main__":
    main()
