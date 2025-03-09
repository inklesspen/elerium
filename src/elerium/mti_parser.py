# SPDX-FileCopyrightText: Contributors to FontTools <https://github.com/fonttools/fonttools?tab=readme-ov-file#copyrights>
# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
# The code in this file is substantially based on fontTools.mtiLib
from __future__ import annotations

import dataclasses
import enum
import functools
import logging
import pathlib
import re
import typing
import warnings
from contextlib import contextmanager

import fontTools.feaLib.ast as ast
import fontTools.misc.plistlib
from fontTools import agl
from fontTools.mtiLib import intSplitComma as int_split_comma
from fontTools.mtiLib import stripSplitComma as strip_split_comma

from .warnings import FeatureSyntaxWarning

if typing.TYPE_CHECKING:
    from typing import Optional

    import ufoLib2
    from ufoLib2.typing import PathLike

logger = logging.getLogger(__name__)


class MtiParserError(Exception):
    pass


class ParseError(MtiParserError):
    pass


class LookupFlag(enum.IntFlag):
    NONE = 0
    RIGHT_TO_LEFT = 0x0001
    IGNORE_BASE_GLYPHS = 0x0002
    IGNORE_LIGATURES = 0x0004
    IGNORE_MARKS = 0x0008
    USE_MARK_FILTERING_SET = 0x0010
    MARK_ATTACHMENT_CLASS_FILTER = 0xFF00


@dataclasses.dataclass(kw_only=True)
class GlyphDefinitions:
    glyph_classes: Optional[list[list[str]]] = None
    attachment_points: Optional[dict[str, list[int]]] = None
    ligature_carets: Optional[dict[str, list[int]]] = None
    mark_attachment_classes: Optional[list[list[str]]] = None
    mark_filter_sets: Optional[dict[int, set[str]]] = None


