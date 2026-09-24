#!/usr/bin/env python3
"""Generate the offline picker catalogue from checksum-pinned Unicode 17 and CLDR 48 data."""
import ctypes as C
import hashlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ElementTree

SOURCES = {
    'emoji-test.txt': '1d8a944f88d7952f7ef7c5167fef3c67995bcae24543949710231b03a201acda',
    'UnicodeData.txt': '2e1efc1dcb59c575eedf5ccae60f95229f706ee6d031835247d843c11d96470c',
    'en.xml': '8511aadd046fdba2f0ffe590266ced8bbf48175ad139b2675d85d7141057b235',
}
ROOT = Path(__file__).resolve().parent.parent


def function(library, name, result, *arguments):
    fn = getattr(library, name)
    fn.restype = result
    fn.argtypes = arguments
    return fn


def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: update-characters.py DIRECTORY_WITH_UNICODE_17_DATA')
    sources = {}
    for name, digest in SOURCES.items():
        data = (Path(sys.argv[1]) / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            sys.exit(f'{name}: Unicode 17 checksum mismatch')
        sources[name] = data.decode('utf-8')

    # CLDR keywords let searches such as "smile" or "happy" find 😀.
    keywords = {}
    for node in ElementTree.fromstring(sources['en.xml'].encode()).iter('annotation'):
        if node.get('type') != 'tts':
            keywords[node.get('cp')] = node.text.split(' | ')

    pango = C.CDLL('libpango-1.0.so.0')
    cairo = C.CDLL('libpangocairo-1.0.so.0')
    gobject = C.CDLL('libgobject-2.0.so.0')
    pointer = C.c_void_p
    fontmap = function(cairo, 'pango_cairo_font_map_get_default', pointer)()
    context = function(pango, 'pango_font_map_create_context', pointer, pointer)(fontmap)
    layout = function(pango, 'pango_layout_new', pointer, pointer)(context)
    font = function(pango, 'pango_font_description_from_string', pointer, C.c_char_p)(b'Noto Sans 16')
    function(pango, 'pango_layout_set_font_description', None, pointer, pointer)(layout, font)
    set_text = function(pango, 'pango_layout_set_text', None, pointer, C.c_char_p, C.c_int)
    unknown = function(pango, 'pango_layout_get_unknown_glyphs_count', C.c_int, pointer)
    unref = function(gobject, 'g_object_unref', None, pointer)
    rows = {}
    named = {}
    skipped = 0

    def add(glyph, description):
        nonlocal skipped
        if glyph in rows:
            return
        # Use the same shaping and font fallback as tofi, including sequences.
        set_text(layout, glyph.encode('utf-8'), -1)
        if unknown(layout):
            skipped += 1
            return
        # CLDR lists emoji without variation selectors or skin tones. Other
        # sequences, such as 🫱🏻‍🫲🏿, use the emoji named before the colon (🤝).
        base = ''.join(c for c in glyph if c != '\ufe0f' and not '\U0001F3FB' <= c <= '\U0001F3FF')
        words = keywords.get(base) or named.get(description.split(':')[0], ())
        named.setdefault(description, words)
        extra = ', '.join(w for w in words if w.lower() not in description.lower())
        rows[glyph] = f'{description} · {extra}' if extra else description

    try:
        for line in sources['emoji-test.txt'].splitlines():
            if not line or line.startswith('#'):
                continue
            points, rest = line.split(';', 1)
            status, comment = rest.split('#', 1)
            if status.strip() != 'fully-qualified':
                continue
            glyph = ''.join(chr(int(point, 16)) for point in points.split())
            description = comment.strip().split(' ', 2)[2]
            add(glyph, 'emoji ' + description)

        for line in sources['UnicodeData.txt'].splitlines():
            fields = line.split(';')
            point, name, category = int(fields[0], 16), fields[1], fields[2]
            if point <= 0x20 or name.startswith('<'):
                continue
            letters = (0xA1 <= point <= 0x52F or 0x1E00 <= point <= 0x1FFF)
            decomposition = fields[5].split()
            if len(decomposition) == 2 and decomposition[0].startswith('<'):
                # Include styled letters such as 𝛅, ᵟ, ℝ and ｍ.
                base = int(decomposition[1], 16)
                letters = letters or base <= 0x52F or 0x1E00 <= base <= 0x1FFF
            if category[0] in 'PSN' or (letters and category[0] == 'L'):
                add(chr(point), f'{name.lower()} U+{point:04X}')
    finally:
        function(pango, 'pango_font_description_free', None, pointer)(font)
        unref(layout)
        unref(context)

    output = ROOT / 'home/.local/share/tofi/characters.txt'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(''.join(f'{glyph}\t{name}\n' for glyph, name in rows.items()), encoding='utf-8')
    print(f'{len(rows)} characters/sequences; {skipped} unsupported entries omitted')


if __name__ == '__main__':
    main()
