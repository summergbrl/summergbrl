#!/usr/bin/env python3
"""
Kali-Linux-terminal-styled neofetch profile SVG generator.

Same engine as the original script, but wrapped in a dark terminal window
(title bar + traffic-light dots) and recolored to match the classic
Kali look: red "user@host" header/prompt, cyan/blue field values,
light-blue ASCII art, navy window background.

Env vars:
  GITHUB_LOGIN   - github username to fetch stats for (required)
  GITHUB_TOKEN   - token with at least public read access (required for live stats)
  AVATAR_PATH    - optional explicit path to an avatar image
  OUT_PATH       - output svg path (default: profile.svg)
"""

import os
import sys
import random
import glob
from xml.sax.saxutils import escape as xml_escape

random.seed()

LOGIN = os.environ.get("GITHUB_LOGIN", "summergbrl")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = os.environ.get("OUT_PATH", "assets/profile.svg")

# ---------------------------------------------------------------------------
# Field list shown on the right, neofetch-style.
# ---------------------------------------------------------------------------
PROFILE_FIELDS = [
    ("Role", "IT systems & infrastructure manager"),
    ("Company", "Neuron Health Systems"),
    ("Location", "New Jersey, USA"),
    ("Focus", "healthcare platforms, automation, SEO"),
    ("Frontend", "next.js, react, typescript, tailwind"),
    ("Backend", "node, prisma, postgres, php"),
    ("Cloud", "aws, vercel, supabase, fly.io"),
    ("Scripting", "python, powershell"),
    ("AI", "claude, bedrock, groq, agents"),
    ("Tools", "git, vscode, claude code"),
    ("GitHub", f"github.com/{LOGIN}"),
    ("LinkedIn", "linkedin.com/in/summergabo"),
]

# ---- Kali color scheme -----------------------------------------------------
BG_COLOR = "#0d211b"          # deep forest (Neuron brand-deep, darkened)
TITLEBAR_COLOR = "#14342b"    # Neuron forest
TITLE_TEXT_COLOR = "#8fb3a3"
ACCENT = "#a3d856"             # Neuron logo lime
HEADER_COLOR = "#a3d856"       # lime header + prompt
LABEL_COLOR = "#f4f9ec"        # Neuron mist
VALUE_COLOR = "#7dc4a3"        # Neuron mint
PALETTE = ["#14342b", "#1f4a3e", "#1f5a27", "#4cae4f", "#7dc4a3",
           "#a3d856", "#2e9bef", "#f4f9ec"]

PROMPT_COMMANDS = [
    "it systems & infrastructure",
    "full-stack builder",
    "healthcare platform engineer",
    "automation & ai tooling",
]
MONO_STACK = "'SF Mono', 'JetBrains Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace"
PROMPT_TYPE_SPEED = 0.08
PROMPT_DELETE_SPEED = 0.045
PROMPT_HOLD_TIME = 1.1
PROMPT_GAP_TIME = 0.4
PROMPT_CHAR_W = 9.0

# RAMP = " .:-=+*#%@"
RAMP = " .:+#@"

CELL_W = 8.4
CELL_H = 15.0
ART_COLS = 40

TITLEBAR_H = 34


