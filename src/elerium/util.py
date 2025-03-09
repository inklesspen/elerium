# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import io
import pathlib
import warnings

from fontTools import agl
from fontTools.feaLib.parser import Parser as FeaParser
from fontTools.misc.transform import Transform
from fontTools.ufoLib import FEATURES_FILENAME
from ufoLib2.objects import Font, Point
from ufoLib2.objects.misc import BoundingBox

from .warnings import GlyphWarning


def equivalent_point(source_point: Point, source_bb: BoundingBox, dest_bb: BoundingBox):
    """Given a source bounding box, and a point relative to that box, compute an "equivalent" point relative to a destination bounding box."""
    source_width = source_bb.xMax - source_bb.xMin
    source_height = source_bb.yMax - source_bb.yMin
    dest_width = dest_bb.xMax - dest_bb.xMin
    dest_height = dest_bb.yMax - dest_bb.yMin

    affine = (
        Transform()  # These have to be in what seems like the reverse order, because of how matrix multiplication works.
        .translate(x=dest_bb.xMin, y=dest_bb.yMin)
        .scale(x=(dest_width / source_width), y=(dest_height / source_height))
        .translate(x=-source_bb.xMin, y=-source_bb.yMin)
    )
    dest_x, dest_y = affine.transformPoint((source_point.x, source_point.y))
    return Point(x=int(dest_x), y=int(dest_y))


def _find_glyph_codepoints(ufo: Font, glyphname: str) -> tuple[int | tuple[int, ...], ...]:
    # This is multiple codepoints for the same glyph
    if glyphname in ufo and ufo[glyphname].unicodes:
        return tuple(ufo[glyphname].unicodes)
    unistr = agl.toUnicode(glyphname)
    # this is potentially a ligature: should be list[list[str]] in that case
    if len(unistr) > 1:
        return (tuple(ord(c) for c in unistr),)
    if len(unistr) == 1:
        return (ord(unistr),)
    if glyphname in ufo.lib["public.postscriptNames"]:
        return _find_glyph_codepoints(ufo, ufo.lib["public.postscriptNames"][glyphname])
    if "." in glyphname:
        baseglyphname, _, _ = glyphname.partition(".")
        if baseglyphname in ufo:
            return _find_glyph_codepoints(ufo, baseglyphname)
    raise KeyError(f"Cannot find codepoints for {glyphname!r}")


def find_glyph_codepoints(ufo: Font, glyphname: str, strict: bool = True):
    """
    Try finding the Unicode codepoint(s) associated with a glyph.

    Will return either a tuple of ints, or a tuple of tuples of ints.

    Raises KeyError if it cannot find any codepoints. Note that a glyph might still be typeable in this case if there's a GSUB rule which produces it.
    """
    if glyphname not in ufo:
        if strict:
            raise ValueError(f"Glyph {glyphname!r} not in font!")
        warnings.warn(f"Asked to find codepoints for {glyphname!r}, but this glyph is not in the font.", GlyphWarning, stacklevel=2)
    return _find_glyph_codepoints(ufo, glyphname)


def parse_ufo_features(ufo: Font):
    if not ufo.features:
        return None
    glyphs = list(ufo.keys())
    if ufo.path:
        with pathlib.Path(ufo.path).joinpath(FEATURES_FILENAME).open("r") as fea_file:
            parser = FeaParser(fea_file, glyphs)
            return parser.parse()
    parser = FeaParser(io.StringIO(ufo.features.text), glyphs, followIncludes=False)
    return parser.parse()
