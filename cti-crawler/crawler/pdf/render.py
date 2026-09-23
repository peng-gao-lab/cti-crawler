"""CPU work runs in separate processes. Only embedded data resources are permitted."""
import io
import base64
import logging
import re
import signal
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup

from ..shared.storage import FileStorage
from .markup import prepare_print, text_fragments


IMAGE_BOUNDS = ((210 - 2 * 16) * 96 / 25.4, 235 * 96 / 25.4)  # A4 print CSS below, px.
CSS = """
@page { size: A4; margin: 16mm; }
body { margin: 0; font-family: 'DejaVu Sans', 'Archived CJK', 'Archived Emoji', 'Archived Devanagari', 'Archived Myanmar', 'Droid Sans Fallback', sans-serif; font-size: 10pt; line-height: 1.45; }
* { overflow-wrap: anywhere; }
pre, code { white-space: pre-wrap; font-size: 9pt; }
img, svg { max-width: 100%; max-height: 235mm; object-fit: contain; }
table { width: 100%; table-layout: auto; border-collapse: collapse; font-size: 8pt; }
/* Size image columns within the page before resolving each image's max-width. */
table:has(img, svg) { table-layout: fixed; }
/* Only tables proven to overflow in the initial layout use this fallback. */
table[data-pdf-fixed-layout] { table-layout: fixed; }
td, th { border: 0.3pt solid #888; padding: 3pt; }
a { color: #174d86; text-decoration: underline; }
/* Permit wrapping when a link is embedded in an unspaced URL or code string. */
a::after { content: "\\200b"; }
details, summary, noscript { display: block; }
/* A button's text is report content here, not a fixed-size form control. */
button { white-space: pre-wrap; width: auto; height: auto; max-width: 100%; }
"""


def initialize_worker():
    # Parent handles terminal signals, stops scheduling, then joins active renders.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)


def normalized(text):
    # Formatting controls and presentation selectors have no independent printed glyph.
    # Retain combining marks (including non-Latin vowel signs) and all source content.
    # Canonical decomposition keeps a base letter and its mark comparable even when an
    # inline image or a box boundary separates them on one side only.
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not c.isspace() and unicodedata.category(c) != 'Cf'
                   and c not in {'\ufe0e', '\ufe0f'})


@lru_cache(maxsize=1)
def print_stylesheet():
    from weasyprint import CSS as Stylesheet
    from weasyprint.text.fonts import FontConfiguration
    from weasyprint.urls import URLFetcher

    directory = Path(__file__).resolve().parents[2] / 'fonts'
    faces = []
    for family, filename in [('Archived CJK', 'NotoSansCJKkr-Regular.otf'),
                             ('Archived Emoji', 'NotoEmoji.ttf'),
                             ('Archived Devanagari', 'NotoSansDevanagari-Regular.ttf'),
                             ('Archived Myanmar', 'NotoSansMyanmar-Regular.ttf')]:
        data = base64.b64encode((directory / filename).read_bytes()).decode('ascii')
        media = 'font/otf' if filename.endswith('.otf') else 'font/ttf'
        faces.append(f"@font-face {{ font-family: '{family}'; src: url(data:{media};base64,{data}); }}")
    config = FontConfiguration()
    sheet = Stylesheet(string='\n'.join(faces) + '\n' + CSS, font_config=config,
        url_fetcher=URLFetcher(allowed_protocols={'data'}, fail_on_errors=True))
    return sheet, config


def fit_overflowing_tables(source, document, stylesheet, font_config, semantics):
    """Retry wide tables once; ordinary tables keep their automatic column widths."""
    parents = {child: parent for parent in source.etree_element.iter() for child in parent}
    tables = set()
    for page in document.pages:
        for box in page._page_box.descendants():
            if not (getattr(box, 'text', None) or hasattr(box, 'replacement')):
                continue
            if box.position_x >= -1 and box.position_x + box.width <= page.width + 1:
                continue
            element = box.element
            while element is not None:
                if element.tag == 'table':
                    tables.add(element)
                    break
                element = parents.get(element)
    semantics['tables_with_fixed_layout'] = len(tables)
    if tables:
        for table in tables:
            table.set('data-pdf-fixed-layout', '')
        document = source.render(stylesheets=[stylesheet], font_config=font_config)
    return document


