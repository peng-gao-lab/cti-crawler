"""HTML/SVG print semantics shared by new and retained offline archives."""
import re
import math
import unicodedata

from bs4 import Comment, NavigableString, Tag
from tinycss2 import parse_component_value_list, parse_declaration_list, parse_stylesheet, serialize


POSITIONING_PROPERTIES = {'position', 'top', 'left', 'right', 'bottom', 'inset', 'z-index'}
# Inline phrasing elements; a run joined to one of them without any space cannot wrap
# across the box boundary in WeasyPrint even with overflow-wrap.
PHRASING_ELEMENTS = {'a', 'abbr', 'b', 'cite', 'code', 'dfn', 'em', 'i', 'kbd', 'mark', 'q',
                     's', 'samp', 'small', 'span', 'strong', 'time', 'u', 'var'}
HTML_BREAKABLE = set(' \t\n\r\f\u200b')


def fixed_length(value, html_attribute=False):
    """Resolve only explicit absolute lengths; relative CSS needs the original layout."""
    tokens = parse_component_value_list(str(value), skip_comments=True)
    tokens = [t for t in tokens if t.type != 'whitespace']
    if len(tokens) != 1:
        return None
    token = tokens[0]
    units = {'px': 1, 'in': 96, 'cm': 96 / 2.54, 'mm': 96 / 25.4,
             'q': 96 / 101.6, 'pt': 96 / 72, 'pc': 16}
    if token.type == 'dimension' and token.lower_unit in units:
        result = token.value * units[token.lower_unit]
    elif token.type == 'number' and (html_attribute or token.value == 0):
        result = token.value
    else:
        return None
    return result if math.isfinite(result) and result >= 0 else None


def preserve_image_size(tag):
    """Keep fixed inline dimensions while removing their original CSS declarations."""
    dimensions = {key: fixed_length(tag[key], html_attribute=True)
                  for key in ('width', 'height') if tag.has_attr(key)}
    declarations = parse_declaration_list(tag.get('style', ''))
    priorities = {}
    for declaration in declarations:
        if declaration.type != 'declaration' or declaration.lower_name not in {'width', 'height'}:
            continue
        key = declaration.lower_name
        if priorities.get(key, False) and not declaration.important:
            continue
        priorities[key] = declaration.important
        # Relative/auto CSS overrides an HTML attribute too; do not invent a size.
        dimensions[key] = fixed_length(serialize(declaration.value))
    for key in ('width', 'height'):
        tag.attrs.pop(key, None)
        if dimensions.get(key) is not None:
            tag[key] = f'{dimensions[key]:.8g}'
    # SVG keeps drawing styles; img's other styles are removed by archive preparation.
    # Site positioning is not reproduced either: an SVG parked off-screen by the
    # publisher's layout must not escape the printed page.
    if tag.name == 'svg' and not any(d.type == 'error' for d in declarations):
        style = serialize([d for d in declarations if not (
            d.type == 'declaration' and (d.lower_name in POSITIONING_PROPERTIES or (
                d.lower_name in {'width', 'height'} and dimensions.get(d.lower_name) is not None)))])
        if style.strip():
            tag['style'] = style
        else:
            tag.attrs.pop('style', None)
    return {key: value for key, value in dimensions.items() if value is not None}


def background_urls(style):
    def urls(tokens):
        for token in tokens:
            if token.type == 'url':
                yield token.value
            elif token.type == 'function':
                if token.lower_name == 'url':
                    args = [a for a in token.arguments if a.type not in {'whitespace', 'comment'}]
                    if len(args) == 1 and args[0].type == 'string':
                        yield args[0].value
                else:
                    yield from urls(token.arguments)

    for declaration in parse_declaration_list(style, skip_comments=True, skip_whitespace=True):
        if declaration.type == 'declaration' and declaration.lower_name in {'background', 'background-image'}:
            yield from urls(declaration.value)


