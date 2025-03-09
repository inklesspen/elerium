# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import pathlib
from collections.abc import Sequence
from contextlib import AbstractContextManager, ExitStack, nullcontext

import pytest
from pytest import raises, warns
from ufoLib2.objects import Font, Point
from ufoLib2.objects.misc import BoundingBox

from elerium.util import GlyphWarning, equivalent_point, find_glyph_codepoints

TESTBORETO_PATH = pathlib.Path(__file__).parent / "data" / "ufo" / "Testboreto.ufo"


def test_equivalent_point():
    source_bb = BoundingBox(xMin=30, xMax=40, yMin=0, yMax=60)
    source_point = Point(x=25, y=30)  # five units to the left of the midpoint of the left side
    dest_bb = BoundingBox(xMin=30, xMax=60, yMin=0, yMax=60)

    expected = Point(x=15, y=30)  # the dest_bb is three times as wide, so… 15 units to the left
    assert expected == equivalent_point(source_point, source_bb, dest_bb)


def test_equivalent_point_cross_origin():
    source_bb = BoundingBox(xMin=30, xMax=40, yMin=0, yMax=60)
    source_point = Point(x=30, y=30)  # exactly at the midpoint of the left side
    dest_bb = BoundingBox(xMin=-30, xMax=60, yMin=-10, yMax=60)

    # should still be exactly at the midpoint of the left side
    expected = Point(x=-30, y=25)
    assert expected == equivalent_point(source_point, source_bb, dest_bb)


def test_equivalent_point_growing_and_shrinking():
    source_bb = BoundingBox(xMin=30, xMax=50, yMin=0, yMax=60)
    source_point = Point(x=35, y=45)
    dest_bb = BoundingBox(xMin=10, xMax=70, yMin=20, yMax=40)

    expected = Point(x=25, y=35)
    assert expected == equivalent_point(source_point, source_bb, dest_bb)


@pytest.fixture
def codepoint_testboreto():
    ufo = Font.open(TESTBORETO_PATH)
    # Add some extra values
    ufo.newGlyph("ABC")
    ufo.lib["public.postscriptNames"]["ABC"] = "uni004100420043"
    # For sanity's sake remove the second code in Lcommaaccent
    ufo["Lcommaaccent"].unicodes = [ufo["Lcommaaccent"].unicode]
    return ufo


@pytest.mark.parametrize(
    ["glyphname", "strict", "expected"],
    [
        ("zero", True, (0x0030,)),  # one codepoint assigned in glif
        ("A", True, (0x0041, 0x0061)),  # two codepoints assigned in glif
        ("zero.tf", True, (0x0030,)),  # no codepoints in glif, but falls back to 'zero'
        ("ABC", True, ((0x0041, 0x0042, 0x0043),)),
        # https://github.com/adobe-type-tools/agl-specification?tab=readme-ov-file#3-examples
        ("Lcommaaccent", False, (0x013B,)),  # single codepoint (see fixture above)
        ("uni20AC0308", False, ((0x20AC, 0x0308),)),  # ligature glyph with two codepoints
        ("u1040C.alternate", False, (0x1040C,)),  # variation glyph with a single codepoint
        ("Lcommaaccent_uni20AC0308_u1040C.alternate", False, ((0x013B, 0x20AC, 0x0308, 0x1040C),)),
        # Edge cases and errors
        (".notdef", True, raises(KeyError)),  # deliberately not assigned codepoints
        ("missingno", True, raises(ValueError)),  # not a known glyph
        ("missingno", False, [raises(KeyError), warns(GlyphWarning)]),  # not a known glyph
    ],
)
@pytest.mark.filterwarnings("ignore::elerium.warnings.GlyphWarning")
def test_find_glyph_codepoints(
    codepoint_testboreto: Font,
    glyphname: str,
    strict: bool,
    expected: tuple[int | tuple[int, ...], ...] | AbstractContextManager | Sequence[AbstractContextManager],
):
    if isinstance(expected, AbstractContextManager):
        guard = expected
    elif isinstance(expected, Sequence) and isinstance(expected[0], AbstractContextManager):
        guard = ExitStack()
        for cm in expected:
            guard.enter_context(cm)
    else:
        guard = nullcontext(expected)

    with guard as exp:
        actual = find_glyph_codepoints(codepoint_testboreto, glyphname, strict=strict)
        assert actual == exp
