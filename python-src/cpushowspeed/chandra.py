"""Local Chandra HTML adapter, compatible with the 0.2.0 output format.

Prompt and behavioral reference: https://github.com/datalab-to/chandra
Apache-2.0; see third-party/Chandra-LICENSE.txt. This module implements only
page parsing, Markdown conversion, image sizing and repetition checks.
"""

import re

from bs4 import BeautifulSoup
from cpushowspeed.ocr_settings import value
from markdownify import MarkdownConverter
from PIL import Image

PROMPT = """OCR this image to HTML, arranged as layout blocks.  Each layout block should be a div with the data-bbox attribute representing the bounding box of the block in x0 y0 x1 y1 format.  Bboxes are normalized 0-1000. The data-label attribute is the label for the block.

Use the following labels:
- Caption
- Footnote
- Equation-Block
- List-Group
- Page-Header
- Page-Footer
- Image
- Section-Header
- Table
- Text
- Complex-Block
- Code-Block
- Form
- Table-Of-Contents
- Figure
- Chemical-Block
- Diagram
- Bibliography
- Blank-Page

Only use these tags ['math', 'br', 'i', 'b', 'u', 'del', 'sup', 'sub', 'table', 'tr', 'td', 'p', 'th', 'div', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'ul', 'ol', 'li', 'input', 'a', 'span', 'img', 'hr', 'tbody', 'small', 'caption', 'strong', 'thead', 'big', 'code', 'chem'], and these attributes ['class', 'colspan', 'rowspan', 'display', 'checked', 'type', 'border', 'value', 'style', 'href', 'alt', 'align', 'data-bbox', 'data-label'].

Guidelines:
* Inline math: Surround math with <math>...</math> tags. Math expressions should be rendered in KaTeX-compatible LaTeX. Use display for block math.
* Tables: Use colspan and rowspan attributes to match table structure.
* Formatting: Maintain consistent formatting with the image, including spacing, indentation, subscripts/superscripts, and special characters.
* Images: Include a description of any images in the alt attribute of an <img> tag. Do not fill out the src property. Describe in detail inside the div tag. Also convert charts to high fidelity data, and convert diagrams to mermaid.
* Forms: Mark checkboxes and radio buttons properly.
* Text: join lines together properly into paragraphs using <p>...</p> tags.  Use <br> tags for line breaks within paragraphs, but only when absolutely necessary to maintain meaning.
* Chemistry: Use <chem>...</chem> tags for chemical formulas with reactive SMILES.
* Lists: Preserve indents and proper list markers.
* Use the simplest possible HTML structure that accurately represents the content of the block.
* Make sure the text is accurate and easy for a human to read and interpret.  Reading order should be correct and natural."""
MODEL = value("VLLM_MODEL_NAME", "chandra")
DPI = value("IMAGE_DPI", 192)
MIN_PDF_IMAGE_DIM = value("MIN_PDF_IMAGE_DIM", 1024)
MAX_TOKENS = value("MAX_OUTPUT_TOKENS", 12384)
BBOX_SCALE = value("BBOX_SCALE", 1000)
TOP_P = (0.1, 0.95)
VISUAL_LABELS = {"Image", "Figure", "Diagram", "Chart"}
CONFIG = {
    "backend": "chandra",
    "adapter_version": 1,
    "image_dpi": DPI,
    "min_pdf_image_dim": MIN_PDF_IMAGE_DIM,
    "bbox_scale": BBOX_SCALE,
    "max_output_tokens": MAX_TOKENS,
}


def resize(image: Image.Image) -> Image.Image:
    width, height = image.size
    pixels = width * height
    minimum, maximum, grid = 1792 * 28, 3072 * 2048, 28
    scale = (min(max(pixels, minimum), maximum) / pixels) ** 0.5
    w, h = max(1, round(width * scale / grid)), max(1, round(height * scale / grid))
    while w * h * grid * grid > maximum:
        if w == 1:
            h -= 1
        elif h == 1 or abs((w - 1) / h - width / height) < abs(w / (h - 1) - width / height):
            w -= 1
        else:
            h -= 1
    size = (w * grid, h * grid)
    return image if size == image.size else image.resize(size, Image.Resampling.LANCZOS)


def repeat_tail(raw: str, trim: int = 0) -> bool:
    text = raw[:-trim] if trim else raw
    for size in range(1, min(250, len(text)) + 1):
        threshold = int(4 * (1 + 3.0 / size)) + 1
        if text.endswith(text[-size:] * threshold):
            return True
    return False


