# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import pathlib

import fontTools.feaLib.ast as ast
import pytest
from more_itertools import flatten as flatten_list

from elerium.mti_parser import AnchorPoint, GposParser, Lookup, make_mark_class

DATA_BASE_PATH = pathlib.Path(__file__).parent / "data"


def data_loader(example_name: str):
    return (DATA_BASE_PATH / example_name).with_suffix(".txt").read_text()


def feaify(lookup: Lookup):
    lookup.statements = [s.asFea() for s in lookup.statements]
    return lookup


def param_ids(val):
    if isinstance(val, str):
        return val
    if isinstance(val, Lookup):
        return str(val.lookup_id).replace("-", "_")
    if isinstance(val, ast.MarkClass):
        return val.name
    return None


@pytest.mark.parametrize(
    ["mti_file", "expected"],
    [
        (
            "mti/gpossingle",
            Lookup(
                lookup_id="GPOS_supsToInferiors",
                statements=[
                    # 'pos [asuperior … egravesuperior] <0 -560 0 0>;'
                    ast.SinglePosStatement(
                        pos=[
                            (
                                ast.GlyphClass(
                                    [
                                        "asuperior",
                                        "bsuperior",
                                        "csuperior",
                                        "dsuperior",
                                        "esuperior",
                                        "fsuperior",
                                        "gsuperior",
                                        "hsuperior",
                                        "isuperior",
                                        "jsuperior",
                                        "ksuperior",
                                        "lsuperior",
                                        "msuperior",
                                        "nsuperior",
                                        "osuperior",
                                        "psuperior",
                                        "qsuperior",
                                        "rsuperior",
                                        "ssuperior",
                                        "tsuperior",
                                        "usuperior",
                                        "vsuperior",
                                        "wsuperior",
                                        "xsuperior",
                                        "ysuperior",
                                        "zsuperior",
                                        "periodsuperior",
                                        "commasuperior",
                                        "dollarsuperior",
                                        "centsuperior",
                                        "aesuperior",
                                        "oesuperior",
                                        "egravesuperior",
                                    ]
                                ),
                                ast.ValueRecord(yPlacement=-560),
                            )
                        ],
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    )
                ],
            ),
        ),
        (
            "multisinglepos",
            Lookup(
                lookup_id="GPOS_slashpos",
                statements=[
                    ast.SinglePosStatement(
                        pos=[(ast.GlyphName("fraction"), ast.ValueRecord(xPlacement=-10, xAdvance=-10))],
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    )
                ],
            ),
        ),
        (
            "mti/gpospairglyph",
            Lookup(
                lookup_id="GPOS_0",
                statements=list(
                    # These would all be easier to read if we could use GlyphClass here, but that's semantically different!!!
                    flatten_list(
                        [
                            [
                                ast.PairPosStatement(
                                    glyphs1=ast.GlyphName(left_glyph),
                                    valuerecord1=ast.ValueRecord(xAdvance=-50),
                                    glyphs2=ast.GlyphName("V"),
                                    valuerecord2=None,
                                )
                                for left_glyph in ["A", "Aacute", "Agrave", "Acircumflex"]
                            ],
                            [
                                ast.PairPosStatement(
                                    glyphs1=ast.GlyphName(left_glyph),
                                    valuerecord1=ast.ValueRecord(xAdvance=-10),
                                    glyphs2=ast.GlyphName("V"),
                                    valuerecord2=None,
                                )
                                for left_glyph in ["O", "Oacute", "Ograve", "Ocircumflex"]
                            ],
                            [
                                ast.PairPosStatement(
                                    glyphs1=ast.GlyphName("T"),
                                    valuerecord1=ast.ValueRecord(xAdvance=-35),
                                    glyphs2=ast.GlyphName(right_glyph),
                                    valuerecord2=None,
                                )
                                for right_glyph in ["a", "aacute", "agrave", "acircumflex"]
                            ],
                        ]
                    )
                ),
            ),
        ),
        (
            "mti/gpospairclass",
            Lookup(
                lookup_id="GPOS_0",
                statements=[
                    # pos [A Aacute Acircumflex Agrave] V -50;
                    ast.PairPosStatement(
                        glyphs1=ast.GlyphClass(["A", "Aacute", "Agrave", "Acircumflex"]),
                        valuerecord1=ast.ValueRecord(xAdvance=-50),
                        glyphs2=ast.GlyphName("V"),
                        valuerecord2=None,
                    ),
                    # pos [O Oacute Ocircumflex Ograve] V -10;
                    ast.PairPosStatement(
                        glyphs1=ast.GlyphClass(["O", "Oacute", "Ograve", "Ocircumflex"]),
                        valuerecord1=ast.ValueRecord(xAdvance=-10),
                        glyphs2=ast.GlyphName("V"),
                        valuerecord2=None,
                    ),
                    # pos T [a aacute acircumflex agrave] -35;
                    ast.PairPosStatement(
                        glyphs1=ast.GlyphName("T"),
                        valuerecord1=ast.ValueRecord(xAdvance=-35),
                        glyphs2=ast.GlyphClass(["a", "aacute", "agrave", "acircumflex"]),
                        valuerecord2=None,
                    ),
                ],
            ),
        ),
        (
            "mti/gposkernset",
            Lookup(
                lookup_id="GPOS_0",
                statements=[
                    # pos Acircumflex V -10;
                    ast.PairPosStatement(
                        glyphs1=ast.GlyphName("Acircumflex"),
                        valuerecord1=ast.ValueRecord(xAdvance=-10),
                        glyphs2=ast.GlyphName("V"),
                        valuerecord2=None,
                    ),
                    # pos T acircumflex -18;
                    ast.PairPosStatement(
                        glyphs1=ast.GlyphName("T"),
                        valuerecord1=ast.ValueRecord(xAdvance=-18),
                        glyphs2=ast.GlyphName("acircumflex"),
                        valuerecord2=None,
                    ),
                    # pos [A Aacute Acircumflex Agrave] V -50;
                    ast.PairPosStatement(
                        glyphs1=ast.GlyphClass(["A", "Aacute", "Agrave", "Acircumflex"]),
                        valuerecord1=ast.ValueRecord(xAdvance=-50),
                        glyphs2=ast.GlyphName("V"),
                        valuerecord2=None,
                    ),
                    # pos [O Oacute Ocircumflex Ograve] V -10;
                    ast.PairPosStatement(
                        glyphs1=ast.GlyphClass(["O", "Oacute", "Ograve", "Ocircumflex"]),
                        valuerecord1=ast.ValueRecord(xAdvance=-10),
                        glyphs2=ast.GlyphName("V"),
                        valuerecord2=None,
                    ),
                    # pos T [a aacute acircumflex agrave] -35;
                    ast.PairPosStatement(
                        glyphs1=ast.GlyphName("T"),
                        valuerecord1=ast.ValueRecord(xAdvance=-35),
                        glyphs2=ast.GlyphClass(["a", "aacute", "agrave", "acircumflex"]),
                        valuerecord2=None,
                    ),
                ],
            ),
        ),
        (
            "mti/gposcursive",
            Lookup(
                lookup_id="GPOS_kernpairs",
                statements=[
                    ast.CursivePosStatement(
                        ast.GlyphName("A"),
                        entryAnchor=ast.Anchor(560, 1466, contourpoint=1),
                        exitAnchor=ast.Anchor(769, 1466, contourpoint=2),
                    ),
                    ast.CursivePosStatement(
                        ast.GlyphName("B"),
                        entryAnchor=ast.Anchor(150, 1466, contourpoint=1),
                        exitAnchor=ast.Anchor(1186, 1091, contourpoint=6),
                    ),
                ],
            ),
        ),
        (
            "nototools/chainsub1",
            Lookup(
                lookup_id="GPOS_testLookupCtx",
                depends_on=["GPOS_testLookupSub"],
                statements=[
                    # pos b a' lookup testLookupSub c;
                    ast.ChainContextPosStatement(
                        glyphs=[ast.GlyphName("a")],
                        lookups=[[ast.LookupBlock(name="GPOS_testLookupSub")]],
                        prefix=[ast.GlyphName("b")],
                        suffix=[ast.GlyphName("c")],
                    )
                ],
            ),
        ),
        (
            "chainedclass",
            Lookup(
                lookup_id="GPOS_contrived",
                depends_on=["GPOS_somelookup", "GPOS_otherlookup"],
                statements=[
                    # pos z [a e]' [a e]' lookup GPOS_somelookup [one three five];
                    ast.ChainContextPosStatement(
                        glyphs=[ast.GlyphClass(glyphs=["a", "e"]), ast.GlyphClass(glyphs=["a", "e"])],
                        lookups=[None, [ast.LookupBlock(name="GPOS_somelookup")]],
                        prefix=[ast.GlyphName("z")],
                        suffix=[ast.GlyphClass(glyphs=["one", "three", "five"])],
                    ),
                    # pos y y [b c d f]' lookup GPOS_somelookup [a e]' [b c d f]' lookup GPOS_otherlookup [two four six];
                    ast.ChainContextPosStatement(
                        glyphs=[
                            ast.GlyphClass(glyphs=["b", "c", "d", "f"]),
                            ast.GlyphClass(glyphs=["a", "e"]),
                            ast.GlyphClass(glyphs=["b", "c", "d", "f"]),
                        ],
                        lookups=[[ast.LookupBlock(name="GPOS_somelookup")], None, [ast.LookupBlock(name="GPOS_otherlookup")]],
                        prefix=[ast.GlyphName("y"), ast.GlyphName("y")],
                        suffix=[ast.GlyphClass(glyphs=["two", "four", "six"])],
                    ),
                ],
            ),
        ),
        (
            "twobacktracks",
            Lookup(
                lookup_id="GPOS_twobacktracks",
                depends_on=["GPOS_sublookup"],
                statements=[
                    # pos [two four six] [one three five] [A B C D]' lookup GPOS_sublookup;
                    ast.ChainContextPosStatement(
                        glyphs=[ast.GlyphClass(["A", "B", "C", "D"])],
                        lookups=[[ast.LookupBlock(name="GPOS_sublookup")]],
                        prefix=[ast.GlyphClass(["two", "four", "six"]), ast.GlyphClass(["one", "three", "five"])],
                        suffix=[],
                    ),
                    # pos [x y z] [a c e] [seven eight nine]' lookup GPOS_sublookup;
                    ast.ChainContextPosStatement(
                        glyphs=[ast.GlyphClass(["seven", "eight", "nine"])],
                        lookups=[[ast.LookupBlock(name="GPOS_sublookup")]],
                        prefix=[ast.GlyphClass(["x", "y", "z"]), ast.GlyphClass(["a", "c", "e"])],
                        suffix=[],
                    ),
                ],
            ),
        ),
    ],
    ids=param_ids,
)
def test_pos_fragment(mti_file: str, expected: Lookup):
    parser = GposParser(data_loader(mti_file))

    parser.parse()
    assert len(parser.lookups) == 1
    actual = feaify(parser.lookups[0])
    expected = feaify(expected)
    assert actual == expected


