# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import pathlib

from elerium.mti_parser import GdefParser, GlyphDefinitions

MTI_BASE_PATH = pathlib.Path(__file__).parent / "data" / "mti"


def mti_loader(example_name: str):
    return (MTI_BASE_PATH / example_name).with_suffix(".txt").read_text()


def test_gdef_classes():
    parser = GdefParser(mti_loader("gdefclasses"))

    expected = GlyphDefinitions(glyph_classes=(("A", "C"), ("fi", "fl"), ("breve", "acute"), ()))
    actual = parser.parse()

    assert expected == actual


def test_gdef_attachment_points():
    parser = GdefParser(mti_loader("gdefattach"))

    expected = GlyphDefinitions(attachment_points={"A": [5], "B": [0, 3, 9]})
    actual = parser.parse()

    assert expected == actual


def test_gdef_ligature_carets():
    parser = GdefParser(mti_loader("gdefligcaret"))

    expected = GlyphDefinitions(ligature_carets={"uniFB01": [236], "ffi": [210, 450]})
    actual = parser.parse()

    assert expected == actual


def test_gdef_mark_attachment_classes():
    parser = GdefParser(mti_loader("gdefmarkattach"))

    expected = GlyphDefinitions(mark_attachment_classes=(("breve", "grave"), ("commaacent", "dotbelow")))
    actual = parser.parse()

    assert expected == actual


def test_gdef_mark_filter_sets():
    parser = GdefParser(mti_loader("gdefmarkfilter"))

    expected = GlyphDefinitions(
        mark_filter_sets={1: {"breve", "acute", "dotabove"}, 2: {"dotbelow", "commaaccent", "cedilla"}, 3: {"dotabove", "dotbelow"}}
    )
    actual = parser.parse()

    assert expected == actual