def canonical_colors(css, stylesheet=False):
    if 'currentcolor' not in css.lower():
        return css
    def visit(tokens):
        for token in tokens:
            if token.type == 'ident' and token.value.lower() == 'currentcolor':
                token.value = 'currentColor'
            for attribute in ('content', 'arguments'):
                if hasattr(token, attribute):
                    visit(getattr(token, attribute))
    nodes = parse_stylesheet(css) if stylesheet else parse_declaration_list(css)
    if any(node.type == 'error' for node in nodes):
        return css  # Leave malformed CSS to the renderer's existing error reporting.
    for node in nodes:
        if node.type == 'declaration':
            visit(node.value)
        elif node.type == 'qualified-rule':
            node.content = parse_component_value_list(canonical_colors(serialize(node.content)))
    return serialize(nodes)


def resolve_custom_properties(value):
    """Replace var() references by their declared fallback; None when a value cannot be resolved.

    The site's stylesheets are not reproduced, so a custom property has no definition here;
    the fallback is the author's own value for that case.
    """
    if 'var(' not in value.lower():
        return value
    tokens = parse_component_value_list(value, skip_comments=True)

    def expand(tokens):
        result = []
        for token in tokens:
            if token.type == 'function' and token.lower_name == 'var':
                arguments = token.arguments
                separators = [i for i, t in enumerate(arguments) if t.type == 'literal' and t.value == ',']
                if not separators:
                    raise LookupError(value)
                result.extend(expand(arguments[separators[0] + 1:]))
            elif token.type == 'function':
                token.arguments = expand(token.arguments)
                result.append(token)
            else:
                result.append(token)
        return result

    try:
        return serialize(expand(tokens)).strip()
    except LookupError:
        return None


def printable(text, replaced):
    """Map characters no archived font can draw to explicit substitutes, counting them.

    Control characters (other than HTML whitespace) and private-use code points have no
    glyph outside the publisher's own fonts. Whitespace-class controls become a space;
    everything else becomes U+FFFD so the loss stays visible in the PDF and its text layer.
    """
    if not any(unicodedata.category(c) in {'Cc', 'Co'} for c in text):
        return text
    out = []
    for c in text:
        category = unicodedata.category(c)
        if category == 'Cc' and c not in '\t\n\r\f':
            replaced[f'U+{ord(c):04X}'] = replaced.get(f'U+{ord(c):04X}', 0) + 1
            out.append(' ' if c.isspace() else '\ufffd')
        elif category == 'Co':
            replaced[f'U+{ord(c):04X}'] = replaced.get(f'U+{ord(c):04X}', 0) + 1
            out.append('\ufffd')
        else:
            out.append(c)
    return ''.join(out)