def find_avatar():
    explicit = os.environ.get("AVATAR_PATH")
    if explicit and os.path.exists(explicit):
        return explicit
    for pattern in ("assets/avatar.*", "avatar.*", ".github/avatar.*"):
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def ascii_rows_from_image(path):
    from PIL import Image
    import numpy as np

    img = Image.open(path).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    arr = np.array(img).astype(np.float32)
    rgb = arr[..., :3]
    alpha = arr[..., 3]

    has_real_alpha = alpha.min() < 250
    if not has_real_alpha:
        m = max(2, int(side * 0.05))
        corners = np.concatenate([
            rgb[0:m, 0:m].reshape(-1, 3),
            rgb[0:m, -m:].reshape(-1, 3),
            rgb[-m:, 0:m].reshape(-1, 3),
            rgb[-m:, -m:].reshape(-1, 3),
        ], axis=0)
        bg_color = np.median(corners, axis=0)
        dist = np.sqrt(((rgb - bg_color) ** 2).sum(axis=-1))
        alpha = np.clip((dist - 42.0) * 6.0, 0, 255)

    rows = max(1, round(ART_COLS * (CELL_W / CELL_H)))

    mask_img = Image.fromarray(alpha.astype(np.uint8), mode="L").resize((ART_COLS, rows), Image.LANCZOS)
    gray_img = Image.fromarray(rgb.astype(np.uint8)).convert("L").resize((ART_COLS, rows), Image.LANCZOS)
    mask_px = mask_img.load()
    gray_px = gray_img.load()

    out_rows = []
    for y in range(rows):
        line = []
        for x in range(ART_COLS):
            fg = mask_px[x, y] / 255.0
            if fg < 0.22:
                line.append(" ")
                continue
            lum = gray_px[x, y] / 255.0
            idx = min(len(RAMP) - 2, int(lum * (len(RAMP) - 1)))
            line.append(RAMP[idx])
        out_rows.append("".join(line))
    return out_rows


def ascii_rows_dragon():
    """Procedural Kali-dragon-ish silhouette (stylized, dotted) when no
    avatar is provided — echoes the curled-tail dragon look of the
    reference screenshot using the character ramp for shading."""
    rows_n = max(1, round(ART_COLS * (CELL_W / CELL_H)))
    mid_chars = ":;."

    def in_dragon(x, y):
        nx = (x - ART_COLS * 0.42) / (ART_COLS / 2)
        ny = (y - rows_n * 0.5) / (rows_n / 2)
        # a loose spiral/curl shape reminiscent of the Kali dragon curve
        r = (nx ** 2 + ny ** 2) ** 0.5
        theta = (nx * 3.4 + ny * 2.1)
        spiral = abs((r * 5.0 - theta) % 2.0 - 1.0) < 0.22
        body = r < 0.9
        return spiral and body

    out_rows = []
    for y in range(rows_n):
        line = []
        for x in range(ART_COLS):
            if in_dragon(x, y):
                if random.random() < 0.12:
                    line.append(" ")
                else:
                    line.append(random.choice(mid_chars))
            else:
                line.append(" ")
        out_rows.append("".join(line))
    return out_rows