@dataclasses.dataclass(kw_only=True)
class ScriptTableEntry:
    script: str
    language: str
    required_feature: Optional[int | str] = None
    features: list[int | str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(kw_only=True)
class FeatureTableEntry:
    feature_id: int | str
    kind: str
    lookups: Optional[list[str]] = None

    def to_ast(self, scripts_for_feature: Optional[list[ScriptTableEntry]] = None):
        block = ast.FeatureBlock(self.kind)
        lookup_stmts = []
        if self.lookups:
            for lookup_id in self.lookups:
                lookup_stmts.append(ast.LookupReferenceStatement(ast.LookupBlock(lookup_id)))
        current_script = "DFLT"
        current_language = "dflt"
        if scripts_for_feature is not None:
            for ste in scripts_for_feature:
                if ste.script != current_script:
                    current_script = ste.script
                    current_language = "dflt"
                    block.statements.append(ast.ScriptStatement(ste.script))
                if ste.language != current_language:
                    current_language = ste.language
                    block.statements.append(ast.LanguageStatement(ste.language, required=(ste.required_feature == self.feature_id)))
                block.statements.extend(lookup_stmts)
        return block


@dataclasses.dataclass(kw_only=True)
class Lookup:
    lookup_id: str
    flags: LookupFlag = LookupFlag.NONE
    mark_attachment_class: Optional[int] = None
    mark_filter_set: Optional[int] = None
    depends_on: list[str] = dataclasses.field(default_factory=list)
    statements: list[ast.Statement] = dataclasses.field(default_factory=list)

    def to_ast(self, glyph_definitions: GlyphDefinitions):
        block = ast.LookupBlock(name=self.lookup_id)
        if self.flags:
            mark_attachment = None
            mark_filtering_set = None
            if self.mark_attachment_class is not None:
                mark_attachment = ast.GlyphClass(glyph_definitions.mark_attachment_classes[self.mark_attachment_class - 1])
            if self.mark_filter_set is not None:
                mark_filtering_set = ast.GlyphClass(list(glyph_definitions.mark_filter_sets[self.mark_filter_set]))
            block.statements.append(ast.LookupFlagStatement(self.flags, mark_attachment, mark_filtering_set))
        block.statements.extend(self.statements)
        return block


@dataclasses.dataclass(kw_only=True)
class FeatureFile:
    table_tag: typing.Literal["GDEF", "GSUB", "GPOS"]
    glyph_definitions: Optional[GlyphDefinitions] = None
    script_table: list[ScriptTableEntry] = dataclasses.field(default_factory=list)
    feature_table: list[FeatureTableEntry] = dataclasses.field(default_factory=list)
    lookups: list[Lookup] = dataclasses.field(default_factory=list)
    mark_classes: list[ast.MarkClass] = dataclasses.field(default_factory=list)


def sorted_lookups(*to_sort: Lookup):
    slookups: list[Lookup] = []
    lookups_seen: set[str] = set()
    parking_lot: list[Lookup] = []
    unsorted = list(to_sort)
    assert len(unsorted) == len(to_sort)
    while parking_lot or unsorted:
        for lookup in parking_lot:
            if all(dep in lookups_seen for dep in lookup.depends_on):
                lookups_seen.add(lookup.lookup_id)
                slookups.append(lookup)
        parking_lot = [lookup for lookup in parking_lot if lookup.lookup_id not in lookups_seen]
        if parking_lot and not unsorted:
            raise ParseError("Cannot sort lookups by dependency; check for circular dependency")
        if unsorted:
            lookup = unsorted.pop(0)
            logger.debug("Checking deps for %s", lookup.lookup_id)
            if all(dep in lookups_seen for dep in lookup.depends_on):
                logger.debug("Deps satisfied")
                lookups_seen.add(lookup.lookup_id)
                slookups.append(lookup)
            else:
                logger.debug("parking it")
                parking_lot.append(lookup)
    assert len(slookups) == len(to_sort)
    return slookups


def _script_feature_to_ast_helper(
    ff: FeatureFile,
    script_entries: dict[tuple[str, str], list[ScriptTableEntry]],
    scripts_for_features: dict[str, list[ScriptTableEntry]],
):
    for ste in ff.script_table:
        scriptkey = (ste.script, ste.language)
        new_ste = ScriptTableEntry(script=ste.script, language=ste.language)
        # The lookups have already been renamed by the parser, but the features have not.
        new_ste.features = [f"{ff.table_tag}_{feature_id}" for feature_id in ste.features]
        if ste.required_feature is not None:
            new_ste.required_feature = f"{ff.table_tag}_{ste.required_feature}"
            scripts_for_features.setdefault(new_ste.required_feature, [])
            if scriptkey not in scripts_for_features[new_ste.required_feature]:
                scripts_for_features[new_ste.required_feature].append(new_ste)
        for feature_id in new_ste.features:
            scripts_for_features.setdefault(feature_id, [])
            if scriptkey not in scripts_for_features[feature_id]:
                scripts_for_features[feature_id].append(new_ste)
        script_entries.setdefault(scriptkey, []).append(new_ste)


def _feature_to_ast_helper(
    ff: FeatureFile,
    scripts_for_features: dict[str, list[ScriptTableEntry]],
):
    statements: list[ast.FeatureBlock] = []
    for fte in ff.feature_table:
        fte.feature_id = f"{ff.table_tag}_{fte.feature_id}"
        statements.append(fte.to_ast(scripts_for_features.get(fte.feature_id)))
    return statements


def to_ast(*files: FeatureFile):
    gdefs = [ff for ff in files if ff.table_tag == "GDEF"]
    not_gdefs = [ff for ff in files if ff.table_tag != "GDEF"]
    if len(gdefs) != 1:
        raise ParseError("Must have one and only one GDEF file")
    gdef = gdefs[0]
    if gdef.glyph_definitions is None:
        raise ParseError("GDEF file is empty")
    for attr in ("script_table", "feature_table", "lookups", "mark_classes"):
        if getattr(gdef, attr):
            raise ParseError(f"GDEF file incorrectly has {attr}")
    for ff in not_gdefs:
        if ff.glyph_definitions is not None:
            raise ParseError("Non-GDEF file incorrectly has GlyphDefinitions")
    glyph_definitions = gdefs[0].glyph_definitions
    gsubs = [ff for ff in files if ff.table_tag == "GSUB"]
    gposs = [ff for ff in files if ff.table_tag == "GPOS"]
    if len(gsubs) > 1:
        logger.warning("More than one GSUB was provided; look out for name collisions.")
    if len(gposs) > 1:
        logger.warning("More than one GPOS was provided; look out for name collisions.")
    root = ast.FeatureFile()
    script_entries: dict[tuple[str, str], list[ScriptTableEntry]] = {}
    scripts_for_features: dict[str, list[ScriptTableEntry]] = {}
    for ff in not_gdefs:
        _script_feature_to_ast_helper(ff, script_entries, scripts_for_features)

    if ("DFLT", "dflt") in script_entries:
        root.statements.append(ast.LanguageSystemStatement(script="DFLT", language="dflt"))
    other_script_langs = []
    for script, language in script_entries:
        if script == "DFLT":
            root.statements.append(ast.LanguageSystemStatement(script="DFLT", language=language))
        else:
            other_script_langs.append(ast.LanguageSystemStatement(script=script, language=language))
    root.statements.extend(other_script_langs)
    if (
        glyph_definitions.glyph_classes is not None
        or glyph_definitions.attachment_points is not None
        or glyph_definitions.ligature_carets is not None
    ):
        gdef_table = ast.TableBlock("GDEF")
        if glyph_definitions.glyph_classes is not None:
            assert len(glyph_definitions.glyph_classes) == 4
            gcds = [
                ast.GlyphClassDefinition(name, ast.GlyphClass(glyph_definitions.glyph_classes[idx]))
                for idx, name in enumerate(["BASES", "LIGATURES", "MARKS", "COMPONENTS"])
            ]
            root.statements.extend(gcds)
            gcns = [ast.GlyphClassName(gcd) for gcd in gcds]
            # no idea why it does this out of order…
            gdef_table.statements.append(ast.GlyphClassDefStatement(gcns[0], gcns[2], gcns[1], gcns[3]))
        if glyph_definitions.attachment_points is not None:
            for glyph, points in glyph_definitions.attachment_points.items():
                gdef_table.statements.append(ast.AttachStatement(ast.GlyphName(glyph), points))
        if glyph_definitions.ligature_carets is not None:
            for glyph, carets in glyph_definitions.ligature_carets.items():
                gdef_table.statements.append(ast.LigatureCaretByPosStatement(ast.GlyphName(glyph), carets))
        root.statements.append(gdef_table)

    for ff in not_gdefs:
        root.statements.extend(ff.mark_classes)

    for ff in gsubs:
        root.statements.extend(lookup.to_ast(glyph_definitions) for lookup in sorted_lookups(*ff.lookups))
    for ff in gposs:
        root.statements.extend(lookup.to_ast(glyph_definitions) for lookup in sorted_lookups(*ff.lookups))

    for ff in not_gdefs:
        root.statements.extend(_feature_to_ast_helper(ff, scripts_for_features))

    return root


@dataclasses.dataclass(frozen=True)
class AnchorPoint:
    x: int
    y: int
    contour_point: Optional[int] = None

    def to_ast(self):
        return ast.Anchor(x=self.x, y=self.y, contourpoint=self.contour_point)


def make_mark_class(name: str, glyphs_with_anchor: list[tuple[list[str], AnchorPoint]]):
    mc = ast.MarkClass(name)
    for glyphs, anchor in glyphs_with_anchor:
        mc.addDefinition(ast.MarkClassDefinition(mc, anchor.to_ast(), ast.GlyphClass(glyphs)))
    return mc


def try_int(val: int | str):
    try:
        return int(val)
    except ValueError:
        return val


def require_int(val: int | str):
    try:
        return int(val)
    except ValueError:
        raise ParseError("Required an integer value but found %r" % val) from None


def _make_glyph_name(codepoint):
    if codepoint in agl.UV2AGL:
        return agl.UV2AGL[codepoint]
    if codepoint <= 0xFFFF:
        return "uni%04X" % codepoint
    return "u%X" % codepoint


def make_glyph(s: str):
    if s[:2] in ["U ", "u "]:
        return _make_glyph_name(int(s[2:], 16))
    if s[:2] == "# ":
        return "glyph%.5d" % int(s[2:])
    assert s.find(" ") < 0, "Space found in glyph name: %s" % s
    assert s, "Glyph name is empty"
    return s


def make_glyphs(glyphs: list[str]):
    return [make_glyph(g) for g in glyphs]


class LookupAndFeatureParser:
    script_table: list[ScriptTableEntry]
    feature_table: list[FeatureTableEntry]
    lookups: list[Lookup]
    mark_classes: list[ast.MarkClass]
    _table_tag: typing.Literal["GSUB", "GPOS"]

    def __init__(self, txt: str):
        self.tokens = Tokenizer(txt)
        self.mark_classes = []
        self._mark_class_counter = 1

    def _name_mark_class(self):
        name = f"{self._table_tag}_MC{self._mark_class_counter:0>3d}"
        self._mark_class_counter += 1
        return name

    def _name_lookup(self, existing_name: str):
        return f"{self._table_tag}_{existing_name}"

    def parse(self):
        self.script_table = []
        self.feature_table = []
        self.lookups = []
        logger.debug("Parsing %s", self._table_tag)

        fields = {
            "script table begin": self.parse_script_table,
            "feature table begin": self.parse_feature_table,
            "lookup": self.parse_lookup,
        }
        while self.tokens.peek() is not None:
            typ = self.tokens.peek()[0].lower()
            if typ not in fields:
                logger.debug("Skipping %s", typ)
                next(self.tokens)
                continue
            parser = fields[typ]
            parser()
        return FeatureFile(
            table_tag=self._table_tag,
            script_table=self.script_table,
            feature_table=self.feature_table,
            lookups=self.lookups,
            mark_classes=self.mark_classes,
        )

    def parse_script_table(self):
        with self.tokens.between("script table"):
            for line in self.tokens:
                while len(line) < 4:
                    line.append("")
                scriptTag, langSysTag, defaultFeature, features = line
                if len(scriptTag) > 4:
                    raise ParseError(f"Script tag {scriptTag} is too long")
                if len(scriptTag) < 4:
                    scriptTag = f"{scriptTag: <4}"
                if langSysTag == "default":
                    langSysTag = "dflt"
                if len(langSysTag) > 4:
                    raise ParseError(f"Language tag {langSysTag} is too long")
                if len(langSysTag) < 4:
                    langSysTag = f"{langSysTag: <4}"
                logger.debug("Adding script %s language-system %s", scriptTag, langSysTag)

                entry = ScriptTableEntry(script=scriptTag, language=langSysTag)
                if defaultFeature:
                    entry.required_feature = require_int(defaultFeature)

                entry.features = [require_int(f_id) for f_id in strip_split_comma(features)]
                self.script_table.append(entry)

    def parse_feature_table(self):
        # Each file (GSUB and GPOS) should have its own feature table.
        # It should only have one, but in both files they start numbering at 0.
        # Luckily this class only has to deal with one file at a time.
        with self.tokens.between("feature table"):
            for line in self.tokens:
                name, featureTag, lookups = line
                feature_num = len(self.feature_table)
                entry = FeatureTableEntry(feature_id=feature_num, kind=featureTag)
                if try_int(name) != entry.feature_id:
                    logger.warning("Found feature %s with specified index %r but it should be %d", entry.kind, name, entry.feature_id)
                if lookups:
                    entry.lookups = [self._name_lookup(l_id) for l_id in strip_split_comma(lookups)]
                self.feature_table.append(entry)

    def parse_lookup(self):
        _, name, typ = self.tokens.expect("lookup")
        entry = Lookup(lookup_id=self._name_lookup(name))
        logger.debug("Parsing lookup type %s %s", typ, name)
        entry.flags, entry.mark_attachment_class, entry.mark_filter_set = self._parse_lookup_flags()

        contents = []
        with self.tokens.until("lookup end"):
            while self.tokens.peek():
                with self.tokens.until((r"% subtable", "subtable end")):
                    while self.tokens.peek():
                        subtable = self.parse_lookup_subtable(entry, typ)
                        contents.extend(subtable)
                if self.tokens.peeks()[0] in (r"% subtable", "subtable end"):
                    next(self.tokens)
        self.tokens.expect("lookup end")
        if contents:
            entry.statements = contents
        self.lookups.append(entry)

    def parse_lookup_subtable(self, lookup: Lookup, kind: str):
        raise NotImplementedError("Implement this in a subclass!")

    def _parse_lookup_flags(self):
        flags = LookupFlag.NONE
        mark_attachment_class = None
        mark_filter_set = None
        allFlags = [
            "righttoleft",
            "ignorebaseglyphs",
            "ignoreligatures",
            "ignoremarks",
            "markattachmenttype",
            "markfiltertype",
        ]
        while self.tokens.peeks()[0].lower() in allFlags:
            line = next(self.tokens)
            flag = {
                "righttoleft": 0x0001,
                "ignorebaseglyphs": 0x0002,
                "ignoreligatures": 0x0004,
                "ignoremarks": 0x0008,
            }.get(line[0].lower())
            if flag:
                assert line[1].lower() in ["yes", "no"], line[1]
                if line[1].lower() == "yes":
                    flags |= LookupFlag(flag)
            elif line[0].lower() == "markattachmenttype":
                flags |= LookupFlag.MARK_ATTACHMENT_CLASS_FILTER
                mark_attachment_class = require_int(line[1])
            elif line[0].lower() == "markfiltertype":
                flags |= LookupFlag.USE_MARK_FILTERING_SET
                mark_filter_set = require_int(line[1])
        return flags, mark_attachment_class, mark_filter_set

    def _parse_contextual_class(self):
        glyphs_seen = set()
        glyphs_by_class: dict[int, list[str]] = {}
        with self.tokens.between("class definition"):
            for line in self.tokens:
                glyph = make_glyph(line[0])
                assert glyph not in glyphs_seen, glyph
                classnum = int(line[1])
                glyphs_seen.add(glyph)
                glyphs_by_class.setdefault(classnum, [])
                glyphs_by_class[classnum].append(glyph)
        return glyphs_by_class

    def _parse_position_lookup_entries(self, glyphs: list[ast.Expression], position_lookups: list[str], current_lookup: Lookup):
        lookups: list[Optional[list[ast.LookupBlock]]] = [None] * len(glyphs)
        indexes = []
        for ref in position_lookups:
            ref = strip_split_comma(ref)
            assert len(ref) == 2
            idx = int(ref[0]) - 1
            indexes.append(idx)
            if lookups[idx] is None:
                lookups[idx] = []
            depname = self._name_lookup(ref[1])
            if depname not in current_lookup.depends_on:
                current_lookup.depends_on.append(depname)
            lookups[idx].append(ast.LookupBlock(name=depname))
        if indexes != sorted(indexes):
            # Hat tip to simoncozens; Monotype syntax permits out-of-order lookups, but ADFKO does not
            # https://github.com/adobe-type-tools/afdko/discussions/1709
            expl = f"Lookup {current_lookup.lookup_id} has syntax that cannot be expressed in ADFKO: {' '.join(position_lookups)}. If the order of application matters here, you will need to restructure this rule."
            warnings.warn(expl, FeatureSyntaxWarning, stacklevel=2)
            return lookups, ast.Comment("# " + expl)
        return lookups, None

    def _parse_chaining[RK: (ast.ChainContextSubstStatement, ast.ChainContextPosStatement)](
        self, ruleklass: type[RK], lookup: Lookup, is_chained: bool
    ):
        glyph_set_count = 3 if is_chained else 1
        sequence_kinds = ["prefix", "glyphs", "suffix"] if is_chained else ["glyphs"]
        typ = self.tokens.peeks()[0].split()[0].lower()
        if typ == "glyph":
            rules = []
            for line in self.tokens:
                assert line[0].lower() == "glyph", line[0]
                if len(line) < 2 + glyph_set_count:
                    continue
                rule_kwargs = {"glyphs": [], "prefix": [], "suffix": []}
                for i, sequence_kind in enumerate(sequence_kinds, start=1):
                    rule_kwargs[sequence_kind] = [ast.GlyphName(g) for g in make_glyphs(strip_split_comma(line[i]))]
                lookups, comment = self._parse_position_lookup_entries(rule_kwargs["glyphs"], line[1 + glyph_set_count :], lookup)
                if comment:
                    rules.append(comment)
                rules.append(ruleklass(lookups=lookups, **rule_kwargs))
            return rules
        if typ.endswith("class"):
            classes: dict[typing.Literal["glyphs", "prefix", "suffix"], dict[int, list[str]]] = {}
            class_kinds = {"class definition begin": "glyphs"}
            if is_chained:
                class_kinds["backtrackclass definition begin"] = "prefix"
                class_kinds["lookaheadclass definition begin"] = "suffix"
            while self.tokens.peeks()[0].lower() in class_kinds:
                kind = class_kinds[self.tokens.peek()[0].lower()]
                classes[kind] = self._parse_contextual_class()
            rules: list[RK] = []
            for line in self.tokens:
                assert line[0].lower().startswith("class"), line[0]
                if len(line) < 2 + glyph_set_count:
                    continue
                rule_kwargs = {"glyphs": [], "prefix": [], "suffix": []}
                for i, sequence_kind in enumerate(sequence_kinds, start=1):
                    class_sequence = int_split_comma(line[i])
                    rule_kwargs[sequence_kind] = []
                    for classnum in class_sequence:
                        class_glyphs = classes[sequence_kind][classnum]
                        if len(class_glyphs) == 1:
                            rule_kwargs[sequence_kind].append(ast.GlyphName(glyph=class_glyphs[0]))
                        else:
                            rule_kwargs[sequence_kind].append(ast.GlyphClass(glyphs=class_glyphs))
                lookups, comment = self._parse_position_lookup_entries(rule_kwargs["glyphs"], line[1 + glyph_set_count :], lookup)
                if comment:
                    rules.append(comment)
                rules.append(ruleklass(lookups=lookups, **rule_kwargs))
            return rules
        if typ.endswith("coverage"):
            # I'm not 100% sure this is correct for the non-chaining case.
            # But also I have been unable to find any examples of it actually in use,
            # which makes testing difficult.
            # https://github.com/Monotype/OpenType_Table_Source/issues/15
            rule_kwargs = {"glyphs": [], "prefix": [], "suffix": []}
            while self.tokens.peeks()[0].endswith("coverage definition begin"):
                typ = self.tokens.peek()[0][: -len("coverage definition begin")].lower()
                match (is_chained, typ):
                    case (False, ""):
                        bucket = "glyphs"
                    case (True, "backtrack"):
                        bucket = "prefix"
                    case (True, "input"):
                        bucket = "glyphs"
                    case (True, "lookahead"):
                        bucket = "suffix"
                bucket_glyphs = []
                with self.tokens.between("coverage definition"):
                    for line in self.tokens:
                        bucket_glyphs.append(make_glyph(line[0]))
                if len(bucket_glyphs) == 1:
                    rule_kwargs[bucket].append(ast.GlyphName(glyph=bucket_glyphs[0]))
                elif len(bucket_glyphs) > 1:
                    rule_kwargs[bucket].append(ast.GlyphClass(glyphs=bucket_glyphs))
            lines = list(self.tokens)
            assert len(lines) == 1
            line = lines[0]
            assert line[0].lower() == "coverage", line[0]
            lookups, comment = self._parse_position_lookup_entries(rule_kwargs["glyphs"], line[1:], lookup)
            # OpenType tables and Monotype syntax have backtrack tables in reverse order.
            # See the twobacktracks.txt test case.
            rule_kwargs["prefix"].reverse()
            rules = []
            if comment:
                rules.append(comment)
            rules.append(ruleklass(lookups=lookups, **rule_kwargs))
            return rules
        raise ParseError("Expected one of glyph, class, or coverage, but didn't get any of them.")


class GsubParser(LookupAndFeatureParser):
    def __init__(self, gsub_txt: str):
        super().__init__(gsub_txt)
        self._table_tag = "GSUB"

    def parse_lookup_subtable(self, lookup: Lookup, kind: str):
        parser = {
            "single": self.parse_single_substitution,
            "multiple": self.parse_multiple_substitution,
            "alternate": self.parse_alternate_substitution,
            "ligature": self.parse_ligature_substitution,
            "context": self.parse_contextual_substitution,
            "chained": self.parse_chaining_contextual_substitution,
            "reversechained": self.parse_reverse_chaining_single_substitution,
        }[kind]
        return parser(lookup)

    def parse_single_substitution(self, _lookup) -> list[ast.SingleSubstStatement]:
        glyphs = []
        replacements = []
        for line in self.tokens:
            assert len(line) == 2, line
            glyphs.append(make_glyph(line[0]))
            replacements.append(make_glyph(line[1]))
        if len(set(glyphs)) == len(set(replacements)):
            if len(set(glyphs)) == 1:
                # just one statement, so use format A
                return [
                    ast.SingleSubstStatement(
                        glyphs=[ast.GlyphName(glyph=glyphs[0])],
                        replace=[ast.GlyphName(glyph=replacements[0])],
                        prefix=[],
                        suffix=[],
                        forceChain=False,
                    )
                ]
            # there's a unique mapping of glyph to replacement, so we can use format C
            return [
                ast.SingleSubstStatement(
                    glyphs=[ast.GlyphClass(glyphs=glyphs)],
                    replace=[ast.GlyphClass(glyphs=replacements)],
                    prefix=[],
                    suffix=[],
                    forceChain=False,
                )
            ]
        if len(replacements) == 1:
            # format B!
            return [
                ast.SingleSubstStatement(
                    glyphs=[ast.GlyphClass(glyphs=glyphs)],
                    replace=[ast.GlyphName(glyph=replacements[0])],
                    prefix=[],
                    suffix=[],
                    forceChain=False,
                )
            ]
        # multiple format A
        return [
            ast.SingleSubstStatement(
                glyphs=[ast.GlyphName(glyph=g)], replace=[ast.GlyphName(glyph=r)], prefix=[], suffix=[], forceChain=False
            )
            for g, r in zip(glyphs, replacements, strict=True)
        ]

    def parse_multiple_substitution(self, _lookup) -> list[ast.MultipleSubstStatement]:
        rules = []
        for line in self.tokens:
            line = make_glyphs(line)
            rules.append(
                ast.MultipleSubstStatement(
                    glyph=ast.GlyphName(glyph=line[0]),
                    replacement=[ast.GlyphClass(glyphs=line[1:])],
                    prefix=[],
                    suffix=[],
                    forceChain=False,
                )
            )
        return rules

    def parse_alternate_substitution(self, _lookup) -> list[ast.AlternateSubstStatement]:
        rules = []
        for line in self.tokens:
            line = make_glyphs(line)
            rules.append(
                ast.AlternateSubstStatement(
                    glyph=ast.GlyphName(glyph=line[0]), replacement=ast.GlyphClass(glyphs=line[1:]), prefix=[], suffix=[]
                )
            )
        return rules

    def parse_ligature_substitution(self, _lookup) -> list[ast.LigatureSubstStatement]:
        rules = []
        for line in self.tokens:
            assert len(line) >= 2, line
            line = make_glyphs(line)
            rules.append(
                ast.LigatureSubstStatement(
                    glyphs=[ast.GlyphName(glyph=g) for g in line[1:]],
                    replacement=ast.GlyphName(glyph=line[0]),
                    prefix=[],
                    suffix=[],
                    forceChain=False,
                )
            )
        return rules

    def parse_contextual_substitution(self, lookup: Lookup):
        return self._parse_chaining(ast.ChainContextSubstStatement, lookup, is_chained=False)

    def parse_chaining_contextual_substitution(self, lookup: Lookup):
        return self._parse_chaining(ast.ChainContextSubstStatement, lookup, is_chained=True)

    def parse_reverse_chaining_single_substitution(self, _lookup):
        rules = []
        while self.tokens.peeks()[0].endswith("coverage definition begin"):
            rule_kwargs = {"glyphs": [], "old_prefix": [], "old_suffix": [], "replacements": []}
            typ = self.tokens.peek()[0][: -len("coverage definition begin")].lower()
            bucket = {"backtrack": "old_prefix", "lookahead": "old_suffix"}[typ]
            bucket_glyphs = []
            with self.tokens.between("coverage definition"):
                for line in self.tokens:
                    bucket_glyphs.append(make_glyph(line[0]))
            if len(bucket_glyphs) == 1:
                rule_kwargs[bucket].append(ast.GlyphName(glyph=bucket_glyphs[0]))
            elif len(bucket_glyphs) > 1:
                rule_kwargs[bucket].append(ast.GlyphClass(glyphs=bucket_glyphs))
            target_glyphs = []
            replacement_glyphs = []

            for line in self.tokens:
                assert len(line) == 2, line
                line = make_glyphs(line)
                target_glyphs.append(line[0])
                replacement_glyphs.append(line[1])

            if len(target_glyphs) == 1:
                rule_kwargs["glyphs"].append(ast.GlyphName(glyph=target_glyphs[0]))
            elif len(target_glyphs) > 1:
                rule_kwargs["glyphs"].append(ast.GlyphClass(glyphs=target_glyphs))
            if len(bucket_glyphs) == 1:
                rule_kwargs["replacements"].append(ast.GlyphName(glyph=replacement_glyphs[0]))
            elif len(bucket_glyphs) > 1:
                rule_kwargs["replacements"].append(ast.GlyphClass(glyphs=replacement_glyphs))
            rules.append(ast.ReverseChainSingleSubstStatement(**rule_kwargs))
        return rules


@dataclasses.dataclass(kw_only=True, frozen=True)
class PositionValue:
    value_record_attr: str
    value: int


class GposParser(LookupAndFeatureParser):
    def __init__(self, gpos_txt: str):
        super().__init__(gpos_txt)
        self._table_tag = "GPOS"

    def parse_lookup_subtable(self, lookup: Lookup, kind: str):
        parser = {
            "single": self.parse_single_position,
            "pair": self.parse_pair,
            "kernset": self.parse_kernset,
            "cursive": self.parse_cursive,
            "mark to base": self.parse_mark_to_base,
            "mark to ligature": self.parse_mark_to_ligature,
            "mark to mark": self.parse_mark_to_mark,
            "context": self.parse_contextual_position,
            "chained": self.parse_chaining_contextual_position,
        }[kind]
        return parser(lookup)

    def parse_single_position(self, _lookup) -> list[ast.SinglePosStatement]:
        attrmap = {"x placement": "xPlacement", "y placement": "yPlacement", "x advance": "xAdvance", "y advance": "yAdvance"}
        glyph_values: dict[str, list[PositionValue]] = {}
        for line in self.tokens:
            assert len(line) == 3, line
            operation = line[0]
            assert operation in attrmap
            op_attr = attrmap[operation]
            glyph = make_glyph(line[1])
            op_val = int(line[2])
            vr = PositionValue(value_record_attr=op_attr, value=op_val)
            glyph_values.setdefault(glyph, []).append(vr)

        values: dict[tuple[tuple[str, int], ...], list[str]] = {}
        for glyph, valuelist in glyph_values.items():
            key = tuple((pv.value_record_attr, pv.value) for pv in valuelist)
            values.setdefault(key, []).append(glyph)

        rules = []
        for valtuple, glyphlist in values.items():
            val = ast.ValueRecord(**dict(valtuple))
            if len(glyphlist) == 1:
                rules.append(ast.SinglePosStatement(pos=[(ast.GlyphName(glyphlist[0]), val)], prefix=[], suffix=[], forceChain=False))
            else:
                rules.append(ast.SinglePosStatement(pos=[(ast.GlyphClass(glyphlist), val)], prefix=[], suffix=[], forceChain=False))
        return rules

    def parse_pair(self, _lookup) -> list[ast.PairPosStatement]:
        attrmap = {"x placement": "xPlacement", "y placement": "yPlacement", "x advance": "xAdvance", "y advance": "yAdvance"}
        typ = self.tokens.peeks()[0].split()[0].lower()
        if typ in ("left", "right"):
            # glyphclasses could be a nice optimization, but the fea compiler always uses subtables for them
            # so that's semantically different and we won't risk that here.
            values: dict[tuple[str, str], tuple[ast.ValueRecord, ast.ValueRecord]] = {}
            for line in self.tokens:
                assert len(line) == 4, line
                side = line[0].split()[0].lower()
                assert side in ("left", "right"), side
                operation = line[0].removeprefix(side + " ")
                op_attr = attrmap[operation]
                glyph1, glyph2 = make_glyphs(line[1:3])
                pair = (glyph1, glyph2)
                if pair not in values:
                    values[pair] = (ast.ValueRecord(), ast.ValueRecord())
                left_vr, right_vr = values[pair]
                target_vr = left_vr if side == "left" else right_vr
                setattr(target_vr, op_attr, int(line[3]))
                values[pair] = (left_vr, right_vr)
            rules = []
            for pair, vrs in values.items():
                rule_kwargs = {
                    "glyphs1": ast.GlyphName(pair[0]),
                    "glyphs2": ast.GlyphName(pair[1]),
                    "valuerecord1": None,
                    "valuerecord2": None,
                }
                if vrs[0]:
                    rule_kwargs["valuerecord1"] = vrs[0]
                if vrs[1]:
                    rule_kwargs["valuerecord2"] = vrs[1]
                rules.append(ast.PairPosStatement(**rule_kwargs))
            return rules
        if typ.endswith("class"):
            classes: dict[typing.Literal["first", "second"], dict[int, list[str]]] = {}
            while self.tokens.peeks()[0].endswith("class definition begin"):
                kind = self.tokens.peek()[0][: -len("class definition begin")].lower()
                classes[kind] = self._parse_contextual_class()
            values: dict[tuple[int, int], tuple[ast.ValueRecord, ast.ValueRecord]] = {}
            for line in self.tokens:
                assert len(line) == 4, line
                side = line[0].split()[0].lower()
                assert side in ("left", "right"), side
                operation = line[0].removeprefix(side + " ")
                op_attr = attrmap[operation]
                class1, class2, value = (int(x) for x in line[1:4])
                pair = (class1, class2)
                if pair not in values:
                    values[pair] = (ast.ValueRecord(), ast.ValueRecord())
                left_vr, right_vr = values[pair]
                target_vr = left_vr if side == "left" else right_vr
                setattr(target_vr, op_attr, value)
                values[pair] = (left_vr, right_vr)
            rules = []
            for (class1, class2), vrs in values.items():
                rule_kwargs = {
                    "valuerecord1": None,
                    "valuerecord2": None,
                }
                first = classes["first"][class1]
                rule_kwargs["glyphs1"] = ast.GlyphClass(first) if len(first) > 1 else ast.GlyphName(first[0])
                second = classes["second"][class2]
                rule_kwargs["glyphs2"] = ast.GlyphClass(second) if len(second) > 1 else ast.GlyphName(second[0])
                if vrs[0]:
                    rule_kwargs["valuerecord1"] = vrs[0]
                if vrs[1]:
                    rule_kwargs["valuerecord2"] = vrs[1]
                rules.append(ast.PairPosStatement(**rule_kwargs))
            return rules
        raise ParseError("Failed to parse pair positioning")

    def parse_kernset(self, _lookup):
        typ = self.tokens.peeks()[0].split()[0].lower()
        if typ in ("left", "right"):
            with self.tokens.until(("firstclass definition begin", "secondclass definition begin")):
                return self.parse_pair(_lookup)
        return self.parse_pair(_lookup)

    @staticmethod
    def _make_anchor(data):
        x, y = int_split_comma(data[0])
        kw = {"x": x, "y": y}
        if len(data) > 1 and data[1] != "":
            kw["contour_point"] = int(data[1])
        return AnchorPoint(**kw)

    def parse_cursive(self, _lookup):
        records = {}
        for line in self.tokens:
            assert len(line) in [3, 4], line
            kind = line[0].lower() + "Anchor"
            glyph = make_glyph(line[1])
            if glyph not in records:
                records[glyph] = {"glyphclass": ast.GlyphName(glyph), "entryAnchor": None, "exitAnchor": None}
            if records[glyph][kind] is not None:
                raise ParseError(f"Already saw {kind} for {glyph}")
            records[glyph][kind] = self._make_anchor(line[2:]).to_ast()
        return [ast.CursivePosStatement(**kw) for kw in records.values()]

    def _parse_mark_to_something[RK: (ast.MarkBasePosStatement, ast.MarkLigPosStatement, ast.MarkMarkPosStatement)](
        self, ruleklass: type[RK]
    ):
        mark_anchor_glyphs: dict[tuple[str, AnchorPoint], list[str]] = {}
        loose_bases: dict[str, list[tuple[str, AnchorPoint] | tuple[str, int, int, AnchorPoint]]] = {}
        anchor_class_names: dict[int, str] = {}
        for line in self.tokens:
            typ = line[0]
            assert typ in ("mark", "base", "ligature")
            glyph = make_glyph(line[1])
            extraItems = 2 if typ == "ligature" else 0
            extras = tuple(int(i) for i in line[2 : 2 + extraItems])
            klass = int(line[2 + extraItems])
            if klass not in anchor_class_names:
                anchor_class_names[klass] = self._name_mark_class()
            anchor = self._make_anchor(line[3 + extraItems :])
            if typ == "mark":
                mark_anchor_glyphs.setdefault((anchor_class_names[klass], anchor), []).append(glyph)
            else:
                val = (anchor_class_names[klass], *extras, anchor)
                loose_bases.setdefault(glyph, []).append(val)

        # Mark
        mark_classes: dict[str, ast.MarkClass] = {}
        marks: dict[str, list[tuple[list[str], AnchorPoint]]] = {}
        for (classname, anchor), glyphs in mark_anchor_glyphs.items():
            marks.setdefault(classname, []).append((glyphs, anchor))
        for classname in marks:
            mark_class = make_mark_class(classname, marks[classname])
            mark_classes[classname] = mark_class
            self.mark_classes.append(mark_class)

        # Base
        # invert the loose_bases dict so we can now group by the totality of anchor points on the base glyph
        anchor_bases: dict[tuple[tuple[str, AnchorPoint] | tuple[str, int, int, AnchorPoint]], list[str]] = {}
        for glyph, anchorkey in loose_bases.items():
            anchorkey = tuple(anchorkey)
            anchor_bases.setdefault(anchorkey, []).append(glyph)

        rules: list[RK] = []
        for anchors, glyphs in anchor_bases.items():
            base = ast.GlyphClass(glyphs) if len(glyphs) > 1 else ast.GlyphName(glyphs[0])
            if ruleklass in (ast.MarkBasePosStatement, ast.MarkMarkPosStatement):
                marks = [(anchor.to_ast(), mark_classes[classname]) for (classname, anchor) in anchors]
                rules.append(ruleklass(base, marks))
            elif ruleklass is ast.MarkLigPosStatement:
                marks = []
                for classname, compnum, totalcomps, anchor in anchors:
                    while len(marks) < totalcomps:
                        marks.append([])
                    idx = compnum - 1
                    marks[idx].append((anchor.to_ast(), mark_classes[classname]))
                rules.append(ruleklass(base, marks))
            else:
                raise ParseError(ruleklass)
        return rules

    def parse_mark_to_base(self, _lookup):
        return self._parse_mark_to_something(ast.MarkBasePosStatement)

    def parse_mark_to_ligature(self, _lookup):
        return self._parse_mark_to_something(ast.MarkLigPosStatement)

    def parse_mark_to_mark(self, _lookup):
        return self._parse_mark_to_something(ast.MarkMarkPosStatement)

    def parse_contextual_position(self, lookup: Lookup):
        return self._parse_chaining(ast.ChainContextPosStatement, lookup, is_chained=False)

    def parse_chaining_contextual_position(self, lookup: Lookup):
        return self._parse_chaining(ast.ChainContextPosStatement, lookup, is_chained=True)


class GdefParser:
    def __init__(self, gdef_txt: str):
        self.tokens = Tokenizer(gdef_txt)

    def parse(self):
        self.glyph_definitions = GlyphDefinitions()
        fields = {
            "class definition begin": functools.partial(self.parse_class_def, "glyph_classes"),
            "attachment list begin": self.parse_attach_list,
            "carets begin": self.parse_caret_list,
            "mark attachment class definition begin": functools.partial(self.parse_class_def, "mark_attachment_classes"),
            "markfilter set definition begin": self.parse_mark_filtering_sets,
        }
        while self.tokens.peek() is not None:
            typ = self.tokens.peek()[0].lower()
            if typ not in fields:
                logger.debug("Skipping %s", typ)
                next(self.tokens)
                continue
            parser = fields[typ]
            parser()
        return self.glyph_definitions

    def parse_class_def(self, target_attr: str):
        seen_glyphs: set[str] = set()
        class_glyphs: list[list[str]] = []
        with self.tokens.between("class definition"):
            for line in self.tokens:
                glyph = make_glyph(line[0])
                classnum = int(line[1])
                if glyph in seen_glyphs:
                    raise ParseError(f"Already saw glyph {glyph}")
                while len(class_glyphs) < classnum:
                    class_glyphs.append([])
                class_glyphs[classnum - 1].append(glyph)
                seen_glyphs.add(glyph)
        if seen_glyphs:
            if target_attr == "glyph_classes":
                # make sure it always has 4
                while len(class_glyphs) < 4:
                    class_glyphs.append([])
                if len(class_glyphs) > 4:
                    raise ParseError("Found more than four classes of glyph; not allowed!")
            tuplized = tuple(tuple(c) for c in class_glyphs)
            setattr(self.glyph_definitions, target_attr, tuplized)

    def parse_attach_list(self):
        points = {}
        with self.tokens.between("attachment list"):
            for line in self.tokens:
                glyph = make_glyph(line[0])
                assert glyph not in points, glyph
                points[glyph] = [int(i) for i in line[1:]]
        if points:
            self.glyph_definitions.attachment_points = points

    def parse_caret_list(self):
        carets = {}
        with self.tokens.between("carets"):
            for line in self.tokens:
                glyph = make_glyph(line[0])
                assert glyph not in carets, glyph
                num = int(line[1])
                thisCarets = [int(i) for i in line[2:]]
                assert num == len(thisCarets), line
                carets[glyph] = thisCarets
        if carets:
            self.glyph_definitions.ligature_carets = carets

    def parse_mark_filtering_sets(self):
        sets = {}
        with self.tokens.between("set definition"):
            for line in self.tokens:
                assert len(line) == 2, line
                glyph = make_glyph(line[0])
                st = int(line[1])
                if st not in sets:
                    sets[st] = set()
                sets[st].add(glyph)
        if sets:
            self.glyph_definitions.mark_filter_sets = sets


class Tokenizer:
    def __init__(self, content: str):
        lines = content.splitlines(keepends=True)
        self.lines = iter(lines)
        self.line = ""
        self.lineno = 0
        self.stoppers = []
        self.buffer = None

    def __iter__(self):
        return self

    def _next_line(self):
        self.lineno += 1
        line = self.line = next(self.lines)
        line = [s.strip() for s in line.split("\t")]
        if len(line) == 1 and not line[0]:
            del line[0]
        if line and not line[-1]:
            logger.warning("trailing tab found on line %d: %s", self.lineno, self.line)
            while line and not line[-1]:
                del line[-1]
        return line

    def _next_nonempty(self):
        while True:
            line = self._next_line()
            # Skip comments and empty lines
            if line and line[0] and (line[0][0] != "%" or line[0] == "% subtable"):
                return line

    def _next_buffered(self):
        if self.buffer:
            ret = self.buffer
            self.buffer = None
            return ret
        return self._next_nonempty()

    def __next__(self):
        line = self._next_buffered()
        if line[0].lower() in self.stoppers:
            self.buffer = line
            raise StopIteration
        return line

    def next(self):
        return self.__next__()

    def peek(self):
        if not self.buffer:
            try:
                self.buffer = self._next_nonempty()
            except StopIteration:
                return None
        if self.buffer[0].lower() in self.stoppers:
            return None
        return self.buffer

    def peeks(self):
        ret = self.peek()
        return ret if ret is not None else ("",)

    @contextmanager
    def between(self, tag):
        start = tag + " begin"
        end = tag + " end"
        self.expectendswith(start)
        self.stoppers.append(end)
        yield
        del self.stoppers[-1]
        self.expect(tag + " end")

    @contextmanager
    def until(self, tags):
        if type(tags) is not tuple:
            tags = (tags,)
        self.stoppers.extend(tags)
        yield
        del self.stoppers[-len(tags) :]

    def expect(self, s):
        line = next(self)
        tag = line[0].lower()
        assert tag == s, "Expected '%s', got '%s'" % (s, tag)
        return line

    def expectendswith(self, s):
        line = next(self)
        tag = line[0].lower()
        assert tag.endswith(s), "Expected '*%s', got '%s'" % (s, tag)
        return line


class Parser:
    units_per_em: Optional[int | float]
    gdef: Optional[str]
    gsub: Optional[str]
    gpos: Optional[str]

    def __init__(self):
        self.gdef = None
        self.gsub = None
        self.gpos = None
        self.units_per_em = None
        self.featurefile = ast.FeatureFile()

    def set_units_per_em(self, value: Optional[int | float]):
        self.units_per_em = value
        return self

    def load_units_per_em_from_ufo(self, ufo: ufoLib2.Font):
        return self.set_units_per_em(ufo.info.unitsPerEm)

    def add_GDEF(self, gdef_path: PathLike):
        self.gdef = pathlib.Path(gdef_path).read_text()
        return self

    def add_GSUB(self, gsub_path: PathLike):
        self.gsub = pathlib.Path(gsub_path).read_text()
        return self

    def add_GPOS(self, gpos_path: PathLike):
        self.gpos = pathlib.Path(gpos_path).read_text()
        return self

    def add_plist(self, plist_path: PathLike, font_name: Optional[str] = None):
        plist_path = pathlib.Path(plist_path)
        with plist_path.open("rb") as plist_file:
            raw_plist = fontTools.misc.plistlib.load(plist_file)
        font_plist: dict[str, str]
        if font_name is None:
            if len(raw_plist) != 1:
                raise ValueError(
                    "Cannot load features from a plist file unless font name is specified or the plist contains only one font."
                )
            font_plist = list(raw_plist.values())[0]
        else:
            font_plist = raw_plist[font_name]
        for table_name, table_filename in font_plist.items():
            table_path = plist_path.parent / table_filename
            match table_name:
                case "GDEF":
                    self.add_GDEF(table_path)
                case "GSUB":
                    self.add_GSUB(table_path)
                case "GPOS":
                    self.add_GPOS(table_path)
                case _:
                    raise KeyError(f"Unexpected table key {table_name}")
        return self

    @staticmethod
    def parse_header(to_parse: str, expected_table: str):
        rest = None
        if "\n" in to_parse:
            to_parse, _nl, rest = to_parse.partition("\n")
        match to_parse.split():
            case ("Font", "Chef", "Table", found_table):
                pass
            case ("FontDame", found_table, "table"):
                pass
            case _:
                raise ParseError("Expected a valid header line")
        if found_table != expected_table:
            raise ValueError(f"Expected {expected_table} but got {found_table}")
        return rest

    @staticmethod
    def parse_units_per_em(to_parse: str):
        match = re.search("^EM\t(\\d+)\n$", to_parse, re.M)
        if not match:
            return None
        return require_int(match.group(1))

    def parse_GDEF(self):
        actual_gdef = self.parse_header(self.gdef, "GDEF")
        return FeatureFile(table_tag="GDEF", glyph_definitions=GdefParser(actual_gdef).parse())

    def parse_GSUB(self):
        actual_gsub = self.parse_header(self.gsub, "GSUB")
        return GsubParser(actual_gsub).parse()

    def parse_GPOS(self):
        actual_gpos = self.parse_header(self.gpos, "GPOS")
        parsed_units = self.parse_units_per_em(actual_gpos)
        if parsed_units is not None:
            if self.units_per_em is None:
                logger.warning(
                    "Found EM statement in GPOS file, but units_per_em was not specified to the parser; cannot check for consistency."
                )
            elif parsed_units != self.units_per_em:
                raise ParseError(f"Found EM {parsed_units} in GPOS file, but units_per_em was set to {self.units_per_em}.")
        return GposParser(actual_gpos).parse()

    def parse(self):
        ffs: list[FeatureFile] = []
        if self.gdef:
            ffs.append(self.parse_GDEF())
        if self.gsub:
            ffs.append(self.parse_GSUB())
        if self.gpos:
            ffs.append(self.parse_GPOS())
        return to_ast(*ffs)
