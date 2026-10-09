"""Build the github.com/am2222 profile README as pinned-style repo cards.

Reads the project groups from ../_config.yml (the same list the website
uses), fetches live repo data from the GitHub API, and writes into OUT_DIR:

    README.md
    cards/<repo>-light.svg
    cards/<repo>-dark.svg

Usage: python3 make_profile.py OUT_DIR
Auth: GITHUB_TOKEN / GH_TOKEN if set (raises the API rate limit), else anonymous.
"""
import json
import os
import sys
import textwrap
import urllib.request
from html import escape
from pathlib import Path

import yaml

OWNER = "am2222"
ROOT = Path(__file__).resolve().parent.parent

# GitHub's Primer colour tokens for the two themes
THEMES = {
    "light": dict(bg="#ffffff", border="#d1d9e0", fg="#1f2328", muted="#59636e", accent="#0969da"),
    "dark": dict(bg="#0d1117", border="#3d444d", fg="#f0f6fc", muted="#9198a1", accent="#4493f8"),
}

WIDTH, HEIGHT = 400, 120
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

# Octicon paths (16px): repo, star, repo-forked
REPO_ICON = "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"
STAR_ICON = "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z"
FORK_ICON = "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"


def fetch_repo(name):
    req = urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{name}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def describe(text, width=58, lines=2):
    """Wrap to the card width and clamp to two lines, like GitHub's pinned cards."""
    wrapped = textwrap.wrap(text or "", width)
    if len(wrapped) > lines:
        wrapped = wrapped[:lines]
        wrapped[-1] = wrapped[-1][: width - 1].rstrip() + "…"
    return wrapped


def card_svg(repo, description, lang_color, t):
    desc = "".join(
        f'<text x="16" y="{62 + i * 18}" class="desc">{escape(line)}</text>'
        for i, line in enumerate(describe(description))
    )
    meta, x = [], 16
    if repo.get("language"):
        meta.append(f'<circle cx="{x + 6}" cy="98" r="6" fill="{lang_color}"/>'
                    f'<text x="{x + 16}" y="102" class="meta">{escape(repo["language"])}</text>')
        x += 16 + 7 * len(repo["language"]) + 16
    for count, icon in ((repo["stargazers_count"], STAR_ICON), (repo["forks_count"], FORK_ICON)):
        if count:
            meta.append(f'<path transform="translate({x} 90)" fill="{t["muted"]}" d="{icon}"/>'
                        f'<text x="{x + 20}" y="102" class="meta">{count}</text>')
            x += 20 + 7 * len(str(count)) + 16
    name = escape(repo["name"])
    pill_x = WIDTH - 16 - 46  # right-aligned, so it never collides with long names
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{name}">
<title>{name}: {escape(description or '')}</title>
<style>
  text {{ font-family: {FONT}; }}
  .name {{ font-size: 14px; font-weight: 600; fill: {t["accent"]}; }}
  .pill {{ font-size: 12px; font-weight: 500; fill: {t["muted"]}; }}
  .desc {{ font-size: 12px; fill: {t["muted"]}; }}
  .meta {{ font-size: 12px; fill: {t["muted"]}; }}
</style>
<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="6" fill="{t["bg"]}" stroke="{t["border"]}"/>
<path transform="translate(16 18)" fill="{t["muted"]}" d="{REPO_ICON}"/>
<text x="40" y="31" class="name">{name}</text>
<rect x="{pill_x}" y="18.5" width="46" height="18" rx="9" fill="none" stroke="{t["border"]}"/>
<text x="{pill_x + 23}" y="31.5" text-anchor="middle" class="pill">Public</text>
{desc}
{''.join(meta)}
</svg>
"""


def main(out_dir):
    out = Path(out_dir)
    (out / "cards").mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((ROOT / "_config.yml").read_text())
    colors = json.loads((ROOT / "_data" / "colors.json").read_text())

    sections = []
    for group in config["projects"]["groups"]:
        cards = []
        for item in group["repos"]:
            repo = fetch_repo(item["name"])
            description = item.get("description") or repo.get("description") or ""
            color = (colors.get(repo.get("language") or "") or {}).get("color") or "#8b949e"
            for theme, t in THEMES.items():
                (out / "cards" / f"{repo['name']}-{theme}.svg").write_text(card_svg(repo, description, color, t))
            cards.append(
                f'<a href="{repo["html_url"]}"><picture>'
                f'<source media="(prefers-color-scheme: dark)" srcset="cards/{repo["name"]}-dark.svg">'
                f'<img src="cards/{repo["name"]}-light.svg" alt="{escape(repo["name"])}" width="49%">'
                f"</picture></a>"
            )
        # Two cards per row, like the pinned grid
        rows = "\n".join(" ".join(cards[i:i + 2]) for i in range(0, len(cards), 2))
        sections.append(f"### {group['name']}\n\n<p>\n{rows}\n</p>")

    (out / "README.md").write_text(
        "<!-- Generated by am2222.github.io/profile/make_profile.py; edit _config.yml there, not this file. -->\n\n"
        + "\n\n".join(sections) + "\n"
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build")
