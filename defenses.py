"""DD's safety layers (Problem 6).

- Code layer:   visible_text() keeps only what a person would see on screen, before any model sees the document.
- Design layer: decide() applies the handbook's four purchasing checks in code, and ground() rejects any number
                that is not actually in the document text. (The trap tools are gated in agent.py.)
- Prompt layer: the "Safety rules" section of prompts/prompt.md (switched on/off in agent.build_instructions).
"""
import email
import re
from dataclasses import dataclass
from email import policy
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
HANDBOOK = HERE / "data" / "shop_handbook.md"


@dataclass(frozen=True)
class Defenses:
    code: bool = True
    design: bool = True
    prompt: bool = True

    @property
    def label(self) -> str:
        on = [n for n in ("code", "design", "prompt") if getattr(self, n)]
        return "+".join(on) if on else "none"


ALL = Defenses()
NONE = Defenses(code=False, design=False, prompt=False)


# =====================================================================
# Code layer: read the document the way a person sees it
# =====================================================================
ZERO_WIDTH = re.compile("[​-‏⁠﻿­]")
VOID_TAGS = {"br", "img", "hr", "meta", "link", "input", "col", "area", "base", "source", "wbr"}
SKIP_TAGS = {"script", "style", "template", "noscript", "head"}
BLOCK_TAGS = {"p", "tr", "h1", "h2", "h3", "h4", "li", "div", "header", "footer", "br", "table", "section"}
WHITE = re.compile(r"color\s*:\s*(#fff\b|#ffffff\b|white\b|rgba?\(\s*25[0-5]\s*,\s*25[0-5]\s*,\s*25[0-5])", re.I)
TINY_FONT = re.compile(r"font-size\s*:\s*(0*\.?\d*)\s*(px|pt|em|rem)?", re.I)


OFFSCREEN = re.compile(r"(?:left|top|right|text-indent|margin-left|margin-top):-(\d{3,})(?:px|pt)?")
ZERO_BOX = re.compile(r"(?:^|;)(?:max-height|height|max-width|width|line-height):0(?:px|pt|em|rem|%)?(?:;|$)")


def _hidden_style(attrs: dict, sheet_style: str = "") -> bool:
    """True if the element's inline style (plus any matching <style> sheet rules) hides it from a person."""
    raw = f"{sheet_style};{attrs.get('style') or ''}"
    style = raw.replace(" ", "").lower()
    if "hidden" in attrs or attrs.get("aria-hidden") == "true":
        return True
    if any(s in style for s in ("display:none", "visibility:hidden", "color:transparent", "transform:scale(0")):
        return True
    if re.search(r"opacity:0(?:\.0+)?(?:;|$)", style):
        return True
    if WHITE.search(raw):
        return True
    m = TINY_FONT.search(raw)
    if m and m.group(1):
        size, unit = float(m.group(1)), (m.group(2) or "px").lower()
        px = size * (16 if unit in ("em", "rem") else 1.33 if unit == "pt" else 1)
        if px < 4:
            return True
    # added after Problem 7 (red team): collapsed boxes, clipping, and off-screen positioning
    if ZERO_BOX.search(style) and "overflow:hidden" in style:
        return True
    if "clip:rect(0" in style or re.search(r"clip-path:inset\((?:50|100)%", style):
        return True
    m = OFFSCREEN.search(style)
    if m and int(m.group(1)) >= 500 and ("position:absolute" in style or "position:fixed" in style or "text-indent" in style):
        return True
    return False


def _parse_css(css: str) -> dict[str, str]:
    """Very small <style> sheet reader: maps simple selectors (tag, .class, #id, tag.class) to their declarations."""
    rules: dict[str, str] = {}
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        for sel in selectors.split(","):
            sel = sel.strip().lower()
            if re.fullmatch(r"[a-z0-9]*(?:[.#][\w-]+)?", sel) and sel:
                rules[sel] = rules.get(sel, "") + ";" + body
    return rules