def build_prompt_typing_svg(commands, x, y):
    if not commands:
        commands = [""]

    durations = []
    for cmd in commands:
        n = max(1, len(cmd))
        durations.append(n * PROMPT_TYPE_SPEED + PROMPT_HOLD_TIME + n * PROMPT_DELETE_SPEED + PROMPT_GAP_TIME)
    total = sum(durations)

    max_w = max(len(c) for c in commands) * PROMPT_CHAR_W

    keyframes_css = []
    cursor_stops = []
    groups_svg = []
    t = 0.0
    for i, cmd in enumerate(commands):
        n = max(1, len(cmd))
        full_w = n * PROMPT_CHAR_W
        type_dur = n * PROMPT_TYPE_SPEED
        delete_dur = n * PROMPT_DELETE_SPEED

        t_start = t
        t_type_end = t_start + type_dur
        t_hold_end = t_type_end + PROMPT_HOLD_TIME
        t_delete_end = t_hold_end + delete_dur
        t = t_delete_end + PROMPT_GAP_TIME

        def pct(sec):
            return round(max(0.0, min(100.0, sec / total * 100)), 3)

        stops = [
            (0, 0, "steps(1, jump-end)"),
            (pct(t_start), 0, f"steps({n}, jump-end)"),
            (pct(t_type_end), full_w, "steps(1, jump-end)"),
            (pct(t_hold_end), full_w, f"steps({n}, jump-end)"),
            (pct(t_delete_end), 0, "steps(1, jump-end)"),
            (100, 0, "steps(1, jump-end)"),
        ]
        seen = []
        for p, w, tf in stops:
            if seen and seen[-1][0] == p:
                seen[-1] = (p, w, tf)
            else:
                seen.append((p, w, tf))

        body = " ".join(
            f"{p}% {{ width: {w:.1f}px; animation-timing-function: {tf}; }}" for p, w, tf in seen
        )
        keyframes_css.append(f"@keyframes promptClip{i} {{ {body} }}")
        cursor_stops.extend(seen)

        groups_svg.append(f'''
      <clipPath id="promptClip{i}">
        <rect x="{x}" y="{y-14}" width="{full_w:.1f}" height="20" class="promptClipRect{i}" />
      </clipPath>''')

    text_svg = []
    for i, cmd in enumerate(commands):
        full_w = max(1, len(cmd)) * PROMPT_CHAR_W
        text_svg.append(
            f'\n      <text x="{x}" y="{y}" class="promptcmd pc{i}" clip-path="url(#promptClip{i})" '
            f'textLength="{full_w:.1f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{xml_escape(cmd)}</text>'
        )

    clip_anim_css = "\n".join(
        f".promptClipRect{i} {{ animation: promptClip{i} {total:.3f}s infinite; }}"
        for i in range(len(commands))
    )

    cursor_body = " ".join(
        f"{p}% {{ transform: translateX({w:.1f}px); animation-timing-function: {tf}; }}"
        for p, w, tf in cursor_stops
    )
    cursor_css = (
        f"@keyframes promptCursorMove {{ {cursor_body} }}\n      "
        f".promptcursor {{ animation: promptCursorMove {total:.3f}s infinite, blink 1s steps(1) infinite; }}"
    )

    cursor_svg = f'<rect x="{x:.1f}" y="{y-14:.1f}" width="8" height="16" class="promptcursor" />'

    style = "\n      ".join(keyframes_css) + "\n      " + clip_anim_css + "\n      " + cursor_css
    defs = "".join(groups_svg)
    return style, defs, "".join(text_svg), cursor_svg, max_w


def fetch_github_stats(login, token):
    stats = {
        "repos": "N/A", "stars": "N/A", "followers": "N/A",
        "contributions": "N/A", "top_languages": "N/A",
    }
    if not token:
        return stats
    try:
        import requests
        from datetime import datetime, timezone

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

        user_resp = requests.get(f"https://api.github.com/users/{login}", headers=headers, timeout=15)
        user_resp.raise_for_status()
        user = user_resp.json()
        stats["followers"] = str(user.get("followers", "N/A"))
        stats["repos"] = str(user.get("public_repos", "N/A"))

        repos = []
        repos_url = f"https://api.github.com/users/{login}/repos?per_page=100&type=owner"
        seen_repo_urls = set()
        while repos_url:
            if repos_url in seen_repo_urls:
                raise ValueError("GitHub repository pagination returned a repeated URL")
            seen_repo_urls.add(repos_url)
            repos_resp = requests.get(repos_url, headers=headers, timeout=15)
            repos_resp.raise_for_status()
            page_repos = repos_resp.json()
            if not isinstance(page_repos, list):
                raise ValueError("GitHub repository response was not a list")
            repos.extend(page_repos)
            repos_url = repos_resp.links.get("next", {}).get("url")

        stats["stars"] = str(sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork")))

        lang_count = {}
        for r in repos:
            lang = r.get("language")
            if lang:
                lang_count[lang] = lang_count.get(lang, 0) + 1
        top_langs = sorted(lang_count, key=lang_count.get, reverse=True)[:4]
        stats["top_languages"] = ", ".join(top_langs) if top_langs else "N/A"

        # GitHub contributions for the current year via GraphQL API.
        current_year = datetime.now(timezone.utc).year
        from_date = f"{current_year}-01-01T00:00:00Z"
        to_date = f"{current_year}-12-31T23:59:59Z"

        graphql_query = """
        query($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                totalContributions
              }
            }
          }
        }
        """

        graphql_resp = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={
                "query": graphql_query,
                "variables": {
                    "login": login,
                    "from": from_date,
                    "to": to_date,
                },
            },
            timeout=15,
        )
        graphql_resp.raise_for_status()
        graphql_data = graphql_resp.json()

        if graphql_data.get("errors"):
            print(
                f"warning: failed to fetch GitHub contributions: {graphql_data['errors']}",
                file=sys.stderr,
            )
        else:
            user_data = graphql_data.get("data", {}).get("user")
            if user_data:
                contributions = user_data.get(
                    "contributionsCollection", {}
                ).get(
                    "contributionCalendar", {}
                ).get(
                    "totalContributions"
                )

                if contributions is not None:
                    stats["contributions"] = str(contributions)

    except Exception as e:
        print(f"warning: failed to fetch live stats: {e}", file=sys.stderr)
    return stats

