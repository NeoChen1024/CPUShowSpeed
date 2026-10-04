"""1990s themes of the timeline page, built from pinned third-party stylesheets and fonts.

Windows 98 takes rules from 98.css and System 7 from system.css, both MIT; the amber VT220
theme uses the public-domain Glass TTY VT220 font. Rules are picked by their exact selector
list, scoped to `:root[data-theme="…"]`, and their icons and fonts are inlined as data URIs,
so the page stays one file. A selector missing after a submodule update is an error.
"""

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "third-party"
WIN98 = ROOT / "98.css"
SYSTEM7 = ROOT / "system.css"
GLASSTTY = ROOT / "glasstty"

MIME = {".svg": "image/svg+xml", ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf"}

CREDITS = (
    'Themes: <a href="https://github.com/jdan/98.css">98.css</a> © Jordan Scales (MIT) with the MS Sans Serif '
    'FontStruction by “lou” (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a>); '
    '<a href="https://github.com/sakofchit/system.css">system.css</a> © Sakun Acharige (MIT) with ChicagoFLF '
    '(public domain); <a href="https://github.com/svofski/glasstty">Glass TTY VT220</a> by Viacheslav Slavinsky '
    "(public domain)."
)


def data_uri(path):
    if not path.is_file():
        raise ValueError(f"missing theme asset {path}; run git submodule update --init {path.relative_to(ROOT.parent).parts[0]}")
    return f'url("data:{MIME[path.suffix]};base64,{base64.b64encode(path.read_bytes()).decode()}")'


def font_face(family, path, weight="normal"):
    return f'@font-face{{font-family:"{family}";src:{data_uri(path)};font-weight:{weight};font-display:swap}}'


def _blocks(css):
    """Top-level (selector list, body) pairs; at-rules come back whole and are not selected."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i = [], 0
    while (j := css.find("{", i)) >= 0:
        depth, k = 1, j + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        parts = [" ".join(p.split()) for p in css[i:j].split(",")]
        out.append((", ".join(parts), css[j + 1 : k - 1]))
        i = k
    return out


def _rename(part, rename):
    for old, new in rename.items():
        if part == old or (part.startswith(old) and not re.match(r"[\w-]", part[len(old)])):
            return new + part[len(old) :]
    return part


def _scope(part, scope):
    if part == ":root":
        return scope
    if part.startswith("::-webkit-scrollbar"):
        return f"{scope}{part}, {scope} {part}"
    return f"{scope} {part}"


def take(sheet, selectors, scope, rename=None, prefix=None):
    """Scoped rules of `sheet` with exactly these selector lists, plus every rule starting with `prefix`."""
    blocks = _blocks((sheet / "style.css").read_text())
    found = [(s, b) for s, b in blocks if s in selectors or (prefix and s.startswith(prefix))]
    missing = set(selectors) - {s for s, _ in found}
    if missing:
        raise ValueError(f"{sheet.name}: selectors not found: {sorted(missing)}")
    out = []
    for selector, body in found:
        body = re.sub(r'(?:svg-load|url)\("(?:\./)?([^"]+)"\)', lambda m: data_uri(sheet / m.group(1)), body)
        body = " ".join(body.replace("Chicago_12", "Chicago").split())
        parts = [_scope(_rename(p, rename or {}), scope) for p in selector.split(", ")]
        out.append(", ".join(parts) + "{" + body + "}")
    return "\n".join(out)


def _scoped(scope, css):
    """Own rules written as `selector{…}` lines, each prefixed with the theme scope."""
    rules = []
    for selector, body in _blocks(css):
        rules.append(", ".join(scope if p == ":root" else f"{scope} {p}" for p in selector.split(", ")) + "{" + body.strip() + "}")
    return "\n".join(rules)


def _license(path):
    return "/*\n" + path.read_text().replace("*/", "* /") + "*/"


WIN98_VARS = {
    "color-scheme": "light",
    "bg": "#c0c0c0",
    "fg": "#000000",
    "muted": "#404040",
    "link": "#0000ff",
    "rule": "#808080",
    "panel": "#c0c0c0",
    "panel-border": "#808080",
    "card": "#c0c0c0",
    "card-border": "#808080",
    "plot-bg": "#ffffff",
    "grid": "#c0c0c0",
    "grid-minor": "#e8e8e8",
    "accent": "#000080",
    "accent-wash": "#00008018",
    "focus": "#000080",
    "overview-bar": "#000080",
    "overview-mask": "#80808080",
    "badge": "#ffffe1",
    "prediction": "#ff0000",
    "halo": "#ffffff",
    "shadow": "#00000000",
    "interval-alpha": ".15",
    "point-alpha": ".55",
    # The VGA 16-colour palette.
    "route-0": "#000080",
    "route-1": "#800000",
    "route-2": "#008000",
    "route-3": "#800080",
    "route-4": "#808000",
    "route-5": "#008080",
    "route-6": "#0000ff",
    "route-7": "#ff00ff",
    "lineage-node": "#ffffff",
    "lineage-unit": "#ffffe1",
    "lineage-model": "#e0e0e0",
    "lineage-active": "#000080",
    "lineage-title": "#000000",
    "lineage-subtitle": "#404040",
    "lineage-model-text": "#800080",
    "lineage-lane": "#404040",
    "lineage-arrow": "#000000",
    "edge-definition": "#008080",
    "edge-candidate": "#808000",
    "edge-diagnostic": "#808080",
    "edge-fit": "#000080",
}

SYSTEM7_VARS = dict(
    WIN98_VARS,
    **{
        "bg": "#ffffff",
        "muted": "#555555",
        "link": "#000000",
        "rule": "#bbbbbb",
        "panel": "#ffffff",
        "panel-border": "#000000",
        "card": "#ffffff",
        "card-border": "#000000",
        "grid": "#cccccc",
        "grid-minor": "#eeeeee",
        "accent": "#000000",
        "accent-wash": "#00000014",
        "focus": "#000000",
        "overview-bar": "#000000",
        "overview-mask": "#a5a5a580",
        "badge": "#eeeeee",
        "prediction": "#dd0806",
        # The colour QuickDraw palette of System 7.
        "route-0": "#0000d4",
        "route-1": "#dd0806",
        "route-2": "#1fb714",
        "route-3": "#4700a5",
        "route-4": "#ff6403",
        "route-5": "#f20884",
        "route-6": "#02abea",
        "route-7": "#562c05",
        "lineage-unit": "#ffffff",
        "lineage-model": "#eeeeee",
        "lineage-active": "#000000",
        "lineage-subtitle": "#555555",
        "lineage-model-text": "#4700a5",
        "lineage-lane": "#000000",
        "edge-definition": "#006411",
        "edge-candidate": "#ff6403",
        "edge-diagnostic": "#a5a5a5",
        "edge-fit": "#0000d4",
    },
)

VT220_VARS = {
    "color-scheme": "dark",
    "bg": "#0a0600",
    "fg": "#ffb000",
    "muted": "#c98a00",
    "link": "#ffd27a",
    "rule": "#4a3000",
    "panel": "#140c00",
    "panel-border": "#6b4600",
    "card": "#0a0600",
    "card-border": "#ffb000",
    "plot-bg": "#0a0600",
    "grid": "#3a2600",
    "grid-minor": "#1e1400",
    "accent": "#ffb000",
    "accent-wash": "#ffb00022",
    "focus": "#ffe0a0",
    "overview-bar": "#b37a00",
    "overview-mask": "#2a1a0080",
    "badge": "#241700",
    "prediction": "#fff2d0",
    "halo": "#0a0600",
    "shadow": "#ffb00033",
    "interval-alpha": ".25",
    "point-alpha": ".7",
    # One phosphor: routes differ in intensity and hue within amber.
    "route-0": "#ffb000",
    "route-1": "#ff7a00",
    "route-2": "#ffe08a",
    "route-3": "#c88400",
    "route-4": "#ff9e40",
    "route-5": "#fff0b0",
    "route-6": "#a86000",
    "route-7": "#e8c060",
    "lineage-node": "#0a0600",
    "lineage-unit": "#1d1300",
    "lineage-model": "#241800",
    "lineage-active": "#ffd27a",
    "lineage-title": "#ffb000",
    "lineage-subtitle": "#c98a00",
    "lineage-model-text": "#ffcc66",
    "lineage-lane": "#c98a00",
    "lineage-arrow": "#c98a00",
    "edge-definition": "#ffd27a",
    "edge-candidate": "#ff8c1a",
    "edge-diagnostic": "#7a5500",
    "edge-fit": "#ffb000",
}


def win98_css(scope):
    vendor = take(
        WIN98,
        [
            ":root",
            "body",
            "button, label, input, legend, textarea, select, option, table, ul.tree-view, .window, .title-bar, li[role=tab]",
            'button, input[type="submit"], input[type="reset"]',
            'button:not(:disabled):active, input[type="submit"]:not(:disabled):active, input[type="reset"]:not(:disabled):active',
            'button:focus, input[type="submit"]:focus, input[type="reset"]:focus',
            "fieldset",
            "legend",
            'input[type="text"], input[type="password"], input[type="email"], input[type="url"], input[type="tel"], '
            'input[type="number"], input[type="search"], select, textarea',
            'input[type="text"], input[type="password"], input[type="email"], input[type="url"], input[type="tel"], '
            'input[type="search"], select',
            "select",
            "select:focus",
            "select:active",
            ".window",
            ".title-bar",
            ".title-bar-text",
            "menu[role=tablist]",
            "menu[role=tablist] > li",
            "menu[role=tablist] > li[aria-selected=true]",
            "menu[role=tablist] > li > a",
            "menu[role=tablist] > li[aria-selected=true] > a:focus",
            "menu[role=tablist] > li > a:focus",
        ],
        scope,
        rename={".window": "body", ".title-bar-text": "h1 span", ".title-bar": "h1"},
        prefix="::-webkit-scrollbar",
    )
    own = _scoped(
        scope,
        f"""
:root{{background:#008080}}
body{{position:relative;max-width:1520px;margin:16px auto;padding:3px 3px 12px}}
h1{{margin:0 0 10px;min-height:28px;font-size:13px;padding:3px 6px}}
#load-status, #timeline-app, .theme-credits{{margin-inline:10px}}
.theme-bar{{position:absolute;top:6px;right:10px;margin:0;z-index:1}}
.theme-bar label{{color:#fff;font-weight:bold}}
.theme-bar select{{color:#000}}
input[type="checkbox"]{{appearance:none;flex:none;width:13px;min-width:13px;height:13px;margin:0 6px 0 0;vertical-align:-2px;background:#fff;box-shadow:var(--border-field)}}
input[type="checkbox"]:checked{{background:#fff {data_uri(WIN98 / "icon/checkmark.svg")} center no-repeat}}
input[type="radio"]{{accent-color:#000080}}
fieldset{{margin:8px 0}}
.timeline-chart{{padding:2px;background:#fff;box-shadow:var(--border-field)}}
#tip{{border:none;border-radius:0;background:var(--surface);box-shadow:var(--border-window-outer), var(--border-window-inner)}}
th{{background:var(--surface);box-shadow:var(--border-raised-outer), var(--border-raised-inner)}}
#lineage, #calculator{{border:none;border-radius:0;box-shadow:var(--border-window-outer), var(--border-window-inner)}}
#lineage h2{{font:bold 13px "Pixelated MS Sans Serif", Arial;-webkit-font-smoothing:none}}
#lineage-card, #calc-kind, .lineage-badge{{border-radius:0}}
#filters>summary{{border:none;border-radius:0;padding:4px 10px;background:var(--surface);box-shadow:var(--border-raised-outer), var(--border-raised-inner)}}
.filters-panel{{border:none;border-radius:0;background:var(--surface);box-shadow:var(--border-window-outer), var(--border-window-inner)}}
menu[role=tablist]{{gap:0;margin-top:20px;border:none}}
menu[role=tablist]>li>a{{padding:0;border:none}}
menu[role=tablist]>li[aria-selected=true]>a{{font-weight:normal}}
.tab-panel{{position:relative;z-index:2;padding:10px;background:var(--surface);box-shadow:var(--border-window-outer), var(--border-window-inner)}}
""",
    )
    return "\n".join(
        [
            _license(WIN98 / "LICENSE"),
            font_face("Pixelated MS Sans Serif", WIN98 / "fonts/converted/ms_sans_serif.woff2"),
            font_face("Pixelated MS Sans Serif", WIN98 / "fonts/converted/ms_sans_serif_bold.woff2", "bold"),
            vendor,
            own,
        ]
    )


def system7_css(scope):
    vendor = take(
        SYSTEM7,
        [
            ":root",
            ".title-bar",
            ".title-bar .title",
            ".window",
            ".btn, .btn-default",
            ".btn:active",
            ".btn:disabled",
            "input",
            'input[type="text"]:focus-visible, input[type="email"]:focus-visible, input[type="password"]:focus-visible, '
            'input[type="number"]:focus-visible, input[type="date"]:focus-visible, input[type="time"]:focus-visible, '
            'input[type="datetime"]:focus-visible, input[type="datetime-local"]:focus-visible, '
            'input[type="month"]:focus-visible, input[type="week"]:focus-visible, input[type="search"]:focus-visible, '
            'input[type="tel"]:focus-visible, input[type="color"]:focus-visible, textarea:focus',
            "select",
        ],
        scope,
        rename={".title-bar .title": "h1 span", ".title-bar": "h1", ".window": "body", ".btn": "button"},
        prefix="::-webkit-scrollbar",
    )
    own = _scoped(
        scope,
        f"""
:root{{background:repeating-conic-gradient(#000 0 25%, #fff 0 50%) 0 0/2px 2px}}
body{{position:relative;max-width:1520px;margin:16px auto;padding:0 0 12px;overflow:visible;font:14px/1.4 Geneva, "Helvetica Neue", Arial, sans-serif;box-shadow:2px 2px 0 #000}}
h1{{margin:0 0 10px;height:auto;min-height:1.6rem;border-bottom:1px solid #000;padding:0.3rem 0.2rem}}
h1 span{{font-size:16px;font-weight:normal}}
#load-status, #timeline-app, .theme-credits{{margin-inline:10px}}
.theme-bar{{position:absolute;top:4px;right:10px;margin:0;z-index:1;background:#fff;padding:0 6px}}
button, input, select, legend, label, th, summary, menu[role=tablist] a, #count, #range-label{{font-family:Chicago, Geneva, sans-serif}}
button, input, select{{font-size:16px}}
button{{padding:0 14px;min-width:0}}
select{{width:auto;padding:2px 28px 2px 8px}}
input[type="checkbox"]{{appearance:none;flex:none;width:13px;min-width:13px;height:13px;margin:0 6px 0 0;padding:0;vertical-align:-2px;border:1.5px solid #000;background:#fff}}
input[type="checkbox"]:checked{{background:#fff {data_uri(SYSTEM7 / "icon/checkmark.svg")} center/9px no-repeat}}
input[type="radio"]{{accent-color:#000}}
fieldset{{border:1px solid #000;margin:8px 0}}
.timeline-chart{{border:1px solid #000}}
#tip{{border-width:1px;border-radius:0;box-shadow:2px 2px 0 #000}}
th{{border-bottom:2px solid #000}}
#lineage, #calculator{{border:1px solid #000;border-radius:0;box-shadow:2px 2px 0 #000}}
#lineage h2{{font:16px Chicago, Geneva, sans-serif}}
#lineage-card, #calc-kind, .lineage-badge{{border-radius:0}}
#filters>summary{{border:1.5px solid #000;border-radius:6px;padding:2px 12px;font-size:16px}}
.filters-panel{{border:1px solid #000;border-radius:0;box-shadow:2px 2px 0 #000}}
menu[role=tablist]{{gap:0;border-bottom:1px solid #000}}
menu[role=tablist]>li>a{{margin-right:-1px;padding:2px 14px;border:1px solid #000;border-bottom:none;border-radius:6px 6px 0 0;font-weight:normal}}
menu[role=tablist]>li[aria-selected=true]>a{{background:#000;color:#fff}}
""",
    )
    return "\n".join([_license(SYSTEM7 / "LICENSE"), font_face("Chicago", SYSTEM7 / "fonts/ChicagoFLF.woff2"), vendor, own])


def vt220_css(scope):
    own = _scoped(
        scope,
        """
body{font:19px/1.25 "Glass TTY VT220", monospace;text-shadow:0 0 2px #ffb000aa, 0 0 9px #ff8c0055}
body::after{content:"";position:fixed;inset:0;z-index:30;pointer-events:none;background:repeating-linear-gradient(#0000 0 2px, #0000002e 2px 3px)}
h1{font-size:30px;font-weight:normal;letter-spacing:.05em}
input, select, button{font:inherit;color:var(--fg);background:var(--bg);border:1px solid var(--fg);border-radius:0;text-shadow:inherit}
button:hover, button:focus-visible, select:focus-visible, input:focus-visible{background:var(--fg);color:var(--bg);outline:none;text-shadow:none}
input[type="checkbox"], input[type="radio"]{accent-color:#ffb000}
::selection{background:#ffb000;color:#0a0600;text-shadow:none}
fieldset{border:1px solid var(--panel-border)}
#tip{border-radius:0;font-size:17px}
svg text{text-shadow:none}
#lineage, #lineage-card, #calculator, #calc-kind, .lineage-badge{border-radius:0}
#lineage h2{font-size:24px;font-weight:normal}
#filters>summary, .filters-panel{border-radius:0;border-color:var(--fg)}
menu[role=tablist]>li[aria-selected=true]>a{background:var(--fg);color:var(--bg);text-shadow:none;font-weight:normal}
""",
    )
    return "\n".join([_license(GLASSTTY / "LICENSE"), font_face("Glass TTY VT220", GLASSTTY / "Glass_TTY_VT220.ttf"), own])