class _VisibleHTML(HTMLParser):
    """Collects visible text; text inside hidden elements, comments, scripts and styles is set aside."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.visible: list[str] = []
        self.removed: list[str] = []
        self.stack: list[tuple[str, bool]] = []  # (tag, hidden)
        self.css: dict[str, str] = {}  # rules from <style> blocks

    def _hidden(self) -> bool:
        return any(h for _, h in self.stack)

    def _sheet_style(self, tag: str, attrs: dict) -> str:
        keys = [tag] + [f".{c}" for c in (attrs.get("class") or "").lower().split()]
        keys += [f"{tag}.{c}" for c in (attrs.get("class") or "").lower().split()]
        if attrs.get("id"):
            keys.append(f"#{attrs['id'].lower()}")
        return ";".join(self.css.get(k, "") for k in keys)

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            if tag == "br" and not self._hidden():
                self.visible.append("\n")
            return
        attrs = dict(attrs)
        hidden = tag in SKIP_TAGS or _hidden_style(attrs, self._sheet_style(tag, attrs))
        self.stack.append((tag, hidden))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        while self.stack:  # pop up to the matching tag (tolerates sloppy HTML)
            t, _ = self.stack.pop()
            if t == tag:
                break
        if tag in BLOCK_TAGS and not self._hidden():
            self.visible.append("\n")

    def handle_data(self, data):
        if self.stack and self.stack[-1][0] == "style":  # remember the sheet so classes/ids can be checked
            self.css.update(_parse_css(data))
            return
        text = ZERO_WIDTH.sub("", data).strip()
        if not text:
            return
        skipped = any(t in SKIP_TAGS for t, _ in self.stack)
        if self._hidden():
            if not skipped:  # don't report <style>/<script> code as "hidden text"
                self.removed.append(text)
        else:
            self.visible.append(text + " ")

    def handle_comment(self, data):
        if data.strip():
            self.removed.append(f"<!--{data.strip()}-->")


def _tidy(parts: list[str]) -> str:
    lines = (line.strip() for line in "".join(parts).splitlines())
    return "\n".join(line for line in lines if line)


def visible_html(html: str) -> tuple[str, list[str]]:
    p = _VisibleHTML()
    p.feed(html)
    return _tidy(p.visible), p.removed


def visible_pdf(path: Path) -> tuple[str, list[str]]:
    """Keep PDF text a person can see: drawn (not render mode 3/7), readable size, not white, and on the page."""
    lines: list[tuple[float, float, str]] = []
    removed: list[str] = []
    for page in PdfReader(path).pages:
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        fill = [(0.0, 0.0, 0.0)]
        mode = [0]  # text render mode: 3 = invisible, 7 = clip only (added after Problem 7)
        saved: list[tuple] = []

        def before(op, args, cm, tm):
            if op == b"q":
                saved.append((fill[0], mode[0]))
            elif op == b"Q" and saved:
                fill[0], mode[0] = saved.pop()
            elif op == b"Tr" and args:
                mode[0] = int(args[0])
            elif op == b"rg" and len(args) == 3:
                fill[0] = tuple(float(a) for a in args)
            elif op == b"g" and args:
                fill[0] = (float(args[0]),) * 3
            elif op == b"k" and len(args) == 4:  # CMYK -> rough RGB
                c, m, y, k = (float(a) for a in args)
                fill[0] = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))

        def visit(text, cm, tm, font_dict, font_size):
            text = ZERO_WIDTH.sub("", text).strip()
            if not text:
                return
            scale = (float(tm[0]) ** 2 + float(tm[1]) ** 2) ** 0.5 * (float(cm[0]) ** 2 + float(cm[1]) ** 2) ** 0.5
            size = float(font_size) * (scale or 1)
            x = float(tm[4]) * float(cm[0]) + float(cm[4])
            y = float(tm[5]) * float(cm[3]) + float(cm[5])
            invisible = mode[0] in (3, 7)
            too_small = size < 4
            too_light = min(fill[0]) > 0.9  # white or near-white on a white page
            off_page = not (0 <= x <= width and 0 <= y <= height)
            if invisible or too_small or too_light or off_page:
                why = ("invisible ink" if invisible else "tiny font" if too_small
                       else "white text" if too_light else "off the page")
                removed.append(f"[{why}] {text}")
            else:
                lines.append((-y, x, text))

        page.extract_text(visitor_operand_before=before, visitor_text=visit)
    return "\n".join(t for _, _, t in sorted(lines)), removed


def visible_eml(raw: bytes) -> tuple[str, list[str]]:
    msg = email.message_from_bytes(raw, policy=policy.default)
    header = "\n".join(f"{h}: {msg[h]}" for h in ("From", "To", "Subject", "Date") if msg[h])
    removed: list[str] = []
    plain = msg.get_body(preferencelist=("plain",))
    if plain is not None:
        body = ZERO_WIDTH.sub("", plain.get_content())
        html = msg.get_body(preferencelist=("html",))
        if html is not None:  # what the email app shows; anything hidden there is reported too
            removed = visible_html(html.get_content())[1]
    else:
        html = msg.get_body(preferencelist=("html",))
        body, removed = visible_html(html.get_content()) if html is not None else ("", [])
    return f"{header}\n\n{body.strip()}", removed


def visible_text(path: Path) -> tuple[str, list[str]]:
    """(text a person would see, hidden snippets that were removed)."""
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm"):
        return visible_html(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".pdf":
        return visible_pdf(path)
    if suffix == ".eml":
        return visible_eml(path.read_bytes())
    return ZERO_WIDTH.sub("", path.read_text(encoding="utf-8", errors="replace")), []


# =====================================================================
# Design layer: code makes the decision from the handbook, not the model
# =====================================================================
def _section(text: str, number: int) -> str:
    m = re.search(rf"^## {number}\..*?(?=^## \d+\.|\Z)", text, re.M | re.S)
    return m.group(0) if m else ""


def _table_rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        if line.startswith("|") and not set(line) <= set("|- "):
            rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows[1:]  # drop header row


def load_rules() -> dict:
    text = HANDBOOK.read_text(encoding="utf-8")
    approved = {r[1].lower() for r in _table_rows(_section(text, 5))}
    removed = {r[0].lower() for r in _table_rows(_section(text, 6))}
    max_cost = {r[0]: float(r[4].lstrip("$")) for r in _table_rows(_section(text, 9)) if r[0].startswith("CC-")}
    rule = _section(text, 4)
    max_lead = int(re.search(r"lead time is (\d+) days or less", rule).group(1))
    max_min = int(re.search(r"minimum order is (\d+) units or less", rule).group(1))
    return {"approved": approved, "removed": removed, "max_cost": max_cost, "max_lead": max_lead, "max_min": max_min}


RULES = load_rules()


def decide(vendor, sku, price, lead, min_order) -> tuple[str, str]:
    """The four purchasing checks from handbook section 4, in order. Returns (decision, one-sentence reason)."""
    v = (vendor or "").strip().lower()
    if v in RULES["removed"] or v not in RULES["approved"]:
        status = "is on the removed/pending list" if v in RULES["removed"] else "is not on the approved vendor list"
        return "do_not_recommend", f"Approved-vendor check fails: {vendor or 'the vendor'} {status}."
    if price is None:
        return "do_not_recommend", "Price check fails: the document does not state a unit price."
    if sku not in RULES["max_cost"]:
        return "do_not_recommend", f"Price check fails: SKU {sku or '(none)'} is not in the catalogue."
    cap = RULES["max_cost"][sku]
    if price > cap:
        return "do_not_recommend", f"Price check fails: ${price:.2f} is above the ${cap:.2f} max unit cost for {sku}."
    if lead is None:
        return "do_not_recommend", "Lead-time check fails: the document does not state a lead time."
    if lead > RULES["max_lead"]:
        return "do_not_recommend", f"Lead-time check fails: {lead} days is more than {RULES['max_lead']} days."
    if min_order is None:
        return "do_not_recommend", "Minimum-order check fails: the document does not state a minimum order."
    if min_order > RULES["max_min"]:
        return "do_not_recommend", f"Minimum-order check fails: {min_order} units is more than {RULES['max_min']}."
    return "recommend", (f"All four checks pass: approved vendor, ${price:.2f} is within the ${cap:.2f} max, "
                         f"{lead}-day lead time, and {min_order}-unit minimum.")


NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def ground(value, text: str):
    """Keep a number only if it is actually written in the document text; otherwise treat it as unknown."""
    if value is None:
        return None
    found = {float(n.replace(",", "")) for n in NUMBER.findall(text)}
    return value if any(abs(float(value) - f) < 0.005 for f in found) else None