def build_svg(art_rows, fields):
    PAD = 34
    ART_W = ART_COLS * CELL_W
    ART_H = len(art_rows) * CELL_H
    GAP = 46
    FIELD_LINE_H = 22
    HEADER_H = 26
    RULE_GAP = 10
    SWATCH = 20
    SWATCH_GAP = 8
    PROMPT_H = 62

    info_x = PAD + ART_W + GAP
    header_y = TITLEBAR_H + PAD + HEADER_H
    rule_y = header_y + RULE_GAP
    fields_start_y = rule_y + 30

    fields_h = len(fields) * FIELD_LINE_H
    swatch_y = fields_start_y + fields_h + 14
    info_bottom = swatch_y + SWATCH + 10

    ART_OFFSET_Y = -12
  
    art_top = fields_start_y +  ART_OFFSET_Y
    art_bottom = art_top + ART_H
    content_bottom = max(info_bottom, art_bottom)

    prompt_y = content_bottom + 40
    H = prompt_y + PROMPT_H + 20
    header_text = f"{LOGIN}@github"
    rule_len = len(header_text) + 2
    label_cols = max((len(k) for k, _ in fields), default=0) + 2
    longest_field = max((label_cols + len(v) for _, v in fields), default=0)
    W = info_x + max(360, longest_field * 8.6) + PAD

    art_lines = []
    for i, row in enumerate(art_rows):
        y = art_top + i * CELL_H + CELL_H * 0.8
        delay = round(i * 0.045, 3)
        art_lines.append(
            f'\n      <text x="{PAD}" y="{y:.1f}" class="art fadein" '
            f'style="animation-delay:{delay}s" textLength="{ART_W:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve">{xml_escape(row)}</text>'
        )
    art_svg = "".join(art_lines)

    header_svg = (
        f'<text x="{info_x}" y="{header_y}" class="header" textLength="{len(header_text) * 12:.1f}" lengthAdjust="spacing">{xml_escape(header_text)}</text>'
        f'\n  <line x1="{info_x}" y1="{rule_y}" x2="{info_x + len(header_text) * 12:.1f}" y2="{rule_y}" class="rule" />'
    )

    field_lines = []
    label_w = max((len(k) for k, _ in fields), default=0) + 2
    for i, (label, value) in enumerate(fields):
        y = fields_start_y + i * FIELD_LINE_H
        delay = 0.5 + i * 0.06
        field_lines.append(
            f'\n      <text x="{info_x}" y="{y}" class="fieldline typewriter" style="animation-delay:{delay:.2f}s" xml:space="preserve">'
            f'<tspan class="label">{xml_escape((label + ":").ljust(label_w))}</tspan>'
            f'<tspan class="value">{xml_escape(value)}</tspan></text>'
        )
    fields_svg = "".join(field_lines)

    swatch_lines = []
    for i, color in enumerate(PALETTE):
        x = info_x + i * (SWATCH + SWATCH_GAP)
        delay = 0.5 + len(fields) * 0.06 + i * 0.05
        swatch_lines.append(
            f'\n      <rect x="{x:.1f}" y="{swatch_y:.1f}" width="{SWATCH}" height="{SWATCH}" rx="3" '
            f'fill="{color}" stroke="#2a3350" stroke-width="1" class="swatch" style="animation-delay:{delay:.2f}s" />'
        )
    swatch_svg = "".join(swatch_lines)

    prompt_line1 = f"┌──({LOGIN}@github-[~]"
    prompt_line2 = "└─$ "

    typed_x = PAD + (len(prompt_line2) + 1) * 9.0
    typed_y = prompt_y + 24
    prompt_style, prompt_defs, prompt_cmd_svg, prompt_cursor_svg, cmd_max_w = build_prompt_typing_svg(
        PROMPT_COMMANDS, typed_x, typed_y
    )

    prompt_svg = (
        f'<text x="{PAD}" y="{prompt_y}" class="prompt" textLength="{len(prompt_line1) * 9.0:.1f}" lengthAdjust="spacing">{xml_escape(prompt_line1)}</text>'
        f'\n  <text x="{PAD}" y="{typed_y}" class="prompt" textLength="{len(prompt_line2.rstrip()) * 9.0:.1f}" lengthAdjust="spacing">{xml_escape(prompt_line2.rstrip())}</text>'
        f'\n  {prompt_cmd_svg}'
        f'\n  {prompt_cursor_svg}'
    )

    W = max(W, typed_x + cmd_max_w + PAD)

    # --- window chrome (title bar + traffic-light dots + title label) -----
    title_text = f"{LOGIN}@github: ~"
    chrome_svg = f'''
  <rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" rx="10" fill="{BG_COLOR}" />
  <path d="M0,10 a10,10 0 0 1 10,-10 h{W-20:.0f} a10,10 0 0 1 10,10 v{TITLEBAR_H-10:.0f} h-{W:.0f} z"
        fill="{TITLEBAR_COLOR}" />
  <circle cx="24" cy="{TITLEBAR_H/2:.0f}" r="6" fill="#ff5f57" />
  <circle cx="46" cy="{TITLEBAR_H/2:.0f}" r="6" fill="#febc2e" />
  <circle cx="68" cy="{TITLEBAR_H/2:.0f}" r="6" fill="#28c840" />
  <text x="{W/2:.0f}" y="{TITLEBAR_H/2 + 5:.0f}" text-anchor="middle" class="titletext">{xml_escape(title_text)}</text>
  <line x1="0" y1="{TITLEBAR_H}" x2="{W:.0f}" y2="{TITLEBAR_H}" stroke="#1f2740" stroke-width="1" />'''

    return f'''<svg width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .art {{ font-family: 'SF Mono', 'JetBrains Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace; font-size: {CELL_H*0.82:.1f}px; fill: {ACCENT}; white-space: pre; }}
      .header {{ font-family: 'SF Mono', 'JetBrains Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace; font-size: 20px; font-weight: 700; letter-spacing: -0.01em; fill: {HEADER_COLOR}; }}
      .rule {{ stroke: {HEADER_COLOR}; stroke-width: 1.2; opacity: 0.5; }}
      .fieldline {{ font-family: 'SF Mono', 'JetBrains Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace; font-size: 13.5px; }}
      .label {{ fill: {LABEL_COLOR}; font-weight: 600; }}
      .value {{ fill: {VALUE_COLOR}; font-weight: 400; }}
      .prompt {{ font-family: 'SF Mono', 'JetBrains Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace; font-size: 15px; font-weight: 600; fill: {HEADER_COLOR}; }}
      .titletext {{ font-family: 'SF Mono', 'JetBrains Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace; font-size: 12px; letter-spacing: 0.04em; fill: {TITLE_TEXT_COLOR}; }}
      .promptcmd {{ font-family: 'SF Mono', 'JetBrains Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace; font-size: 15px; fill: {VALUE_COLOR}; white-space: pre; }}
      .promptcursor {{ fill: {ACCENT}; }}
      {prompt_style}
      .fadein {{ animation-name: reveal; animation-duration: 0.35s; animation-fill-mode: forwards; animation-timing-function: steps(1); }}
      .typewriter {{ animation-name: reveal; animation-duration: 0.4s; animation-fill-mode: forwards; animation-timing-function: steps(1); }}
      .swatch {{ animation-name: revealSwatch; animation-duration: 0.35s; animation-fill-mode: forwards; animation-timing-function: steps(1); }}
      @keyframes reveal {{ 0% {{ opacity: 0; }} 1%, 100% {{ opacity: 1; }} }}
      @keyframes revealSwatch {{ 0% {{ opacity: 0; }} 1%, 100% {{ opacity: 1; }} }}
      @media (prefers-reduced-motion: reduce) {{
        * {{ animation: none !important; }}
        .promptcmd:not(.pc0), .promptcursor {{ display: none; }}
      }}
      @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
    </style>
    {prompt_defs}
  </defs>
  {chrome_svg}

  {art_svg}

  {header_svg}
  {fields_svg}
  {swatch_svg}

  {prompt_svg}
</svg>
'''


