#!/usr/bin/env python3
"""Render outlined Legends Font SVG design cards (Slots 1-7, rev r2) for the cto-legends README."""
import argparse
from pathlib import Path
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True


def _find_typeset_root() -> Path:
    candidates = []
    if os.environ.get("AVALON_TYPESET_ROOT"):
        candidates.append(Path(os.environ["AVALON_TYPESET_ROOT"]))
    parent_root = Path(__file__).resolve().parents[2]
    candidates.extend([
        parent_root / "avalonreset",
        parent_root / "cto-legends-glowup" / "repos" / "avalonreset",
    ])
    for cand in candidates:
        if (cand / "typeset.py").is_file():
            return cand
    raise SystemExit("FAIL: typeset.py not found; set AVALON_TYPESET_ROOT to the avalonreset directory.")


AVALON_ROOT = _find_typeset_root()
sys.path.insert(0, str(AVALON_ROOT))
from typeset import CAP, EM, FONT, Typesetter, width  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REV = "r2"
CARDS_DIR = ROOT / "assets" / "cards" / REV
README_PATH = ROOT / "README.md"

TYPE = {"head": 14, "title": 12, "body": 11, "label": 9}
K_CARD = 829 * 0.3333 / 303  # px per SVG unit, 3-across tiles
K_WIDE = 829 / 886           # px per SVG unit, full-width panels

COL_W = 303
COL_MIN_X = (0, (292 - COL_W) / 2, 292 - COL_W)
COL_PCT = 33.33

BORDER = 'stroke="#ffffff" stroke-opacity="0.09" stroke-width="1"'
HAIR = 'stroke="#ffffff" stroke-opacity="0.07" stroke-width="1"'
CHIP = 'fill="#090a0e" stroke="#ffffff" stroke-opacity="0.15" stroke-width="1"'
RED = 'stroke="#ff0000" stroke-opacity="0.68" stroke-width="1"'
RED_HAIR = 'stroke="#ff0000" stroke-opacity="0.30" stroke-width="1"'


def u(role: str, k: float) -> float:
    return round(TYPE[role] / k, 2)


def svg(vb: str, body: str, t: Typesetter = None) -> str:
    defs = t.defs() if t else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="100%">\n{defs}{body}</svg>\n'


def panel_defs(height: float) -> str:
    return (
        "  <defs>\n"
        f'    <linearGradient id="sheen" x1="0" y1="1" x2="0" y2="{height:.1f}" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#ffffff" stop-opacity="0.05"/>'
        '<stop offset="0.55" stop-color="#ffffff" stop-opacity="0"/></linearGradient>\n'
        f'    <linearGradient id="edge" x1="0" y1="1" x2="0" y2="{height:.1f}" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#ffffff" stop-opacity="0.22"/>'
        '<stop offset="1" stop-color="#ffffff" stop-opacity="0.09"/></linearGradient>\n'
        "  </defs>\n"
    )


def button(t: Typesetter, cx: float, y: float, fill: str, label: str, size: float, weight: str = "600") -> str:
    plain = re.sub(r"<[^>]+>|&\w+;", "", label)
    spacing = size * 0.1 if plain.isupper() else 0.0
    return t.run(cx, y, size, label, fill, weight, "middle", spacing)


