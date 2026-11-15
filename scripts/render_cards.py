#!/usr/bin/env python3
"""Render outlined Legends Font SVG design cards (Slots 2-7) for the cto-legends README."""
from pathlib import Path
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
AVALON_ROOT = Path(os.environ.get("AVALON_TYPESET_ROOT", Path(__file__).resolve().parents[2] / "avalonreset"))
sys.path.insert(0, str(AVALON_ROOT))
from typeset import CAP, EM, FONT, Typesetter, width  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REV = "r1"
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


def render_slot_2() -> None:
    """Slot 2: Above the install block ('Look, then do' with 2 columns)."""
    t = Typesetter()
    hd, ti, bd, lb = u("head", K_WIDE), u("title", K_WIDE), u("body", K_WIDE), u("label", K_WIDE)
    h = 92
    body = (
        panel_defs(h)
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#000000"/>\n'
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="url(#sheen)" stroke="url(#edge)" stroke-width="1"/>\n'
        + f'  <rect x="1" y="1" width="4" height="{h - 2}" rx="2" fill="#ff0000"/>\n'
    )
    # Header row
    y_head = 25
    body += t.run(20, y_head, ti, "&gt;_", "#ff0000", "700")
    x_title = 20 + width("&gt;_", ti) + 8
    body += t.run(x_title, y_head, hd, "Look, then do", "#ffffff", "700")
    x_sub = x_title + width("Look, then do", hd) + 14
    body += t.run(x_sub, y_head, lb, "// preview plan first, mutate only on explicit flag", "#a1a1aa", "400")
    body += f'  <line x1="20" y1="37" x2="866" y2="37" {HAIR}/>\n'

    # Two columns: "no flag: prints the plan" and "--apply: makes the change"
    body += f'  <line x1="443" y1="44" x2="443" y2="{h - 10}" {HAIR}/>\n'

    # Left column
    c1_x = 20
    body += t.run(c1_x, 61, lb, "01", "#ff0000", "700")
    chip1_x = c1_x + width("01", lb) + 10
    chip1_w = width("no flag", lb) + 18
    body += f'  <rect x="{chip1_x:.2f}" y="47.5" width="{chip1_w:.2f}" height="19" rx="3" {CHIP}/>\n'
    body += t.run(chip1_x + chip1_w / 2, 60.5, lb, "no flag", "#e4e4e7", "600", "middle")
    txt1_x = chip1_x + chip1_w + 12
    body += t.run(txt1_x, 61, ti, "no flag: prints the plan", "#ffffff", "700")
    body += t.run(txt1_x, 78, bd, "returns the JSON preview and changes nothing", "#a1a1aa", "400")

    # Right column
    c2_x = 462
    body += t.run(c2_x, 61, lb, "02", "#ff0000", "700")
    chip2_x = c2_x + width("02", lb) + 10
    chip2_w = width("--apply", lb) + 18
    body += f'  <rect x="{chip2_x:.2f}" y="47.5" width="{chip2_w:.2f}" height="19" rx="3" fill="#0c0507" {RED}/>\n'
    body += t.run(chip2_x + chip2_w / 2, 60.5, lb, "--apply", "#ffffff", "700", "middle")
    txt2_x = chip2_x + chip2_w + 12
    body += t.run(txt2_x, 61, ti, "--apply: makes the change", "#ffffff", "700")
    body += t.run(txt2_x, 78, bd, "executes the reviewed plan on disk", "#d4d4d8", "400")

    (CARDS_DIR / "slot-2-look-then-do.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


def render_slot_3() -> None:
    """Slot 3: 'Why this exists' ('A shelf of skills' against 'One router', four rows)."""
    t = Typesetter()
    ti, bd, lb = u("title", K_WIDE), u("body", K_WIDE), u("label", K_WIDE)
    rows = [
        ("What is registered", "One folder per skill you added", "One skill, cto-legends"),
        ("When a recipe is read", "Decided by your host", "When the task calls for it, through cto-legends handoff MODULE"),
        ("How a release is pinned", "Whatever copy is in the folder", "By version, commit and SHA-256 in the catalog"),
        ("How it is rolled back", "Whatever backup you kept", "With cto-legends rollback MODULE; previous env retained"),
    ]
    h = 198
    col0_x, col1_x, col2_x = 20, 212, 504
    body = (
        panel_defs(h)
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#000000"/>\n'
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="url(#sheen)" stroke="url(#edge)" stroke-width="1"/>\n'
        + f'  <rect x="{col2_x - 12}" y="7" width="{880 - (col2_x - 12)}" height="{h - 14}" rx="3" fill="#0c0507" {RED_HAIR}/>\n'
    )
    # Column headers
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
        body += t.run(col1_x, ry, bd, shelf_txt, "#a1a1aa", "400")
        body += t.run(col2_x, ry, lb, router_txt, "#ffffff", "600")

    (CARDS_DIR / "slot-3-shelf-vs-router.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


def render_slot_4() -> None:
    """Slot 4: 'One job, start to finish' (Seven steps: route, look, do, handoff, doctor, readiness, run)."""
    t = Typesetter()
    hd, ti, lb = u("head", K_WIDE), u("title", K_WIDE), u("label", K_WIDE)
    steps = [
        ("01", "route", "rank goal"),
        ("02", "look", "preview plan"),
        ("03", "do", "--apply"),
        ("04", "handoff", "load recipe"),
        ("05", "doctor", "check env"),
        ("06", "readiness", "report check"),
        ("07", "run", "execute cli"),
    ]
    h = 112
    body = (
        panel_defs(h)
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="#000000"/>\n'
        + f'  <rect x="1" y="1" width="884" height="{h - 2}" rx="4" fill="url(#sheen)" stroke="url(#edge)" stroke-width="1"/>\n'
    )
    body += t.run(20, 25, hd, "One job, start to finish", "#ffffff", "700")
    body += t.run(20 + width("One job, start to finish", hd) + 12, 25, lb, "// seven steps from plain-English request to execution", "#ff0000", "600")
    body += f'  <line x1="20" y1="36" x2="866" y2="36" {HAIR}/>\n'

    margin_x = 16
    gap = 12
    tile_w = (886 - 2 * margin_x - 6 * gap) / 7  # ~111.7u each
    tile_y = 46
    tile_h = 54
    for i, (num, name, sub) in enumerate(steps):
        tx = margin_x + i * (tile_w + gap)
        is_apply = name in ("do", "run")
        fill = "#0c0507" if is_apply else "#090a0e"
        stroke = RED if is_apply else BORDER
        body += f'  <rect x="{tx:.2f}" y="{tile_y}" width="{tile_w:.2f}" height="{tile_h}" rx="3" fill="{fill}" {stroke}/>\n'
        body += t.run(tx + 10, tile_y + 18, lb, num, "#ff0000", "700")
        body += t.run(tx + 10 + width(num, lb) + 6, tile_y + 18, ti, name, "#ffffff", "700")
        body += t.run(tx + 10, tile_y + 39, lb, sub, "#a1a1aa", "400")
        if i < 6:
            ax = tx + tile_w + gap / 2
            body += t.run(ax, tile_y + 31, lb, "→", "#ff0000", "700", "middle")

    (CARDS_DIR / "slot-4-seven-steps.svg").write_text(svg(f"0 0 886 {h}", body, t), encoding="utf-8")


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
            "1 module · legends-empire · source-cited vault memory and stewardship",
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
    """Slot 7: 'Start here' ('Want this way of working applied to your own stack? Message Avalon Reset')."""
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


def wire_readme() -> None:
    """Embed Slots 2-7 SVG cards at their designated positions in README.md while keeping stand-in Markdown intact."""
    text = README_PATH.read_text(encoding="utf-8")

    # Slot 2: Above the install block
    slot2_html = (
        '<p align="left">\n'
        '  <img src="assets/cards/r1/slot-2-look-then-do.svg" width="100%" align="top" '
        'alt="Look, then do: no flag prints the plan; --apply makes the change" />\n'
        "</p>\n\n"
    )
    target2 = "```sh\npython -m pip install cto-legends\n"
    if "assets/cards/r1/slot-2-look-then-do.svg" not in text:
        assert target2 in text, "Slot 2 target not found"
        text = text.replace(target2, slot2_html + target2, 1)

    # Slot 3: Above the 'A shelf of skills' vs 'One router' table
    slot3_html = (
        '<p align="left">\n'
        '  <img src="assets/cards/r1/slot-3-shelf-vs-router.svg" width="100%" align="top" '
        'alt="A shelf of skills against One router: what is registered, when a recipe is read, how a release is pinned, and how it is rolled back" />\n'
        "</p>\n\n"
    )
    target3 = "| | A shelf of skills | One router |\n"
    if "assets/cards/r1/slot-3-shelf-vs-router.svg" not in text:
        assert target3 in text, "Slot 3 target not found"
        text = text.replace(target3, slot3_html + target3, 1)

    # Slot 4: Above the 7-step walkthrough code block in 'One job, start to finish'
    slot4_html = (
        '<p align="left">\n'
        '  <img src="assets/cards/r1/slot-4-seven-steps.svg" width="100%" align="top" '
        'alt="One job, start to finish in seven steps: route, look, do, handoff, doctor, readiness, run" />\n'
        "</p>\n\n"
    )
    target4 = '```sh\ncto-legends route "Google Maps ranking grids"'
    if "assets/cards/r1/slot-4-seven-steps.svg" not in text:
        assert target4 in text, "Slot 4 target not found"
        text = text.replace(target4, slot4_html + target4, 1)

    # Slot 5: Above '### Claude skills: the `claude` preset'
    slot5_html = (
        '<p align="left">\n'
        '  <a href="#claude-skills-the-claude-preset"><img src="assets/cards/r1/slot-5-claude.svg" width="33.33%" align="top" alt="Claude: the claude preset writes ~/.claude/skills/cto-legends" /></a><!--\n'
        '  --><a href="#codex-skills-the-codex-preset"><img src="assets/cards/r1/slot-5-codex.svg" width="33.33%" align="top" alt="Codex: the codex preset writes ~/.codex/skills and ~/.agents/skills" /></a><!--\n'
        '  --><a href="#agent-skills-paths-for-every-preset"><img src="assets/cards/r1/slot-5-every-preset.svg" width="33.33%" align="top" alt="Every preset: skill paths for all nine host presets" /></a>\n'
        "</p>\n\n"
    )
    target5 = "### Claude skills: the `claude` preset\n"
    if "assets/cards/r1/slot-5-claude.svg" not in text:
        assert target5 in text, "Slot 5 target not found"
        text = text.replace(target5, slot5_html + target5, 1)

    # Slot 6: Above each of the four module group H3 headings
    slot6_pairs = [
        (
            "### Local search and research\n",
            "slot-6-local-search-and-research.svg",
            "#local-search-and-research",
            "Local search and research: 6 modules (geogrid, dataforseo, jev, firecrawl, github, grant)",
        ),
        (
            "### Web stack\n",
            "slot-6-web-stack.svg",
            "#web-stack",
            "Web stack: 7 modules (hetzner, coolify, cloudflare, astro, stripe, gohighlevel, buzz)",
        ),
        (
            "### Recording, audio and video\n",
            "slot-6-recording-audio-and-video.svg",
            "#recording-audio-and-video",
            "Recording, audio and video: 7 modules (obs, captions, youtube, yt-dlp, stable-audio-3, hyperyap, ambient-intelligence)",
        ),
        (
            "### Memory\n",
            "slot-6-memory.svg",
            "#memory",
            "Memory: 1 module (legends-empire)",
        ),
    ]
    for heading, svg_name, href, alt_txt in slot6_pairs:
        if f"assets/cards/r1/{svg_name}" not in text:
            assert heading in text, f"Slot 6 heading not found: {heading}"
            card_html = (
                f"{heading}\n"
                '<p align="left">\n'
                f'  <a href="{href}"><img src="assets/cards/r1/{svg_name}" width="100%" align="top" alt="{alt_txt}" /></a>\n'
                "</p>\n"
            )
            text = text.replace(heading, card_html, 1)

    # Slot 7: Above the closing message desk line in 'Start here'
    slot7_html = (
        '<p align="left">\n'
        '  <a href="https://cto-legends.com/dm"><img src="assets/cards/r1/slot-7-message-avalon-reset.svg" width="100%" align="top" '
        'alt="Want this way of working applied to your own stack? Message Avalon Reset at cto-legends.com/dm" /></a>\n'
        "</p>\n\n"
    )
    target7 = "Want this way of working applied to your own stack? Message Avalon Reset at the [site message desk](https://cto-legends.com/dm)."
    if "assets/cards/r1/slot-7-message-avalon-reset.svg" not in text:
        assert target7 in text, "Slot 7 target not found"
        text = text.replace(target7, slot7_html + target7, 1)

    README_PATH.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def validate() -> None:
    svgs = sorted(CARDS_DIR.glob("*.svg"))
    assert len(svgs) == 11, f"Expected 11 SVGs in {CARDS_DIR}, found {len(svgs)}"
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
        ET.fromstring(s)
        colors = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}", s)}
        unexpected = colors - allowed_hex
        assert not unexpected, f"Unexpected color in {p.name}: {unexpected}"


def main() -> int:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    render_slot_2()
    render_slot_3()
    render_slot_4()
    render_slot_5()
    render_slot_6()
    render_slot_7()
    wire_readme()
    validate()
    print(f"Rendered and validated 10 SVG cards in {CARDS_DIR.relative_to(ROOT)} (font={FONT}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
