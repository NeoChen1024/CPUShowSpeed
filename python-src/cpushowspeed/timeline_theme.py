"""Colour themes of the timeline page: CSS custom properties, the theme picker and its early initialisation.

Every colour the page draws (CSS, SVG markup and canvas) reads a `--name` property, so a theme
is one set of values. `auto` follows the browser's light/dark preference; a chosen theme is
remembered in localStorage and applied before the first paint.
"""

from cpushowspeed import timeline_retro

STORAGE_KEY = "cpushowspeed-theme"

LIGHT = {
    "color-scheme": "light",
    "bg": "#ffffff",
    "fg": "#223",
    "muted": "#556",
    "link": "#0b57b0",
    "rule": "#ddd",
    "panel": "#f4f6f8",
    "panel-border": "#bdccd7",
    "card": "#ffffff",
    "card-border": "#d8e2e9",
    "plot-bg": "#fafbfd",
    "grid": "#dde3e8",
    "grid-minor": "#eeeeee",
    "accent": "#207ca3",
    "accent-wash": "#207ca318",
    "focus": "#e78a19",
    "overview-bar": "#829bad",
    "overview-mask": "#ccd3da80",
    "badge": "#e8f1f8",
    "prediction": "#b34400",
    "halo": "#ffffff",
    "shadow": "#22333333",
    "interval-alpha": ".12",
    "point-alpha": ".45",
    "route-0": "#207ca3",
    "route-1": "#bd5934",
    "route-2": "#397947",
    "route-3": "#7c57a2",
    "route-4": "#ad7130",
    "route-5": "#ca4779",
    "route-6": "#4064ac",
    "route-7": "#537b79",
    "lineage-node": "#ffffff",
    "lineage-unit": "#d9f3ed",
    "lineage-model": "#e8e6f7",
    "lineage-active": "#1c658e",
    "lineage-title": "#213b50",
    "lineage-subtitle": "#506676",
    "lineage-model-text": "#60567d",
    "lineage-lane": "#516a7a",
    "lineage-arrow": "#648398",
    "edge-definition": "#148c80",
    "edge-candidate": "#a66c3d",
    "edge-diagnostic": "#8a949c",
    "edge-fit": "#497e9d",
}

DARK = dict(
    LIGHT,
    **{
        "color-scheme": "dark",
        "bg": "#12161b",
        "fg": "#dde4ea",
        "muted": "#9aa7b2",
        "link": "#8ab4f8",
        "rule": "#2c343c",
        "panel": "#1a2027",
        "panel-border": "#34414c",
        "card": "#11161b",
        "card-border": "#33404b",
        "plot-bg": "#0f1418",
        "grid": "#26313a",
        "grid-minor": "#1c252c",
        "accent": "#4fb0dc",
        "accent-wash": "#4fb0dc22",
        "focus": "#f0a040",
        "overview-bar": "#5d7486",
        "overview-mask": "#2a323880",
        "badge": "#1d3242",
        "prediction": "#ff8a3d",
        "halo": "#0f1418",
        "shadow": "#00000088",
        "interval-alpha": ".22",
        "point-alpha": ".6",
        "route-0": "#5fb3df",
        "route-1": "#f08a5d",
        "route-2": "#6cc47e",
        "route-3": "#b394e0",
        "route-4": "#e0a458",
        "route-5": "#f07aa8",
        "route-6": "#7c9cf0",
        "route-7": "#7fbdb9",
        "lineage-node": "#161c22",
        "lineage-unit": "#173a33",
        "lineage-model": "#2a2742",
        "lineage-active": "#6fb6e0",
        "lineage-title": "#dde4ea",
        "lineage-subtitle": "#9aa7b2",
        "lineage-model-text": "#b8a9e6",
        "lineage-lane": "#8fa3b2",
        "lineage-arrow": "#7f9fb3",
        "edge-definition": "#3cc1b2",
        "edge-candidate": "#d99a63",
        "edge-diagnostic": "#7d8891",
        "edge-fit": "#6fa8c9",
    },
)

# (value, label, variables, builder of extra CSS given the theme's root selector).
THEMES = [
    ("light", "Light", LIGHT, None),
    ("dark", "Dark", DARK, None),
    ("win98", "Windows 98", timeline_retro.WIN98_VARS, timeline_retro.win98_css),
    ("system7", "System 7", timeline_retro.SYSTEM7_VARS, timeline_retro.system7_css),
    ("vt220", "Amber VT220", timeline_retro.VT220_VARS, timeline_retro.vt220_css),
]


def _variables(values):
    return ";".join(("color-scheme:" if k == "color-scheme" else f"--{k}:") + v for k, v in values.items())


def stylesheet():
    """Theme variables: light by default, dark under the browser preference unless a theme is chosen."""
    css = [f":root{{{_variables(LIGHT)}}}"]
    css.append(f"@media(prefers-color-scheme:dark){{:root:not([data-theme]){{{_variables(DARK)}}}}}")
    for value, _, variables, extra in THEMES:
        scope = f':root[data-theme="{value}"]'
        css.append(f"{scope}{{{_variables(variables)}}}")
        if extra:
            css.append(extra(scope))
    css.append(".theme-bar{display:flex;justify-content:flex-end;gap:8px;align-items:center;margin:-8px 0 8px}")
    css.append(".theme-credits{margin-top:32px;font-size:12px;color:var(--muted)}")
    return "\n".join(css)


def picker():
    options = '<option value="auto">Auto (system)</option>' + "".join(
        f'<option value="{value}">{label}</option>' for value, label, _, _ in THEMES
    )
    return f'<div class="theme-bar"><label>Theme: <select id="theme">{options}</select></label></div>'


def credits():
    return f'<p class="theme-credits">{timeline_retro.CREDITS}</p>'


# Runs in <head>: applies the stored theme before the first paint, then binds the picker. A
# `themechange` event tells canvas drawing to reread the colours.
INIT_SCRIPT = (
    """<script id="theme-init">(()=>{const key='"""
    + STORAGE_KEY
    + """',root=document.documentElement;
const themes=new Set(["""
    + ",".join(f"'{value}'" for value, _, _, _ in THEMES)
    + """]);
function apply(value,save){if(themes.has(value))root.dataset.theme=value;else delete root.dataset.theme;
 if(save)try{value==='auto'?localStorage.removeItem(key):localStorage.setItem(key,value);}catch{}
 dispatchEvent(new Event('themechange'));}
let stored=null;try{stored=localStorage.getItem(key);}catch{}
apply(stored,false);
matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change',()=>dispatchEvent(new Event('themechange')));
addEventListener('DOMContentLoaded',()=>{const picker=document.querySelector('#theme');if(!picker)return;
 picker.value=themes.has(root.dataset.theme)?root.dataset.theme:'auto';
 picker.addEventListener('change',()=>apply(picker.value,true));});
})();</script>"""
)