@pytest.mark.parametrize(
    ["mti_file", "expected", "expected_mark_class"],
    [
        (
            "mti/gposmarktobase",
            Lookup(
                lookup_id="GPOS_topmarktobase-guru",
                statements=[
                    # pos base [ngagurmukhi nganuktagurmukhi] <anchor 816 1183 contourpoint 41> mark @GPOS_MC001;
                    ast.MarkBasePosStatement(
                        base=ast.GlyphClass(["ngagurmukhi", "nganuktagurmukhi"]),
                        marks=[(ast.Anchor(816, 1183, contourpoint=41), ast.MarkClass("GPOS_MC001"))],
                    ),
                    # pos base [tthagurmukhi tthanuktagurmukhi] <anchor 816 1183 contourpoint 30> mark @GPOS_MC001;
                    ast.MarkBasePosStatement(
                        base=ast.GlyphClass(["tthagurmukhi", "tthanuktagurmukhi"]),
                        marks=[(ast.Anchor(816, 1183, contourpoint=30), ast.MarkClass("GPOS_MC001"))],
                    ),
                    # pos base [nnagurmukhi nnanuktagurmukhi] <anchor 976 1183 contourpoint 35> mark @GPOS_MC001;
                    ast.MarkBasePosStatement(
                        base=ast.GlyphClass(["nnagurmukhi", "nnanuktagurmukhi"]),
                        marks=[(ast.Anchor(976, 1183, contourpoint=35), ast.MarkClass("GPOS_MC001"))],
                    ),
                    # pos base [nagurmukhi nanuktagurmukhi] <anchor 816 1183 contourpoint 32> mark @GPOS_MC001;
                    ast.MarkBasePosStatement(
                        base=ast.GlyphClass(["nagurmukhi", "nanuktagurmukhi"]),
                        marks=[(ast.Anchor(816, 1183, contourpoint=32), ast.MarkClass("GPOS_MC001"))],
                    ),
                    # pos base [lagurmukhi lanuktagurmukhi] <anchor 996 1183 contourpoint 46> mark @GPOS_MC001;
                    ast.MarkBasePosStatement(
                        base=ast.GlyphClass(["lagurmukhi", "lanuktagurmukhi"]),
                        marks=[(ast.Anchor(996, 1183, contourpoint=46), ast.MarkClass("GPOS_MC001"))],
                    ),
                ],
            ),
            make_mark_class(
                "GPOS_MC001",
                [
                    # markClass [bindigurmukhi] <anchor -184 1183 contourpoint 16> @GPOS_MC001;
                    (["bindigurmukhi"], AnchorPoint(-184, 1183, contour_point=16)),
                    # markClass [eematragurmukhi eematratippigurmukhi] <anchor -184 1183 contourpoint 15> @GPOS_MC001;
                    (["eematragurmukhi", "eematratippigurmukhi"], AnchorPoint(-184, 1183, contour_point=15)),
                    # markClass [aimatragurmukhi aimatratippigurmukhi] <anchor -184 1183 contourpoint 28> @GPOS_MC001;
                    (["aimatragurmukhi", "aimatratippigurmukhi"], AnchorPoint(-184, 1183, contour_point=28)),
                    # markClass [oomatragurmukhi oomatratippigurmukhi] <anchor -184 1183 contourpoint 20> @GPOS_MC001;
                    (["oomatragurmukhi", "oomatratippigurmukhi"], AnchorPoint(-184, 1183, contour_point=20)),
                    # markClass [aumatragurmukhi] <anchor -184 1183 contourpoint 38> @GPOS_MC001
                    (["aumatragurmukhi"], AnchorPoint(-184, 1183, contour_point=38)),
                    # markClass [eematrabindigurmukhi] <anchor -184 1183 contourpoint 27> @GPOS_MC001;
                    (["eematrabindigurmukhi"], AnchorPoint(-184, 1183, contour_point=27)),
                    # markClass [aimatrabindigurmukhi] <anchor -184 1183 contourpoint 40> @GPOS_MC001;
                    (["aimatrabindigurmukhi"], AnchorPoint(-184, 1183, contour_point=40)),
                    # markClass [oomatrabindigurmukhi] <anchor -184 1183 contourpoint 36> @GPOS_MC001;
                    (["oomatrabindigurmukhi"], AnchorPoint(-184, 1183, contour_point=36)),
                    # markClass [aumatrabindigurmukhi] <anchor -184 1183 contourpoint 54> @GPOS_MC001;
                    (["aumatrabindigurmukhi"], AnchorPoint(-184, 1183, contour_point=54)),
                ],
            ),
        ),
        (
            "mti/mark-to-ligature",
            Lookup(
                lookup_id="GPOS_LigMk0",
                statements=[
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamAlefFin.short"),
                        marks=[
                            [(ast.Anchor(1122, 1620, contourpoint=96), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(162, 1487, contourpoint=99), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamAlefFin.cup"),
                        marks=[
                            [(ast.Anchor(1122, 1620, contourpoint=105), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(162, 1487, contourpoint=106), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamAlefFin.cut"),
                        marks=[
                            [(ast.Anchor(1122, 1620, contourpoint=110), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(162, 1487, contourpoint=108), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("BehxIni_RehFin"),
                        marks=[
                            [(ast.Anchor(618, 813, contourpoint=59), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(282, 523, contourpoint=58), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("BehxIni_RehFin.b"),
                        marks=[
                            [(ast.Anchor(708, 813, contourpoint=65), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(282, 543, contourpoint=64), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("BehxIni_NoonGhunnaFin"),
                        marks=[
                            [(ast.Anchor(1205, 871, contourpoint=78), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(516, 565, contourpoint=74), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("BehxIni_MeemFin"),
                        marks=[
                            [(ast.Anchor(785, 1255, contourpoint=90), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(269, 952, contourpoint=93), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("HahIni_YehBarreeFin"),
                        marks=[
                            [(ast.Anchor(1017, 732, contourpoint=83), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(344, 743, contourpoint=86), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("AinMed_YehBarreeFin"),
                        marks=[
                            [(ast.Anchor(774, 860, contourpoint=105), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(312, 618, contourpoint=108), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("TahIni_YehBarreeFin"),
                        marks=[
                            [(ast.Anchor(1253, 1065, contourpoint=143), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(263, 419, contourpoint=142), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphClass(["BehxMed_NoonGhunnaFin", "BehxMed_NoonGhunnaFin.cup"]),
                        marks=[
                            [(ast.Anchor(1205, 1061, contourpoint=78), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(516, 755, contourpoint=74), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("KafMed_MeemFin"),
                        marks=[
                            [(ast.Anchor(238, 1435, contourpoint=182), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(84, 308, contourpoint=186), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamMed_MeemFin"),
                        marks=[
                            [(ast.Anchor(555, 1627, contourpoint=154), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(175, 472, contourpoint=155), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamMed_MeemFin.b"),
                        marks=[
                            [(ast.Anchor(555, 1627, contourpoint=156), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(175, 472, contourpoint=157), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamIni_MeemFin"),
                        marks=[
                            [(ast.Anchor(386, 1808, contourpoint=70), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(130, 701, contourpoint=150), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("AinIni.12m_MeemFin.02"),
                        marks=[
                            [(ast.Anchor(720, 1281, contourpoint=160), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(75, 631, contourpoint=158), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("KafMed.12_YehxFin.01"),
                        marks=[
                            [(ast.Anchor(807, 1457, contourpoint=106), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(440, 418, contourpoint=176), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamMed_YehxFin"),
                        marks=[
                            [(ast.Anchor(925, 1620, contourpoint=157), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(490, 196, contourpoint=152), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamMed_YehxFin.cup"),
                        marks=[
                            [(ast.Anchor(935, 1620, contourpoint=159), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(500, 196, contourpoint=155), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("FehxMed_YehBarreeFin"),
                        marks=[
                            [(ast.Anchor(397, 804, contourpoint=158), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(6, -65, contourpoint=161), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("KafIni_YehBarreeFin"),
                        marks=[
                            [(ast.Anchor(496, 1549, contourpoint=81), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(328, 339, contourpoint=171), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("KafMed_YehBarreeFin"),
                        marks=[
                            [(ast.Anchor(465, 1407, contourpoint=106), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(328, 251, contourpoint=197), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamIni_YehBarreeFin"),
                        marks=[
                            [(ast.Anchor(719, 1633, contourpoint=70), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(328, 339, contourpoint=160), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("AinIni_YehBarreeFin"),
                        marks=[
                            [(ast.Anchor(766, 1036, contourpoint=82), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(194, 312, contourpoint=151), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("BehxMed_YehxFin"),
                        marks=[
                            [(ast.Anchor(913, -285, contourpoint=117), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(1223, -305, contourpoint=112), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("BehxMed_MeemFin.py"),
                        marks=[
                            [(ast.Anchor(777, 699, contourpoint=99), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(194, 481, contourpoint=102), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphClass(["BehxMed_RehFin", "BehxMed_RehFin.cup"]),
                        marks=[
                            [(ast.Anchor(708, 1083, contourpoint=65), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(282, 813, contourpoint=64), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamAlefSep"),
                        marks=[
                            [(ast.Anchor(1055, 1583, contourpoint=105), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(198, 1528, contourpoint=106), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                    ast.MarkLigPosStatement(
                        ligatures=ast.GlyphName("LamAlefFin"),
                        marks=[
                            [(ast.Anchor(1122, 1620, contourpoint=98), ast.MarkClass("GPOS_MC001"))],
                            [(ast.Anchor(162, 1487, contourpoint=99), ast.MarkClass("GPOS_MC001"))],
                        ],
                    ),
                ],
            ),
            make_mark_class(
                "GPOS_MC001",
                [
                    (["FathatanNS"], AnchorPoint(281, 1388, contour_point=0)),
                    (["DammatanNS"], AnchorPoint(354, 1409, contour_point=0)),
                    (["FathaNS"], AnchorPoint(277, 1379, contour_point=0)),
                    (["DammaNS"], AnchorPoint(394, 1444, contour_point=0)),
                    (["ShaddaNS", "ShaddaAlefNS", "ShaddaDammatanNS", "ShaddaDammaNS"], AnchorPoint(283, 1581, contour_point=0)),
                    (["SukunNS"], AnchorPoint(220, 1474, contour_point=1)),
                    (["MaddaNS"], AnchorPoint(397, 1472, contour_point=1)),
                    (["HamzaAboveNS"], AnchorPoint(266, 1425, contour_point=2)),
                    (["UltapeshNS", "DammaRflxNS"], AnchorPoint(454, 1128, contour_point=1)),
                    (["Fatha2dotsNS"], AnchorPoint(272, 1097, contour_point=0)),
                    (["AlefSuperiorNS"], AnchorPoint(141, 874, contour_point=1)),
                    (["WaslaNS"], AnchorPoint(357, 1470, contour_point=0)),
                    (["OneDotAboveNS", "OneDotAbove2NS"], AnchorPoint(215, 1001, contour_point=3)),
                    (["TwoDotsAboveNS", "ThreeDotsUpAboveNS"], AnchorPoint(346, 1003, contour_point=0)),
                    (["ThreeDotsDownAboveNS"], AnchorPoint(346, 687, contour_point=0)),
                    (["FourDotsAboveNS"], AnchorPoint(347, 860, contour_point=0)),
                    (["TwoDotsVerticalAboveNS"], AnchorPoint(357, 707, contour_point=1)),
                    (["SharetKafNS"], AnchorPoint(382, 520, contour_point=1)),
                    (["ShaddaKasratanNS"], AnchorPoint(315, 1164, contour_point=55)),
                    (["ShaddaKasraNS"], AnchorPoint(426, 1340, contour_point=55)),
                    (["ShaddaFathatanNS"], AnchorPoint(369, 1604, contour_point=0)),
                ],
            ),
        ),
    ],
    ids=param_ids,
)
def test_pos_fragment_with_mark_class(mti_file: str, expected: Lookup, expected_mark_class: ast.MarkClass):
    parser = GposParser(data_loader(mti_file))

    parser.parse()
    assert len(parser.lookups) == 1
    actual = feaify(parser.lookups[0])
    expected = feaify(expected)
    assert actual == expected

    assert len(parser.mark_classes) == 1
    actual_mark_class = parser.mark_classes[0].asFea()
    expected_mark_class = expected_mark_class.asFea()
    assert actual_mark_class == expected_mark_class