def render_slot_1() -> None:
    """Slot 1: Compact agent handoff bar placed immediately above the copy-paste prompt fence."""
    t = Typesetter()
    ti, bd = u("title", K_WIDE), u("body", K_WIDE)
    h = 38
    body = (
        panel_defs(h)
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#000000"/>\n'
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="url(#sheen)" stroke="url(#edge)" stroke-width="1"/>\n'
        + f'  <rect x="1" y="1" width="4" height="{h - 2}" rx="2" fill="#ff0000"/>\n'
    )
    y_text = 23.5
    x_prompt = 18
    body += t.run(x_prompt, y_text, ti, "&gt;_", "#ff0000", "700")
    x_title = x_prompt + width("&gt;_", ti) + 8
    body += t.run(x_title, y_text, ti, "agent handoff", "#ffffff", "700")
    x_note = x_title + width("agent handoff", ti) + 12
    note = "// paste this into claude code, codex or any coding agent and it does the setup"
    body += t.run(x_note, y_text, bd, note, "#a1a1aa", "400")
    (CARDS_DIR / "slot-1-agent-handoff.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


def render_slot_2() -> None:
    """Slot 2: 3-column overview panel ('The human is the controller. The agents do the operating.')."""
    t = Typesetter()
    hd, ti, bd, lb = u("head", K_WIDE), u("title", K_WIDE), u("body", K_WIDE), u("label", K_WIDE)
    h = 204
    x0, x1 = 20, 866
    body = (
        panel_defs(h)
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#000000"/>\n'
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="url(#sheen)" stroke="url(#edge)" stroke-width="1"/>\n'
        + f'  <rect x="1" y="1" width="4" height="{h - 2}" rx="2" fill="#ff0000"/>\n'
    )
    # Top header bar
    y_head = 26
    body += t.run(x0, y_head, ti, "&gt;_", "#ff0000", "700")
    x_title = x0 + width("&gt;_", ti) + 8
    body += t.run(x_title, y_head, hd, "The human is the controller. The agents do the operating.", "#ffffff", "700")
    body += t.run(x1, y_head, lb, "// 1 skill · 21 curated tools", "#a1a1aa", "400", "end")
    body += f'  <line x1="{x0}" y1="40" x2="{x1}" y2="40" {HAIR}/>\n'

    # Three equal columns separated by vertical hairlines
    pillars = [
        (
            "01",
            "Talk like a human",
            [
                "Say the job in plain english.",
                "No module names or CLI flags",
                "to memorize.",
            ],
        ),
        (
            "02",
            "21 curated tools",
            [
                "One opinionated best-in-class",
                "stack where every tool already",
                "knows the others.",
            ],
        ),
        (
            "03",
            "Look, then do",
            [
                "Your agent shows you the plan",
                "before anything installs or",
                "changes on your machine.",
            ],
        ),
    ]
    gap = 28
    col_w = (x1 - x0 - 2 * gap) / 3
    y_col_head = 67
    for i, (num, title, lines) in enumerate(pillars):
        cx = x0 + i * (col_w + gap)
        body += t.run(cx, y_col_head, lb, num, "#ff0000", "700")
        body += t.run(cx + width(num, lb) + 9, y_col_head, ti, title, "#ffffff", "700")
        for j, ln in enumerate(lines):
            body += t.run(cx, y_col_head + 22 + 18 * j, bd, ln, "#a1a1aa", "400")
        if i > 0:
            vx = cx - gap / 2
            body += f'  <line x1="{vx:.2f}" y1="52" x2="{vx:.2f}" y2="136" {HAIR}/>\n'

    # Bottom bar with 9 host preset chips
    body += f'  <line x1="{x0}" y1="148" x2="{x1}" y2="148" {HAIR}/>\n'
    chip_top = 165
    base = chip_top + 13.5
    lab = "9 host presets:"
    body += t.run(x0, base, lb, lab, "#a1a1aa", "600")
    cx = x0 + width(lab, lb) + 10
    presets = ("claude", "codex", "gemini", "grok", "muse", "deepseek", "qwen", "glm", "opencode")
    for preset in presets:
        cw = width(preset, lb) + 16
        body += f'  <rect x="{cx:.2f}" y="{chip_top}" width="{cw:.2f}" height="20" rx="3" {CHIP}/>\n'
        body += t.run(cx + cw / 2, base, lb, preset, "#e4e4e7", "600", "middle")
        cx += cw + 6
    body += t.run(x1, base, lb, "zero context bloat", "#ff0000", "600", "end")

    (CARDS_DIR / "slot-2-three-pillars.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


def render_slot_3() -> None:
    """Slot 3: 4-row visual chain map ('Say the job in plain words')."""
    t = Typesetter()
    hd, ti, bd, lb = u("head", K_WIDE), u("title", K_WIDE), u("body", K_WIDE), u("label", K_WIDE)
    h = 208
    x0, x1 = 20, 866
    body = (
        panel_defs(h)
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#000000"/>\n'
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="url(#sheen)" stroke="url(#edge)" stroke-width="1"/>\n'
        + f'  <rect x="1" y="1" width="4" height="{h - 2}" rx="2" fill="#ff0000"/>\n'
    )
    body += t.run(x0, 26, hd, "Say the job in plain words", "#ffffff", "700")
    body += t.run(
        x0 + width("Say the job in plain words", hd) + 12,
        26,
        lb,
        "// your agent chains the curated stack behind the scenes",
        "#ff0000",
        "600",
    )
    body += f'  <line x1="{x0}" y1="38" x2="{x1}" y2="38" {HAIR}/>\n'

    rows = [
        (
            "01",
            '"Study my business on Google Maps"',
            'legends-geogrid <tspan fill="#ff0000">→</tspan> legends-dataforseo <tspan fill="#ff0000">→</tspan> legends-jev',
        ),
        (
            "02",
            '"Convert my WordPress site to Astro v7"',
            'legends-firecrawl <tspan fill="#ff0000">→</tspan> legends-astro <tspan fill="#ff0000">→</tspan> <tspan fill="#d4d4d8">stripe · hetzner · coolify · cloudflare</tspan>',
        ),
        (
            "03",
            '"Save this research in my vault"',
            'legends-dataforseo · legends-firecrawl <tspan fill="#ff0000">→</tspan> legends-empire',
        ),
        (
            "04",
            '"Record and caption a YouTube tutorial"',
            'legends-obs <tspan fill="#ff0000">→</tspan> legends-captions <tspan fill="#ff0000">→</tspan> legends-stable-audio-3 <tspan fill="#ff0000">→</tspan> legends-youtube',
        ),
    ]

    pill_x = 362
    pill_w = x1 - pill_x
    for i, (num, prompt_txt, chain_markup) in enumerate(rows):
        ry = 64 + i * 42
        if i > 0:
            div_y = ry - 25
            body += f'  <line x1="{x0}" y1="{div_y}" x2="{x1}" y2="{div_y}" {HAIR}/>\n'
        body += t.run(x0, ry, lb, num, "#ff0000", "700")
        body += t.run(x0 + width(num, lb) + 10, ry, bd, prompt_txt, "#ffffff", "700")
        body += t.run(pill_x - 16, ry, ti, "→", "#ff0000", "700", "middle")
        body += f'  <rect x="{pill_x}" y="{ry - 16.5:.1f}" width="{pill_w}" height="24" rx="3" fill="#090a0e" {RED_HAIR}/>\n'
        body += t.run(pill_x + 12, ry - 0.5, lb, chain_markup, "#ffffff", "600")

    (CARDS_DIR / "slot-3-plain-english-chains.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


def render_slot_4() -> None:
    """Slot 4: Comparison table ('A shelf of skills' vs 'One router // cto-legends', four rows)."""
    t = Typesetter()
    ti, bd, lb = u("title", K_WIDE), u("body", K_WIDE), u("label", K_WIDE)
    rows = [
        ("What is registered", "One folder per skill you added", "One skill, cto-legends"),
        ("When a recipe is read", "Decided by your host", "When the task calls for it, via cto-legends handoff MODULE"),
        ("How a release is pinned", "Whatever copy is in the folder", "By version, commit and SHA-256 in the catalog"),
        ("How it is rolled back", "Whatever backup you kept", "Via cto-legends rollback MODULE --apply; prior env kept"),
    ]
    h = 198
    col0_x, col1_x, col2_x = 20, 212, 504
    body = (
        panel_defs(h)
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#000000"/>\n'
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="url(#sheen)" stroke="url(#edge)" stroke-width="1"/>\n'
        + f'  <rect x="{col2_x - 12}" y="7" width="{880 - (col2_x - 12)}" height="{h - 14}" rx="3" fill="#0c0507" {RED_HAIR}/>\n'
    )
    y_hdr = 27
    body += t.run(col0_x, y_hdr, lb, "comparison", "#8b8b94", "600")
    body += t.run(col1_x, y_hdr, ti, "A shelf of skills", "#a1a1aa", "700")
    body += t.run(col2_x, y_hdr, ti, "One router", "#ffffff", "700")
    body += t.run(col2_x + width("One router", ti) + 10, y_hdr, lb, "// cto-legends", "#ff0000", "600")
    body += f'  <line x1="16" y1="39" x2="870" y2="39" {HAIR}/>\n'
    body += f'  <line x1="{col1_x - 12}" y1="12" x2="{col1_x - 12}" y2="{h - 12}" {HAIR}/>\n'

    for i, (label_txt, shelf_txt, router_txt) in enumerate(rows):
        ry = 64 + i * 38
        if i > 0:
            div_y = ry - 21
            body += f'  <line x1="16" y1="{div_y}" x2="870" y2="{div_y}" {HAIR}/>\n'
        body += t.run(col0_x, ry, lb, label_txt, "#e4e4e7", "600")
        body += t.run(col1_x, ry, lb, shelf_txt, "#a1a1aa", "400")
        body += t.run(col2_x, ry, lb, router_txt, "#ffffff", "600")

    (CARDS_DIR / "slot-4-shelf-vs-router.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


def render_slot_5() -> None:
    """Slot 5: Three tiles ('Claude', 'Codex', 'Every preset') in 3-across grid."""
    tiles = [
        (
            "slot-5-claude",
            "01",
            "Claude",
            "preset: claude",
            "Writes ~/.claude/skills/cto-legends",
            "No MCP server required",
            "CLAUDE PRESET →",
        ),
        (
            "slot-5-codex",
            "02",
            "Codex",
            "preset: codex",
            "Writes ~/.codex/skills and",
            "shared ~/.agents/skills root",
            "CODEX PRESET →",
        ),
        (
            "slot-5-every-preset",
            "03",
            "Every preset",
            "9 host presets",
            "claude, codex, gemini, grok, muse,",
            "deepseek, qwen, glm, opencode",
            "ALL 9 PRESETS →",
        ),
    ]
    ti, bd, lb = u("title", K_CARD), u("body", K_CARD), u("label", K_CARD)
    body_h = 104
    foot_h = 28
    total_h = body_h + foot_h
    for col, (fname, num, title, meta, line1, line2, cta) in enumerate(tiles):
        m = COL_MIN_X[col]
        t = Typesetter()
        edge = f"M1 {body_h} V6.5 A4 4 0 0 1 5 2.5 H287 A4 4 0 0 1 291 6.5 V{body_h}"
        b = total_h - 0.5
        body = (
            "  <defs>\n"
            '    <linearGradient id="sheen" x1="0" y1="2.5" x2="0" y2="100" gradientUnits="userSpaceOnUse">'
            '<stop offset="0" stop-color="#ffffff" stop-opacity="0.05"/><stop offset="0.6" stop-color="#ffffff" stop-opacity="0"/></linearGradient>\n'
            '    <linearGradient id="edge" x1="0" y1="2.5" x2="0" y2="100" gradientUnits="userSpaceOnUse">'
            '<stop offset="0" stop-color="#ffffff" stop-opacity="0.22"/><stop offset="1" stop-color="#ffffff" stop-opacity="0.09"/></linearGradient>\n'
            "  </defs>\n"
            f'  <rect x="1" y="2.5" width="290" height="{total_h - 3}" rx="4" fill="#000000"/>\n'
            f'  <path d="{edge} Z" fill="url(#sheen)"/>\n'
            f'  <path d="{edge}" fill="none" stroke="url(#edge)" stroke-width="1"/>\n'
            f'  <path d="M1 {body_h} V{b - 4} A4 4 0 0 0 5 {b} H287 A4 4 0 0 0 291 {b - 4} V{body_h} Z" fill="#0c0507"/>\n'
            f'  <path d="M1 {body_h} V{b - 4} A4 4 0 0 0 5 {b} H287 A4 4 0 0 0 291 {b - 4} V{body_h}" fill="none" {RED}/>\n'
            f'  <line x1="1" y1="{body_h + 0.5}" x2="291" y2="{body_h + 0.5}" {RED_HAIR}/>\n'
        )
        body += t.run(14, 25, lb, num, "#ff0000", "700")
        body += t.run(14 + width(num, lb) + 8, 25, ti, title, "#ffffff", "700")
        body += t.run(14, 42, lb, meta, "#a1a1aa", "600")
        body += t.run(14, 64, bd, line1, "#e4e4e7", "400")
        body += t.run(14, 82, bd, line2, "#a1a1aa", "400")
        body += button(t, 146, body_h + 18, "#ffffff", f'{cta[:-2]} <tspan fill="#ff0000">→</tspan>', lb, "700")
        (CARDS_DIR / f"{fname}.svg").write_text(svg(f"{m:g} 0 {COL_W} {total_h}", body, t), encoding="utf-8")


def render_slot_6() -> None:
    """Slot 6: Four module group header cards linking to each group anchor."""
    groups = [
        (
            "slot-6-local-search-and-research",
            "01",
            "Local search and research",
            "6 modules · geogrid · dataforseo · jev · firecrawl · github · grant",
        ),
        (
            "slot-6-web-stack",
            "02",
            "Web stack",
            "7 modules · hetzner · coolify · cloudflare · astro · stripe · gohighlevel · buzz",
        ),
        (
            "slot-6-recording-audio-and-video",
            "03",
            "Recording, audio and video",
            "7 modules · obs · captions · youtube · yt-dlp · stable-audio-3 · hyperyap · ambient-intelligence",
        ),
        (
            "slot-6-memory",
            "04",
            "Memory",
            "1 module · legends-empire · source-cited vault memory, search and stewardship",
        ),
    ]
    hd, lb = u("head", K_WIDE), u("label", K_WIDE)
    h = 44
    for fname, num, title, meta in groups:
        t = Typesetter()
        body = (
            panel_defs(h)
            + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#000000"/>\n'
            + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="url(#sheen)" stroke="url(#edge)" stroke-width="1"/>\n'
            + f'  <rect x="1" y="1" width="4" height="{h - 2}" rx="2" fill="#ff0000"/>\n'
        )
        y_text = 27
        body += t.run(18, y_text, lb, num, "#ff0000", "700")
        x_t = 18 + width(num, lb) + 10
        body += t.run(x_t, y_text, hd, title, "#ffffff", "700")
        body += t.run(868, y_text, lb, meta, "#a1a1aa", "400", "end")
        (CARDS_DIR / f"{fname}.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


def render_slot_7() -> None:
    """Slot 7: Closing message desk CTA card ('Message Avalon Reset')."""
    t = Typesetter()
    ti, bd, lb = u("title", K_WIDE), u("body", K_WIDE), u("label", K_WIDE)
    h = 68
    body = (
        f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#0c0507" {RED}/>\n'
        f'  <rect x="1" y="1" width="4" height="{h - 2}" rx="2" fill="#ff0000"/>\n'
    )
    body += t.run(22, 28, ti, "Want this way of working applied to your own stack?", "#ffffff", "700")
    body += t.run(22, 48, bd, "Message Avalon Reset", "#ff0000", "700")
    x_note = 22 + width("Message Avalon Reset", bd) + 10
    body += t.run(x_note, 48, lb, "// async message desk at cto-legends.com/dm", "#a1a1aa", "400")

    btn_w = 228
    btn_x = 868 - btn_w
    body += f'  <rect x="{btn_x}" y="18" width="{btn_w}" height="32" rx="3" fill="#000000" {RED}/>\n'
    body += button(t, btn_x + btn_w / 2, 38.5, "#ffffff", 'MESSAGE AVALON RESET <tspan fill="#ff0000">↗</tspan>', lb, "700")

    (CARDS_DIR / "slot-7-message-avalon-reset.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


def validate() -> None:
    expected = [
        "slot-1-agent-handoff.svg",
        "slot-2-three-pillars.svg",
        "slot-3-plain-english-chains.svg",
        "slot-4-shelf-vs-router.svg",
        "slot-5-claude.svg",
        "slot-5-codex.svg",
        "slot-5-every-preset.svg",
        "slot-6-local-search-and-research.svg",
        "slot-6-memory.svg",
        "slot-6-recording-audio-and-video.svg",
        "slot-6-web-stack.svg",
        "slot-7-message-avalon-reset.svg",
    ]
    svgs = sorted(CARDS_DIR.glob("*.svg"))
    names = [p.name for p in svgs]
    assert names == expected, f"Expected {len(expected)} SVGs {expected}, found {names}"
    allowed_hex = {
        "#000000", "#ffffff", "#ff0000",
        "#e4e4e7", "#d4d4d8", "#a1a1aa", "#8b8b94", "#52525b",
        "#090a0e", "#0c0507",
    }
    for p in svgs:
        raw = p.read_bytes().replace(b"\r\n", b"\n")
        p.write_bytes(raw)
        s = raw.decode("utf-8")
        assert "\u2014" not in s and "\u2013" not in s, f"Dash found in {p.name}"
        assert "<text" not in s, f"Live <text> element found in {p.name}; all text must be outlined"
        ET.fromstring(s)
        colors = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}", s)}
        unexpected = colors - allowed_hex
        assert not unexpected, f"Unexpected color in {p.name}: {unexpected}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Render outlined Legends Font SVG cards (rev r2).")
    ap.parse_args()
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    render_slot_1()
    render_slot_2()
    render_slot_3()
    render_slot_4()
    render_slot_5()
    render_slot_6()
    render_slot_7()
    validate()
    print(f"Rendered and validated 12 SVG cards in {CARDS_DIR.relative_to(ROOT)} (font={FONT}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