class RenderMessages(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.messages = []
        self.failures = []

    def emit(self, record):
        message = record.getMessage()
        self.messages.append(message)
        # Only known anchor/decorative CSS warnings are non-fatal. Missing glyphs,
        # resource errors and unrecognized warnings still require attention.
        # SVG presentation properties written as inline style are reported by the CSS
        # validator but still applied by WeasyPrint's SVG renderer; blend modes are
        # unsupported visual effects, dropped on HTML elements by archiving already.
        decorative = re.match(r"Ignored `(fill|fill-rule|fill-opacity|clip-rule|clip-path|stroke|stroke-width|stroke-opacity"
                              r"|stroke-linecap|stroke-linejoin|stroke-miterlimit|stroke-dasharray|stroke-dashoffset"
                              r"|mix-blend-mode|enable-background|background-color):", message)
        harmless = message.startswith('Anchor defined twice:') or decorative
        if record.levelno >= logging.ERROR or not harmless:
            self.failures.append(message)


def convert(archive_path: str, destination: str):
    # Lazy imports keep the crawler and archive-only mode independent of PDF packages.
    from weasyprint import HTML
    from weasyprint.urls import URLFetcher, FatalURLFetchingError
    from pypdf import PdfReader
    from PIL import Image, UnidentifiedImageError
    from urllib.request import urlopen
    from xml.etree import ElementTree

    html = Path(archive_path).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    semantics = prepare_print(soup, IMAGE_BOUNDS)
    body = soup.body
    layout_text = defaultdict(list)
    animations = []
    missing_images = []
    for image_index, image in enumerate(body.select("img")):
        if not image["src"].startswith("data:image/"):
            raise ValueError("Archive contains a non-embedded image")
        # Animated images print their first frame; the loss of animation is recorded.
        if image["src"].startswith("data:image/svg+xml"):
            with urlopen(image['src']) as resource:
                try:
                    tree = ElementTree.fromstring(resource.read())
                    if tree.tag not in {'svg', '{http://www.w3.org/2000/svg}svg'}:
                        raise ValueError('Embedded SVG has no SVG root')
                except (ElementTree.ParseError, ValueError) as error:
                    missing_images.append({'image_index': image_index, 'alt': image.get('alt', ''),
                                           'reason': f'Invalid embedded SVG: {error}'})
                    placeholder = soup.new_tag('span')
                    placeholder.string = '[Image unavailable' + (': ' + image['alt'] if image.get('alt') else '') + ']'
                    image.replace_with(placeholder)
        else:
            with urlopen(image["src"]) as resource:
                try:
                    with Image.open(io.BytesIO(resource.read())) as picture:
                        if getattr(picture, "n_frames", 1) > 1:
                            frames = picture.n_frames
                            picture.seek(0)
                            frame = picture.convert("RGBA")
                            buffer = io.BytesIO()
                            frame.save(buffer, format="PNG")
                            image["src"] = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
                            animations.append({"image_index": image_index, "frames": frames, "selected_frame": 0})
                            continue
                        picture.verify()
                        # Same rule as explicitly sized images: a picture that will fill
                        # the line cannot share it with a caption glued by a no-break space.
                        if (not image.has_attr('width') and picture.width >= IMAGE_BOUNDS[0] - 1):
                            image['style'] = image.get('style', '') + ';display:block'
                            semantics['full_width_images_as_blocks'] += 1
                except UnidentifiedImageError as error:
                    raise ValueError("Invalid archived image") from error
    handler = RenderMessages()
    logger = logging.getLogger("weasyprint")
    logger.addHandler(handler)
    try:
        source = HTML(string=str(soup), url_fetcher=URLFetcher(
            allowed_protocols={"data"}, fail_on_errors=True,
        ))
        # Use the renderer's HTML5 tree directly. Re-parsing malformed nesting after
        # assigning IDs can move text to different parents and create false failures.
        body_tree = source.etree_element.find('body')
        for number, element in enumerate(body_tree.iter()):
            if not isinstance(element.tag, str):
                continue
            key = str(number)
            element.set('data-pdf-check', key)
        expected, semantics['svg_nonvisual_text_nodes'] = text_fragments(body_tree)
        expected = [(key, text) for key, text in expected if normalized(text)]
        stylesheet, font_config = print_stylesheet()
        document = source.render(stylesheets=[stylesheet], font_config=font_config)
        document = fit_overflowing_tables(source, document, stylesheet, font_config, semantics)
        # Text extraction alone can include text painted outside the physical page.
        # This layout-tree check is intentionally tied to the pinned WeasyPrint 69 API.
        for number, page in enumerate(document.pages, 1):
            for box in page._page_box.descendants():
                if not (getattr(box, "text", None) or hasattr(box, "replacement")):
                    continue
                if getattr(box, "text", None) and box.element is not None:
                    text = box.text
                    # A line broken at a soft hyphen carries the renderer's inserted hyphen.
                    hyphen = box.style['hyphenate_character']
                    if hyphen and text.endswith('\u00ad' + hyphen):
                        text = text[:-len(hyphen)]
                    layout_text[box.element.get("data-pdf-check")].append(text)
                x, y = box.position_x, box.position_y
                if x < -1 or y < -1 or x + box.width > page.width + 1 or y + box.height > page.height + 1:
                    raise ValueError(f"Content extends beyond PDF page {number}; layout needs review")
        pdf = document.write_pdf()
    except FatalURLFetchingError as error:
        # WeasyPrint derives this document-specific error from BaseException.
        # Normalize it before crossing the process boundary so the pipeline can
        # record one failed article and continue; do not catch interrupts/exits.
        raise ValueError(f"PDF resource could not be embedded: {error}") from error
    finally:
        logger.removeHandler(handler)
    if handler.failures:
        raise ValueError("PDF renderer warnings: " + "; ".join(handler.failures[:10]))
    reader = PdfReader(io.BytesIO(pdf))
    actual = normalized("\n".join(page.extract_text() or "" for page in reader.pages))
    extraction_mode = 'plain'
    expected_characters = Counter(normalized(''.join(text for _, text in expected)))
    if expected_characters - Counter(actual):
        # pypdf's default bidi handling can omit characters at script boundaries.
        # Accept the alternative only if it satisfies the same complete check.
        alternative = normalized("\n".join(
            page.extract_text(extraction_mode='layout') or '' for page in reader.pages))
        if not expected_characters - Counter(alternative):
            actual = alternative
            extraction_mode = 'layout'
    laid_out = {key: normalized("".join(parts)) for key, parts in layout_text.items()}
    missing = [text for key, text in expected
               if normalized(text) not in (actual if key is None else laid_out.get(key, ""))]
    if missing:
        raise ValueError(f"PDF text check failed ({len(missing)} fragments): {missing[0][:160]}")
    if not reader.pages or not actual:
        raise ValueError("PDF contains no searchable text")
    missing_characters = expected_characters - Counter(actual)
    details = ', '.join(f'U+{ord(char):04X} x{count}'
                        for char, count in list(missing_characters.items())[:10])
    text_layer_issues = []
    if missing_characters:
        # Every fragment was laid out and no glyph was missing, so the page shows the text.
        # WeasyPrint maps each glyph to the text between consecutive cluster positions;
        # a mark that shares a cluster with its base (Myanmar medials, reordered vowel
        # signs) therefore gets no Unicode entry and disappears from copy/search only.
        # That documented text-layer defect is accepted; a missing letter is not.
        if not all(unicodedata.category(char) in {'Mn', 'Mc'} for char in missing_characters):
            raise ValueError(f"PDF text character counts are incomplete: {details}")
        affected = sorted({text for _, text in expected
                           if any(char in normalized(text) for char in missing_characters)})
        text_layer_issues.append({
            'kind': 'combining_marks_missing_from_text_layer',
            'characters': {f'U+{ord(char):04X}': count for char, count in missing_characters.items()},
            'affected_text': affected[:10],
            'basis': 'All text fragments are present in the laid-out pages and no missing-glyph '
                     'warning occurred; only dependent marks that share a glyph cluster with their '
                     'base letter are absent from the extractable text layer. The HTML original '
                     'keeps the exact text.'})
    path = Path(destination)
    FileStorage(path.parent).write(path.name, pdf)
    return {"pages": len(reader.pages), "text_fragments_checked": len(expected),
            "text_extraction_mode": extraction_mode, "text_layer_issues": text_layer_issues,
            "images_checked": len(body.select('img')), "bytes": len(pdf),
            "animations_flattened": animations,
            "renderer_warnings": handler.messages,
            "print_semantics": semantics, "missing_images": missing_images,
            "check_scope": "static_html_text_and_embedded_images; dynamic content and original site appearance are not certified"}
