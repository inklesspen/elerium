# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import pathlib

import fontTools.feaLib.ast as ast
import pytest

from elerium.mti_parser import GsubParser, Lookup, LookupFlag, Parser
from elerium.warnings import FeatureSyntaxWarning

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
    return None


@pytest.mark.parametrize(
    ["mti_file", "expected"],
    [
        (
            "mti/gsubsingle",
            Lookup(
                lookup_id="GSUB_alt-fractions",
                statements=[
                    ast.SingleSubstStatement(
                        glyphs=[ast.GlyphClass(glyphs=["onehalf", "onequarter", "threequarters"])],
                        replace=[ast.GlyphClass(glyphs=["onehalf.alt", "onequarter.alt", "threequarters.alt"])],
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    )
                ],
            ),
        ),
        (
            "mti/gsubmultiple",
            Lookup(
                lookup_id="GSUB_replace-akhand-telugu",
                statements=[
                    ast.MultipleSubstStatement(
                        glyph=ast.GlyphName(glyph="kassevoweltelugu"),
                        replacement=[ast.GlyphClass(glyphs=["kaivoweltelugu", "ssasubscripttelugu"])],
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.MultipleSubstStatement(
                        glyph=ast.GlyphName(glyph="janyevoweltelugu"),
                        replacement=[ast.GlyphClass(glyphs=["jaivoweltelugu", "nyasubscripttelugu"])],
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                ],
            ),
        ),
        (
            "mti/gsubalternate",
            Lookup(
                lookup_id="GSUB_27",
                statements=[
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("zero"),
                        replacement=ast.GlyphClass(
                            ["uniF730", "uniE13D", "uniE13E", "uniE13A", "uni2070", "uni2080", "uniE13B", "uniE139", "uniE13C"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("one"),
                        replacement=ast.GlyphClass(
                            ["uniF731", "uniE0F3", "uniE0F4", "uniE0F1", "uni00B9", "uni2081", "uniE0F2", "uniE0F0", "uniE0F8"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("two"),
                        replacement=ast.GlyphClass(
                            ["uniF732", "uniE133", "uniE134", "uniE131", "uni00B2", "uni2082", "uniE132", "uniE130", "uniE0F9"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("three"),
                        replacement=ast.GlyphClass(
                            ["uniF733", "uniE12B", "uniE12C", "uniE129", "uni00B3", "uni2083", "uniE12A", "uniE128"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("four"),
                        replacement=ast.GlyphClass(
                            ["uniF734", "uniE0D4", "uniE0D5", "uniE0D2", "uni2074", "uni2084", "uniE0D3", "uniE0D1"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("five"),
                        replacement=ast.GlyphClass(
                            ["uniF735", "uniE0CD", "uniE0CE", "uniE0CB", "uni2075", "uni2085", "uniE0CC", "uniE0CA"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("six"),
                        replacement=ast.GlyphClass(
                            ["uniF736", "uniE121", "uniE122", "uniE11F", "uni2076", "uni2086", "uniE120", "uniE11E"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("seven"),
                        replacement=ast.GlyphClass(
                            ["uniF737", "uniE11C", "uniE11D", "uniE11A", "uni2077", "uni2087", "uniE11B", "uniE119"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("eight"),
                        replacement=ast.GlyphClass(
                            ["uniF738", "uniE0C0", "uniE0C1", "uniE0BE", "uni2078", "uni2088", "uniE0BF", "uniE0BD"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("nine"),
                        replacement=ast.GlyphClass(
                            ["uniF739", "uniE0EC", "uniE0ED", "uniE0EA", "uni2079", "uni2089", "uniE0EB", "uniE0E9"]
                        ),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("guilsinglleft"),
                        replacement=ast.GlyphClass(["uniE0DB", "uniE0DC"]),
                        prefix=[],
                        suffix=[],
                    ),
                    ast.AlternateSubstStatement(
                        glyph=ast.GlyphName("guilsinglright"),
                        replacement=ast.GlyphClass(["uniE0DD", "uniE0DE"]),
                        prefix=[],
                        suffix=[],
                    ),
                ],
            ),
        ),
        (
            "mti/gsubligature",
            Lookup(
                lookup_id="GSUB_latinLigatures",
                statements=[
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("I"), ast.GlyphName("J")],
                        replacement=ast.GlyphName("IJ"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("f"), ast.GlyphName("i")],
                        replacement=ast.GlyphName("ffi"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("f"), ast.GlyphName("l")],
                        replacement=ast.GlyphName("ffl"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("f"), ast.GlyphName("t")],
                        replacement=ast.GlyphName("fft"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("f"), ast.GlyphName("b")],
                        replacement=ast.GlyphName("ffb"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("f"), ast.GlyphName("h")],
                        replacement=ast.GlyphName("ffh"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("f"), ast.GlyphName("k")],
                        replacement=ast.GlyphName("ffk"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("i")],
                        replacement=ast.GlyphName("fi"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("l")],
                        replacement=ast.GlyphName("fl"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("f")],
                        replacement=ast.GlyphName("ff"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("t")],
                        replacement=ast.GlyphName("ft"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("b")],
                        replacement=ast.GlyphName("fb"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("h")],
                        replacement=ast.GlyphName("fh"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("k")],
                        replacement=ast.GlyphName("fk"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("f"), ast.GlyphName("j")],
                        replacement=ast.GlyphName("fj"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("i"), ast.GlyphName("j")],
                        replacement=ast.GlyphName("ij"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("t"), ast.GlyphName("t")],
                        replacement=ast.GlyphName("tt"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                    ast.LigatureSubstStatement(
                        glyphs=[ast.GlyphName("Ismall"), ast.GlyphName("Jsmall")],
                        replacement=ast.GlyphName("IJsmall"),
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    ),
                ],
            ),
        ),
        (
            "nototools/consub1",
            Lookup(
                lookup_id="GSUB_testLookupCtx",
                depends_on=["GSUB_testLookupSub"],
                statements=[
                    # sub b' lookup GSUB_testLookupSub a';
                    ast.ChainContextSubstStatement(
                        glyphs=[ast.GlyphName("b"), ast.GlyphName("a")],
                        lookups=[[ast.LookupBlock(name="GSUB_testLookupSub")], None],
                        prefix=[],
                        suffix=[],
                    )
                ],
            ),
        ),
        (
            "nototools/consub2",
            Lookup(
                lookup_id="GSUB_testLookupCtx",
                depends_on=["GSUB_testLookupSub"],
                statements=[
                    # sub [a d]' lookup GSUB_testLookupSub b' c' [a d]';
                    ast.ChainContextSubstStatement(
                        glyphs=[ast.GlyphClass(["a", "d"]), ast.GlyphName("b"), ast.GlyphName("c"), ast.GlyphClass(["a", "d"])],
                        lookups=[[ast.LookupBlock(name="GSUB_testLookupSub")], None, None, None],
                        prefix=[],
                        suffix=[],
                    )
                ],
            ),
        ),
        (
            "mti/chained-glyph",
            Lookup(
                lookup_id="GSUB_raucontext-sinh",
                flags=LookupFlag.MARK_ATTACHMENT_CLASS_FILTER,
                mark_attachment_class=2,
                depends_on=["GSUB_u2aelow-sinh"],
                statements=[
                    # sub rakarsinh uvowelsignsinh' lookup GSUB_u2aelow-sinh;
                    # sub rakarsinh uuvowelsignsinh' lookup GSUB_u2aelow-sinh;
                    ast.ChainContextSubstStatement(
                        glyphs=[ast.GlyphName("uvowelsignsinh")],
                        lookups=[[ast.LookupBlock(name="GSUB_u2aelow-sinh")]],
                        prefix=[ast.GlyphName("rakarsinh")],
                        suffix=[],
                    ),
                    ast.ChainContextSubstStatement(
                        glyphs=[ast.GlyphName("uuvowelsignsinh")],
                        lookups=[[ast.LookupBlock(name="GSUB_u2aelow-sinh")]],
                        prefix=[ast.GlyphName("rakarsinh")],
                        suffix=[],
                    ),
                ],
            ),
        ),
        (
            "nototools/chainsub1",
            Lookup(
                lookup_id="GSUB_testLookupCtx",
                depends_on=["GSUB_testLookupSub"],
                statements=[
                    # sub b a' lookup GSUB_testLookupSub c;
                    ast.ChainContextSubstStatement(
                        glyphs=[ast.GlyphName("a")],
                        lookups=[[ast.LookupBlock(name="GSUB_testLookupSub")]],
                        prefix=[ast.GlyphName("b")],
                        suffix=[ast.GlyphName("c")],
                    )
                ],
            ),
        ),
        (
            "chainedclass",
            Lookup(
                lookup_id="GSUB_contrived",
                depends_on=["GSUB_somelookup", "GSUB_otherlookup"],
                statements=[
                    # sub z [a e]' [a e]' lookup GSUB_somelookup [one three five];
                    ast.ChainContextSubstStatement(
                        glyphs=[ast.GlyphClass(glyphs=["a", "e"]), ast.GlyphClass(glyphs=["a", "e"])],
                        lookups=[None, [ast.LookupBlock(name="GSUB_somelookup")]],
                        prefix=[ast.GlyphName("z")],
                        suffix=[ast.GlyphClass(glyphs=["one", "three", "five"])],
                    ),
                    # sub y y [b c d f]' lookup GSUB_somelookup [a e]' [b c d f]' lookup GSUB_otherlookup [two four six];
                    ast.ChainContextSubstStatement(
                        glyphs=[
                            ast.GlyphClass(glyphs=["b", "c", "d", "f"]),
                            ast.GlyphClass(glyphs=["a", "e"]),
                            ast.GlyphClass(glyphs=["b", "c", "d", "f"]),
                        ],
                        lookups=[[ast.LookupBlock(name="GSUB_somelookup")], None, [ast.LookupBlock(name="GSUB_otherlookup")]],
                        prefix=[ast.GlyphName("y"), ast.GlyphName("y")],
                        suffix=[ast.GlyphClass(glyphs=["two", "four", "six"])],
                    ),
                ],
            ),
        ),
        (
            "mti/chainedcoverage",
            Lookup(
                lookup_id="GSUB_slashcontext",
                depends_on=["GSUB_slashTofraction"],
                statements=[
                    # "sub [zero one two three four five six seven eight nine] slash' lookup GSUB_slashTofraction [zero one two three four five six seven eight nine];"
                    ast.ChainContextSubstStatement(
                        glyphs=[ast.GlyphName("slash")],
                        lookups=[[ast.LookupBlock(name="GSUB_slashTofraction")]],
                        prefix=[ast.GlyphClass(["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"])],
                        suffix=[ast.GlyphClass(["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"])],
                    ),
                ],
            ),
        ),
        (
            "mti/gsubreversechanined",  # lol typo
            Lookup(
                lookup_id="GSUB_arabicReverse",
                flags=LookupFlag.RIGHT_TO_LEFT | LookupFlag.IGNORE_MARKS,
                statements=[
                    # rsub [bayi1 jeemi1 kafi1 ghafi1 laami1 kafm1 ghafm1 laamm1] [rayf2 reyf2 zayf2 yayf2]' by [rayf1 reyf1 zayf1 yayf1];
                    ast.ReverseChainSingleSubstStatement(
                        old_prefix=[ast.GlyphClass(["bayi1", "jeemi1", "kafi1", "ghafi1", "laami1", "kafm1", "ghafm1", "laamm1"])],
                        old_suffix=[],
                        glyphs=[ast.GlyphClass(["rayf2", "reyf2", "zayf2", "yayf2"])],
                        replacements=[ast.GlyphClass(["rayf1", "reyf1", "zayf1", "yayf1"])],
                    ),
                    # rsub [bayi1 kafi1 ghafi1 laami1 kafm1 ghafm1 laamm1 fayi1] [hamzayehf2 hamzayeharabf2 ayehf2 yehf2]' by [hamzayehf1 hamzayeharabf1 ayehf1 yehf1];
                    ast.ReverseChainSingleSubstStatement(
                        old_prefix=[ast.GlyphClass(["bayi1", "fayi1", "kafi1", "ghafi1", "laami1", "kafm1", "ghafm1", "laamm1"])],
                        old_suffix=[],
                        glyphs=[ast.GlyphClass(["hamzayehf2", "hamzayeharabf2", "ayehf2", "yehf2"])],
                        replacements=[ast.GlyphClass(["hamzayehf1", "hamzayeharabf1", "ayehf1", "yehf1"])],
                    ),
                    # rsub [dal del zal]' [ray rey zay yay] by [dal1 del1 zal1];
                    ast.ReverseChainSingleSubstStatement(
                        old_prefix=[],
                        old_suffix=[ast.GlyphClass(["ray", "rey", "zay", "yay"])],
                        glyphs=[ast.GlyphClass(["dal", "del", "zal"])],
                        replacements=[ast.GlyphClass(["dal1", "del1", "zal1"])],
                    ),
                ],
            ),
        ),
    ],
    ids=param_ids,
)
def test_gsub_fragment(mti_file: str, expected: Lookup):
    parser = GsubParser(data_loader(mti_file))

    parser.parse()
    assert len(parser.lookups) == 1
    actual = feaify(parser.lookups[0])
    expected = feaify(expected)
    assert actual == expected


def test_out_of_order_context_lookups():
    expected = Lookup(
        lookup_id="GSUB_ooochaining",
        depends_on=["GSUB_sublookup", "GSUB_otherlookup", "GSUB_thirdlookup"],
        statements=[
            ast.Comment(
                "# Lookup GSUB_ooochaining has syntax that cannot be expressed in ADFKO: 2,sublookup 1,otherlookup. If the order of application matters here, you will need to restructure this rule.",
            ),
            ast.ChainContextSubstStatement(
                glyphs=[ast.GlyphClass(["A", "B", "C", "D"]), ast.GlyphClass(["Z", "Y", "X"])],
                lookups=[[ast.LookupBlock(name="GSUB_otherlookup")], [ast.LookupBlock(name="GSUB_sublookup")]],
                prefix=[ast.GlyphClass(["two", "four", "six"]), ast.GlyphClass(["one", "three", "five"])],
                suffix=[ast.GlyphClass(["two", "four", "six"])],
            ),
            ast.Comment(
                "# Lookup GSUB_ooochaining has syntax that cannot be expressed in ADFKO: 2,sublookup 1,thirdlookup. If the order of application matters here, you will need to restructure this rule.",
            ),
            ast.ChainContextSubstStatement(
                glyphs=[ast.GlyphClass(["seven", "eight", "nine"]), ast.GlyphClass(["one", "two", "three"])],
                lookups=[[ast.LookupBlock(name="GSUB_thirdlookup")], [ast.LookupBlock(name="GSUB_sublookup")]],
                prefix=[ast.GlyphClass(["a", "c", "e"])],
                suffix=[ast.GlyphClass(["x", "y", "z"])],
            ),
        ],
    )
    parser = GsubParser(data_loader("ooo_chaining"))

    with pytest.warns(FeatureSyntaxWarning):
        parser.parse()

    assert len(parser.lookups) == 1
    actual = feaify(parser.lookups[0])
    expected = feaify(expected)
    assert actual == expected


CYRL_GREK_FEATURE = """\
feature test {
    script cyrl;
    lookup GSUB_slashcontext;
    script grek;
    lookup GSUB_slashcontext;
} test;
"""

LATN_FEATURE = """\
feature test {
    script latn;
    lookup GSUB_slashcontext;
} test;
"""

LATN_DEU_FEATURE = """\
feature test {
    script latn;
    language DEU;
    lookup GSUB_slashcontext;
} test;
"""

# This is technically possible, and probably would be better, but is not currently produced.
COMBINED_FEATURE = """\
feature test {
    script cyrl;
    lookup GSUB_slashcontext;
    script grek;
    lookup GSUB_slashcontext;
    script latn;
    lookup GSUB_slashcontext;
    language DEU;
} test;
"""


def test_multi_script_lookups():
    # In this example, a lookup is used by multiple scripts.
    # cyrl and grek both use feature 0.
    # latn with the default language uses feature 1.
    # latin with the DEU (German) language uses feature 2.
    # But all three features reference the same lookup.
    # The parser should produce one feature with both cyrl and grek, one for latn, and one for latn DEU.
    parser = Parser()
    parser.add_GDEF(DATA_BASE_PATH / "plist" / "Example GDEF.txt")
    parser.add_GSUB(DATA_BASE_PATH / "multiscriptlookup.txt")

    fea_ast = parser.parse()
    assert isinstance(fea_ast, ast.FeatureFile)

    actual_feature_defs = [stmt.asFea() for stmt in fea_ast.statements if isinstance(stmt, ast.FeatureBlock)]
    expected_feature_defs = [CYRL_GREK_FEATURE, LATN_FEATURE, LATN_DEU_FEATURE]
    assert actual_feature_defs == expected_feature_defs
