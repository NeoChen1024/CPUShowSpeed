"""Infinity-Parser2 wire format; no upstream client or PDF parser imports.

Prompt reproduced from infly-ai/INF-MLLM, Infinity-Parser2 0.4.0,
under Apache-2.0. See third-party/Infinity-Parser2-LICENSE.txt.
All validation and resizing below are local implementations.
"""

import json
import math
import re

from PIL import Image

# Source: https://github.com/infly-ai/INF-MLLM/tree/main/Infinity-Parser2
PROMPT = """
- Extract layout information from the provided PDF image.
- For each layout element, output its bbox, category, and the text content within the bbox.
- Bbox format: [x1, y1, x2, y2].
- Allowed layout categories: ['header', 'title', 'text', 'figure', 'table', 'formula', 'figure_caption', 'table_caption', 'formula_caption', 'figure_footnote', 'table_footnote', 'page_footnote', 'footer'].
- Text extraction and formatting:
  1) For 'figure', the text field must be an empty string.
  2) For 'formula', format text as LaTeX.
  3) For 'table', format text as HTML.
  4) For all other categories (e.g., text, title), format text as Markdown.
- The output text must be exactly the original text from the image, with no translation or rewriting.
- Sort all layout elements in human reading order.
- Final output must be a single JSON object.
"""
MODEL = "Infinity-Parser2-Flash"
DPI = 300
MAX_TOKENS = 32768
MIN_PIXELS = 2048
MAX_PIXELS = 16777216
CATEGORIES = {
    "header",
    "title",
    "text",
    "figure",
    "table",
    "formula",
    "figure_caption",
    "table_caption",
    "formula_caption",
    "figure_footnote",
    "table_footnote",
    "page_footnote",
    "footer",
}


def resize(image: Image.Image) -> Image.Image:
    """Match the documented 32-pixel grid and pixel budget without Torch."""
    width, height = image.size
    if max(width, height) / min(width, height) > 200:
        raise ValueError("page aspect ratio exceeds 200")
    w, h = max(32, round(width / 32) * 32), max(32, round(height / 32) * 32)
    if w * h > MAX_PIXELS:
        scale = math.sqrt(MAX_PIXELS / (width * height))
        w, h = math.floor(width * scale / 32) * 32, math.floor(height * scale / 32) * 32
    elif w * h < MIN_PIXELS:
        scale = math.sqrt(MIN_PIXELS / (width * height))
        w, h = math.ceil(width * scale / 32) * 32, math.ceil(height * scale / 32) * 32
    return image.resize((max(32, w), max(32, h)), Image.Resampling.BICUBIC)


def parse_layout(raw: str) -> list[dict]:
    """Accept complete JSON (optionally fenced), never repair truncated output."""
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    items = json.loads(text)
    if not isinstance(items, list):
        raise ValueError("Infinity layout must be an array")
    for item in items:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("category"), str)
            or item.get("category") not in CATEGORIES
            or not isinstance(item.get("text"), str)
        ):
            raise ValueError("invalid Infinity layout block")
        box = item.get("bbox")
        if not isinstance(box, list) or len(box) != 4 or any(type(x) not in (int, float) or not math.isfinite(x) for x in box):
            raise ValueError("invalid Infinity bounding box")
        if not (0 <= box[0] < box[2] <= 1000 and 0 <= box[1] < box[3] <= 1000):
            raise ValueError("Infinity bounding box outside normalized page")
    return items


def has_repeat(raw: str) -> bool:
    """Detect long repeated suffixes, including unfinished JSON generations."""
    tail = raw[-8000:].rstrip()
    for size in range(1, 251):
        unit = tail[-size:]
        count = max(8, math.ceil(400 / size))
        if len(unit) == size and tail.endswith(unit * count):
            return True
    return False


MIN_PDF_IMAGE_DIM = 0
TOP_P = (1.0, 1.0)
VISUAL_LABELS = {"figure"}
CONFIG = {
    "backend": "infinity",
    "adapter_version": 1,
    "image_dpi": DPI,
    "bbox_scale": 1000,
    "max_output_tokens": MAX_TOKENS,
    "min_pixels": MIN_PIXELS,
    "max_pixels": MAX_PIXELS,
    "resize_grid": 32,
}


def parse_page(raw: str, width: int, height: int) -> tuple[list[dict], list[dict]]:
    chunks = parse_layout(raw)
    blocks = []
    for chunk in chunks:
        label, content, box = chunk["category"], chunk["text"], chunk["bbox"]
        bbox = [int(box[0] * width / 1000), int(box[1] * height / 1000), int(box[2] * width / 1000), int(box[3] * height / 1000)]
        if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            raise ValueError("Infinity bounding box collapses at source resolution")
        block = {"kind": "text", "source_label": label, "bbox_px": bbox}
        if label == "table":
            block.update(kind="table", html=content)
        elif label == "figure":
            block.update(kind="visual", caption=None)
        else:
            block["markdown"] = content
        blocks.append(block)
    return chunks, blocks