def has_repeat(raw: str) -> bool:
    if repeat_tail(raw):
        return True
    if len(raw) <= 50 or not repeat_tail(raw, 50):
        return False
    cell = re.search(r"<td(?:\s[^>]*)?>([01\s]+)$", raw[:-50])
    if cell and raw.rstrip().endswith("</div>") and len(re.findall(r"[01]", cell.group(1))) <= 256:
        return False
    return True


class _Markdown(MarkdownConverter):
    """Preserve OCR math, nested HTML tables, and legacy escaping semantics."""

    def convert_math(self, el, text, parent_tags):
        if el.get("display") == "block":
            return "\n$$" + text.strip() + "$$\n"
        return " $" + text.strip() + "$ "

    def convert_table(self, el, text, parent_tags):
        return "\n\n" + str(el) + "\n\n"

    def escape(self, text, parent_tags=None):
        return super().escape(text, parent_tags).replace("$", r"\$")

    def convert_a(self, el, text, parent_tags):
        text = re.sub(r"([\[\]()])", r"\\\1", self.escape(text))
        return super().convert_a(el, text, parent_tags)

    def process_text(self, el, parent_tags=None):
        text = str(el)
        if not el.find_parent("pre"):
            text = re.sub(r"[\t ]+", " ", text)
        if not el.find_parent(["pre", "code", "kbd", "samp", "math"]):
            text = self.escape(text)
        if el.parent.name == "li" and (not el.next_sibling or el.next_sibling.name in ["ul", "ol"]):
            text = text.rstrip()
        return text


def markdown(content: str, label: str) -> str:
    soup = BeautifulSoup(content, "html.parser")
    for image in soup.find_all("img"):
        if not image.get("src"):
            image.decompose()
    html = str(soup)
    if label == "Text" and not re.search("<.+>", html.strip()):
        html = "<p>" + html.strip() + "</p>"
    converter = _Markdown(
        heading_style="ATX",
        bullets="-",
        escape_misc=False,
        escape_underscores=True,
        escape_asterisks=True,
        sub_symbol="<sub>",
        sup_symbol="<sup>",
    )
    return converter.convert(html).strip()


def parse_page(raw: str, width: int, height: int) -> tuple[list[dict], list[dict]]:
    divs = BeautifulSoup(raw, "html.parser").find_all("div", recursive=False)
    if not divs:
        raise ValueError("model response has no top-level layout blocks")
    chunks, blocks = [], []
    for div in divs:
        label = div.get("data-label") or "block"
        if label == "Blank-Page":
            continue
        # Preserve historical raw chunk coordinates; invalid DocIR boxes stay null.
        try:
            box = [int(v) for v in div.get("data-bbox", "").split(" ")]
            if len(box) != 4:
                raise ValueError("bbox length")
        except ValueError:
            box = [0, 0, 1, 1]
        chunk_box = [
            max(0, int(box[0] * (width / BBOX_SCALE))),
            max(0, int(box[1] * (height / BBOX_SCALE))),
            min(width, int(box[2] * (width / BBOX_SCALE))),
            min(height, int(box[3] * (height / BBOX_SCALE))),
        ]
        bbox = None
        try:
            coords = [int(v) for v in div.get("data-bbox", "").split()]
            if len(coords) == 4 and 0 <= coords[0] < coords[2] <= BBOX_SCALE and 0 <= coords[1] < coords[3] <= BBOX_SCALE:
                candidate = [
                    int(coords[0] * width / BBOX_SCALE),
                    int(coords[1] * height / BBOX_SCALE),
                    int(coords[2] * width / BBOX_SCALE),
                    int(coords[3] * height / BBOX_SCALE),
                ]
                if candidate[0] < candidate[2] and candidate[1] < candidate[3]:
                    bbox = candidate
        except ValueError:
            pass
        content = BeautifulSoup(div.decode_contents(), "html.parser")
        for tag in content.find_all(attrs={"data-bbox": True}):
            del tag["data-bbox"]
        html = str(content)
        chunks.append({"bbox": chunk_box, "label": label, "content": html})
        block = {"kind": "text", "source_label": label, "bbox_px": bbox}
        if label == "Table":
            block.update(kind="table", html=html)
        else:
            plain = content.get_text("\n").strip()
            mermaid = re.search(r"(?:^|\n)\s*(?:graph|flowchart)\s+(?:TB|TD|BT|LR|RL)\b", plain, re.I)
            if mermaid:
                block.update(kind="diagram", diagram={"format": "mermaid", "code": plain[mermaid.start() :].strip()})
            elif label in VISUAL_LABELS:
                block.update(kind="visual", caption=None)
            else:
                block["markdown"] = markdown(html, label)
        blocks.append(block)
    return chunks, blocks