CAL_PATH = os.environ.get("CAL_PATH", "assets/contributions.svg")
CAL_LEVELS = ["#16302a", "#1f5a27", "#3d8f45", "#7cc45a", "#a3d856"]  # Neuron forest to lime


def build_calendar_svg(login, token):
    """Contribution calendar for the last year, drawn in Neuron colors. None without a token."""
    if not token:
        return None
    import requests
    q = """query($login: String!) { user(login: $login) { contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { contributionLevel date } } } } } }"""
    r = requests.post("https://api.github.com/graphql", headers={"Authorization": f"Bearer {token}"},
                      json={"query": q, "variables": {"login": login}}, timeout=15)
    r.raise_for_status()
    cal = r.json()["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    lvl = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    cell, gap, left, top = 11, 3, 8, 30
    weeks = cal["weeks"]
    W = left * 2 + len(weeks) * (cell + gap) - gap
    H = top + 7 * (cell + gap) + 6
    rects, months, last_month = [], [], None
    for wi, week in enumerate(weeks):
        x = left + wi * (cell + gap)
        first = week["contributionDays"][0]["date"]
        if first[5:7] != last_month and first[8:10] <= "07":
            last_month = first[5:7]
            name = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][int(last_month) - 1]
            months.append(f'<text x="{x}" y="{top - 9}" class="m">{name}</text>')
        for day in week["contributionDays"]:
            from datetime import date
            y = top + date.fromisoformat(day["date"]).isoweekday() % 7 * (cell + gap)
            rects.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{CAL_LEVELS[lvl[day["contributionLevel"]]]}"/>')
    total = cal["totalContributions"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H + 22}" viewBox="0 0 {W} {H + 22}">'
            f"<style>text{{font-family:{MONO_STACK};fill:#8fb3a3}} .m{{font-size:10px;letter-spacing:.02em}} "
            f".t{{font-size:11px;fill:#a3d856;font-weight:600}}</style>"
            f'<rect width="100%" height="100%" rx="10" fill="#0d211b"/>'
            + "".join(months) + "".join(rects)
            + f'<text x="{left}" y="{H + 12}" class="t">{total:,} contributions in the last year</text></svg>')


def main():
    avatar_path = find_avatar()
    if avatar_path:
        print(f"using avatar image: {avatar_path}")
        art_rows = ascii_rows_from_image(avatar_path)
    else:
        print("no avatar found, using procedural Kali-dragon placeholder art")
        art_rows = ascii_rows_dragon()

    stats = fetch_github_stats(LOGIN, TOKEN)

    fields = list(PROFILE_FIELDS)
    fields.extend([
        ("Repos", stats["repos"]),
        ("Stars", stats["stars"]),
        ("Followers", stats["followers"]),
        ("Languages", stats["top_languages"]),
        ("Contributions", stats["contributions"])
    ])

    svg = build_svg(art_rows, fields)
    os.makedirs(os.path.dirname(OUT_PATH) or ".", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH}")

    cal = build_calendar_svg(LOGIN, TOKEN)
    if cal:
        with open(CAL_PATH, "w", encoding="utf-8") as f:
            f.write(cal)
        print(f"wrote {CAL_PATH}")


if __name__ == "__main__":
    main()