def prepare_print(soup, image_bounds):
    body = soup.body
    changes = {'selects_expanded': 0, 'hidden_inputs_omitted': [],
               'decorative_icons_omitted': [], 'line_separators': 0,
               'images_with_explicit_size': 0, 'images_scaled_to_page': 0,
               'full_width_images_as_blocks': 0, 'attachment_links_preserved': [],
               'head_titles_in_body_omitted': [], 'unprintable_characters_replaced': {},
               'inline_break_opportunities_added': 0, 'svg_custom_properties_resolved': 0,
               'svg_unresolved_attributes_dropped': {}, 'svg_self_referential_colors_removed': 0}
    # A <title> that a streaming page emitted inside <body> is document metadata: no
    # browser displays it and the PDF title carries it, so it is not report text.
    for title in body.find_all('title'):
        if title.find_parent('svg'):
            continue
        changes['head_titles_in_body_omitted'].append(title.get_text(strip=True))
        title.decompose()
    # Preserve visible links without asking the PDF writer to embed their targets.
    # Apply at render time too, so retained archives need not be downloaded again.
    for link in body.select('a[rel]'):
        relations = link.get('rel', [])
        if any(value.lower() == 'attachment' for value in relations):
            changes['attachment_links_preserved'].append(link.get('href', ''))
            remaining = [value for value in relations if value.lower() != 'attachment']
            if remaining:
                link['rel'] = remaining
            else:
                del link['rel']
    for image in body.select('img, svg'):
        if image.find_parent('svg'):
            continue  # Nested SVG dimensions belong to the drawing's coordinate system.
        dimensions = preserve_image_size(image)
        if not dimensions:
            continue
        changes['images_with_explicit_size'] += 1
        scale = min([1, *(limit / dimensions[key] for key, limit in
                          zip(('width', 'height'), image_bounds) if dimensions.get(key, 0) > 0)])
        changes['images_scaled_to_page'] += scale < 1
        style = image.get('style', '')
        for key, value in dimensions.items():
            value *= scale
            image[key] = f'{value:.8g}'
            style += f';{key}:{value:.8g}px'
        # A full-line image cannot share its line with a following caption, even
        # when a publisher joins them with a non-breaking space.
        if image.name == 'img' and dimensions.get('width', 0) * scale >= image_bounds[0] - 1:
            style += ';display:block'
            changes['full_width_images_as_blocks'] += 1
        image['style'] = style
    for field in body.select('input[type="hidden" i]'):
        changes['hidden_inputs_omitted'].append({'name': field.get('name')})
        field.decompose()
    for select in body.select('select'):
        changes['selects_expanded'] += 1
        select.name = 'div'
        for group in select.select('optgroup'):
            group.name = 'div'
            if group.get('label'):
                label = soup.new_tag('p')
                label.string = group['label']
                group.insert(0, label)
        for option in select.select('option'):
            option.name = 'p'
            if not option.get_text() and option.get('label'):
                option.string = option['label']
            if option.has_attr('selected'):
                option.append(' [selected]')
    # Only explicitly decorative, text-only private-use glyphs are omitted.
    # aria-hidden by itself is never sufficient to discard ordinary text or graphics.
    for tag in body.find_all(True):
        text = tag.get_text(strip=True)
        if (text and not tag.find(True)
                and all(unicodedata.category(c) == 'Co' for c in text)
                and any(str(p.get('aria-hidden', '')).lower() == 'true'
                        for p in [tag, *tag.parents])):
            changes['decorative_icons_omitted'].append([f'U+{ord(c):04X}' for c in text])
            tag.string = '[Decorative icon omitted]'
    replaced = changes['unprintable_characters_replaced']
    for node in list(body.find_all(string=True)):
        if isinstance(node, Comment) or node.parent.name in {'style', 'script'}:
            continue
        text = printable(str(node), replaced)
        if text != str(node):
            node.replace_with(text)
    for field in body.select('input[value]'):  # printed through the UA's content: attr(value)
        field['value'] = printable(field['value'], replaced)
    # A phrasing element glued to the preceding text (",&nbsp;<em>", "\u201c,\u201d<em>", an
    # image followed by a non-breaking space) forms one unbreakable run across boxes;
    # a zero-width space at that join lets the line wrap there when it must.
    for element in body.find_all(PHRASING_ELEMENTS):
        if element.find_parent('svg'):
            continue
        # A following text node can also become an unbreakable run, even when
        # it begins with a space. Keep its text and allow wrapping at the join.
        following = element.next_sibling
        if (isinstance(following, NavigableString) and not isinstance(following, Comment)
                and following.strip() and not following.startswith('\u200b')):
            element.insert_after(NavigableString('\u200b'))
            changes['inline_break_opportunities_added'] += 1
        previous = element.previous_sibling
        if previous is None or isinstance(previous, Comment):
            continue
        before = previous.get_text() if isinstance(previous, Tag) else str(previous)
        after = element.get_text()
        if (before and before[-1] in HTML_BREAKABLE) or not after or after[0] in HTML_BREAKABLE:
            continue
        element.insert_before(NavigableString('\u200b'))
        changes['inline_break_opportunities_added'] += 1
    for node in list(body.find_all(string=True)):
        if isinstance(node, Comment) or node.parent.name in {'style', 'script'}:
            continue
        count = str(node).count('\u2028') + str(node).count('\u2029')
        if not count:
            continue
        changes['line_separators'] += count
        if node.find_parent('svg'):
            node.replace_with(str(node).replace('\u2028', '\n').replace('\u2029', '\n'))
        else:
            parts = re.split('[\u2028\u2029]', str(node))
            for i, part in enumerate(parts):
                if i:
                    node.insert_before(soup.new_tag('br'))
                node.insert_before(part)
            node.extract()
    for svg in body.select('svg'):
        for tag in [svg, *svg.find_all(True)]:
            for key, value in list(tag.attrs.items()):
                if not isinstance(value, str) or key == 'style':
                    continue
                if 'var(' in value.lower():
                    resolved = resolve_custom_properties(value)
                    if resolved is None:
                        dropped = changes['svg_unresolved_attributes_dropped']
                        dropped[key] = dropped.get(key, 0) + 1
                        del tag[key]
                        continue
                    tag[key] = resolved
                    changes['svg_custom_properties_resolved'] += 1
            # color="currentColor" refers to itself; the renderer must inherit instead.
            if str(tag.get('color', '')).lower() == 'currentcolor':
                del tag['color']
                changes['svg_self_referential_colors_removed'] += 1
            for key in ('color', 'fill', 'stroke', 'stop-color', 'flood-color', 'lighting-color'):
                value = tag.get(key)
                if isinstance(value, str) and value.lower() == 'currentcolor':
                    tag[key] = 'currentColor'
            if tag.get('style'):
                declarations = parse_declaration_list(tag['style'])
                if not any(d.type == 'error' for d in declarations):
                    kept = []
                    for declaration in declarations:
                        if declaration.type != 'declaration':
                            kept.append(declaration)
                            continue
                        value = serialize(declaration.value)
                        if declaration.lower_name == 'color' and value.strip().lower() == 'currentcolor':
                            changes['svg_self_referential_colors_removed'] += 1
                            continue
                        if 'var(' in value.lower():
                            resolved = resolve_custom_properties(value)
                            if resolved is None:
                                dropped = changes['svg_unresolved_attributes_dropped']
                                dropped[declaration.lower_name] = dropped.get(declaration.lower_name, 0) + 1
                                continue
                            declaration.value = parse_component_value_list(resolved)
                            changes['svg_custom_properties_resolved'] += 1
                        kept.append(declaration)
                    tag['style'] = serialize(kept)
                tag['style'] = canonical_colors(tag['style'])
            if tag.name == 'style':
                tag.string = canonical_colors(tag.get_text(), stylesheet=True)
    return changes


def text_fragments(body):
    """Use HTML layout IDs, but check SVG text through searchable PDF text."""
    svg_prefix = '{http://www.w3.org/2000/svg}'
    nonvisual = {'title', 'desc', 'style', 'metadata', 'defs', 'symbol',
                 'clipPath', 'mask', 'pattern', 'marker'}
    expected = []
    ignored = 0

    def walk(element, in_svg_text=False, excluded=False):
        nonlocal ignored
        if not isinstance(element.tag, str):
            return
        svg = element.tag.startswith(svg_prefix)
        name = element.tag.removeprefix(svg_prefix)
        excluded = excluded or (svg and name in nonvisual)
        in_svg_text = svg and (in_svg_text or name in {'text', 'tspan', 'textPath'})
        key = None if svg else element.get('data-pdf-check')
        for text in [element.text, *(child.tail for child in element)]:
            if text and text.strip():
                if excluded or (svg and not in_svg_text):
                    ignored += 1
                else:
                    expected.append((key, text.strip()))
        for child in element:
            walk(child, in_svg_text, excluded)

    walk(body)
    return expected, ignored
