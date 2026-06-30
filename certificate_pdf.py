"""Shared certificate template parsing and PDF generation."""
import base64
import io
import os

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    fitz = None
    HAS_PYMUPDF = False

DISPLAY_WIDTH = 900
DEFAULT_TEMPLATE = os.path.join(os.path.dirname(__file__), "certificates", "TXCOAN.pdf")


def detect_alignment(bbox, page_width):
    x0, _, x1, _ = bbox
    center_x = (x0 + x1) / 2
    page_center = page_width / 2
    if x0 < 130:
        return "left"
    if x1 > page_width - 130:
        return "right"
    if abs(center_x - page_center) < 100:
        return "center"
    return "left"


def merge_spans(spans):
    if not spans:
        return []
    spans = sorted(spans, key=lambda s: (round(s["bbox"][1], 1), s["bbox"][0]))
    merged = []
    current = None
    for span in spans:
        text = span["text"].strip()
        if not text:
            continue
        if current is None:
            current = dict(span)
            current["text"] = text
            continue
        cb = current["bbox"]
        sb = span["bbox"]
        same_line = abs(cb[1] - sb[1]) < 8
        adjacent = sb[0] - cb[2] < 20
        if same_line and adjacent:
            current["text"] = current["text"] + span["text"]
            current["bbox"] = [cb[0], min(cb[1], sb[1]), sb[2], max(cb[3], sb[3])]
            current["origin"] = current.get("origin", [cb[0], cb[3]])
        else:
            merged.append(current)
            current = dict(span)
            current["text"] = text
    if current:
        merged.append(current)
    return merged


def merge_stacked_left_areas(fields):
    if not fields:
        return fields
    merged = []
    skip = set()
    for i, field in enumerate(fields):
        if i in skip:
            continue
        if field["alignment"] != "left":
            merged.append(field)
            continue
        combined = dict(field)
        j = i + 1
        while j < len(fields):
            nxt = fields[j]
            if nxt["alignment"] != "left":
                break
            if abs(nxt["bbox"][0] - combined["bbox"][0]) > 8:
                break
            gap = nxt["bbox"][1] - combined["bbox"][3]
            if gap < 0 or gap > 22:
                break
            combined["text"] = combined["text"] + nxt["text"]
            combined["editedText"] = combined["editedText"] + nxt["editedText"]
            combined["bbox"] = [
                combined["bbox"][0],
                combined["bbox"][1],
                max(combined["bbox"][2], nxt["bbox"][2]),
                nxt["bbox"][3],
            ]
            skip.add(j)
            j += 1
        merged.append(combined)
    return merged


def extract_fields(page):
    text_dict = page.get_text("dict")
    raw_spans = []
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                bbox = list(span["bbox"])
                origin = list(span.get("origin", [bbox[0], bbox[3]]))
                raw_spans.append({
                    "bbox": bbox,
                    "origin": origin,
                    "text": text,
                    "font": span.get("font", "Helvetica"),
                    "size": span.get("size", 12),
                })

    page_width = page.rect.width
    fields = []
    for idx, span in enumerate(merge_spans(raw_spans)):
        fields.append({
            "id": idx,
            "text": span["text"],
            "editedText": span["text"],
            "bbox": span["bbox"],
            "originalBbox": list(span["bbox"]),
            "origin": span["origin"],
            "font": span["font"],
            "fontSize": span["size"],
            "alignment": detect_alignment(span["bbox"], page_width),
            "edited": False,
        })
    fields.sort(key=lambda f: (round(f["bbox"][1], 1), f["bbox"][0]))
    fields = merge_stacked_left_areas(fields)
    for i, field in enumerate(fields):
        field["id"] = i
    return fields


def resolve_pdf_font(font_name):
    name = (font_name or "").lower()
    if "bold" in name:
        return "hebo"
    if "italic" in name or "oblique" in name:
        return "heit"
    return "helv"


def pdf_text_position(field):
    fontname = resolve_pdf_font(field.get("font"))
    fontsize = field.get("fontSize") or 12
    text = field.get("editedText") or ""
    bbox = field["bbox"]
    origin_x, origin_y = field.get("origin", [bbox[0], bbox[3]])
    alignment = field.get("alignment", "left")

    if alignment == "center":
        text_width = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
        x = (bbox[0] + bbox[2] - text_width) / 2
    elif alignment == "right":
        text_width = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
        x = bbox[2] - text_width
    else:
        x = origin_x
    return x, origin_y, fontname, fontsize


def redact_rect_for_field(field):
    bbox = field["bbox"]
    original = field.get("originalBbox", bbox)
    x0 = min(bbox[0], original[0])
    y0 = min(bbox[1], original[1])
    x1 = max(bbox[2], original[2])
    y1 = max(bbox[3], original[3])
    return fitz.Rect(x0, y0, x1, y1)


def load_template_data(pdf_path=None, include_image=False):
    if not HAS_PYMUPDF:
        raise RuntimeError("PyMuPDF is required. Install with: pip install PyMuPDF")
    pdf_path = pdf_path or DEFAULT_TEMPLATE
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Template not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    page = doc[0]
    page_width = page.rect.width
    page_height = page.rect.height
    scale = DISPLAY_WIDTH / page_width
    fields = extract_fields(page)
    doc.close()

    data = {
        "templatePath": pdf_path,
        "templateName": os.path.basename(pdf_path),
        "pageWidth": page_width,
        "pageHeight": page_height,
        "displayWidth": DISPLAY_WIDTH,
        "displayHeight": page_height * scale,
        "scale": scale,
        "fields": fields,
    }
    if include_image:
        data["imageBase64"] = base64.b64encode(render_template_png(pdf_path)).decode("ascii")
    return data


def render_template_png(pdf_path=None):
    if not HAS_PYMUPDF:
        raise RuntimeError("PyMuPDF is required. Install with: pip install PyMuPDF")
    pdf_path = pdf_path or DEFAULT_TEMPLATE
    doc = fitz.open(pdf_path)
    page = doc[0]
    scale = DISPLAY_WIDTH / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def generate_certificate_pdf(template_path, fields, output_path):
    if not HAS_PYMUPDF:
        raise RuntimeError("PyMuPDF is required. Install with: pip install PyMuPDF")

    edited = [
        f for f in fields
        if f.get("edited") or (f.get("editedText", "").strip() != f.get("text", "").strip())
    ]

    doc = fitz.open(template_path)
    page = doc[0]

    for field in edited:
        page.add_redact_annot(redact_rect_for_field(field))
    if edited:
        page.apply_redactions()

    for field in edited:
        text = (field.get("editedText") or "").strip()
        if not text:
            continue
        x, y, fontname, fontsize = pdf_text_position(field)
        page.insert_text((x, y), text, fontname=fontname, fontsize=fontsize, color=(0, 0, 0))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return output_path
