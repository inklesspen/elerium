# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import dataclasses
import enum
import logging
from collections.abc import Sequence
from functools import cached_property
from typing import Optional, cast

import ufoLib2.objects
from fontTools.feaLib import ast
from fontTools.ttLib.tables.G_D_E_F_ import table_G_D_E_F_
from fontTools.ttLib.tables.G_S_U_B_ import table_G_S_U_B_
from fontTools.unicodedata import ot_tag_to_script
from ufo2ft.fontInfoData import getAttrWithFallback
from ufo2ft.util import (
    classifyGlyphs,
    closeGlyphsOverGSUB,
    compileGDEF,
    compileGSUB,
    makeOfficialGlyphOrder,
    makeUnicodeToGlyphNameMapping,
    unicodeScriptExtensions,
)

from .svg import GlyphSvg
from .util import parse_ufo_features

logger = logging.getLogger(__name__)

VIEWABLE_FEATURES = frozenset(("mark",))


class GlyphClass(enum.IntEnum):
    BASE = 1
    LIGATURE = 2
    MARK = 3
    COMPONENT = 4


@dataclasses.dataclass()
class Font:
    """UFO wrapper to help with retrieving various OpenType features from the UFO."""

    ufo: ufoLib2.objects.Font
    _glyph_cache: dict[str, GlyphSvg] = dataclasses.field(default_factory=dict, init=False, repr=False, compare=False)

    @cached_property
    def font_name(self) -> str:
        return getAttrWithFallback(self.ufo.info, "postscriptFullName")

    @cached_property
    def all_glyphs(self) -> list[str]:
        return makeOfficialGlyphOrder(self.ufo)

    @cached_property
    def cmap(self) -> dict[int, str]:
        return makeUnicodeToGlyphNameMapping(self.ufo, self.all_glyphs)

    @cached_property
    def features(self):
        return parse_ufo_features(self.ufo)

    @cached_property
    def _script_glyphs(self) -> dict[str, set[str]]:
        return classifyGlyphs(unicodeScriptExtensions, self.cmap, self._gsub)

    @cached_property
    def supported_scripts(self) -> frozenset[str]:
        """Returns a set of Unicode script codes supported by the font."""
        scripts = set()
        if self.features is not None:
            for stmt in self.features.statements:
                if isinstance(stmt, ast.LanguageSystemStatement) and (code := ot_tag_to_script(stmt.script)):
                    scripts.add(code)
        if scripts:
            for meta_script in ["Zinh", "Zyyy", "Zzzz"]:
                if meta_script in self._script_glyphs:
                    scripts.add(meta_script)
            return frozenset(scripts)
        threshold = len(self.all_glyphs) // 100
        for code in self._script_glyphs:
            if len(self._script_glyphs[code]) >= threshold:
                scripts.add(code)
        return frozenset(scripts)

    def script_glyphs(self, script: str) -> frozenset[str]:
        """Returns a set of glyphs which belong to this script."""
        return frozenset(self._script_glyphs[script])

    @cached_property
    def typeable_glyphs(self) -> frozenset[str]:
        """Returns a set of all glyphs which can be typed, either because they have a Unicode codepoint mapping, or there is a substitution rule which produces them from typeable glyphs."""
        glyphs = set(self.cmap.values())
        closeGlyphsOverGSUB(self._gsub, glyphs)
        return frozenset(glyphs)

    @cached_property
    def _gsub(self) -> Optional[table_G_S_U_B_]:
        if self.features is None:
            return None
        return compileGSUB(self.features, self.all_glyphs)

    @cached_property
    def _gdef(self) -> Optional[table_G_D_E_F_]:
        if self.features is None:
            # TODO: maybe use ufo2ft's gdefFeatureWriter here
            return None
        return compileGDEF(self.features, self.all_glyphs)

    @cached_property
    def glyph_classes(self):
        if self._gdef is None:
            return None
        return {glyphname: GlyphClass(classnum) for glyphname, classnum in self.gdef.table.GlyphClassDef.classDefs.items()}

    def __getitem__(self, glyph_name: str) -> "GlyphSvg":
        self.ufo[glyph_name]  # existence check
        if glyph_name not in self._glyph_cache:
            self._glyph_cache[glyph_name] = GlyphSvg.draw_glif(self.ufo, glyph_name)
        return self._glyph_cache[glyph_name]

    @cached_property
    def viewable_features(self) -> tuple["Feature", ...]:
        viewable = {}
        for stmt in self.features.statements:
            if not isinstance(stmt, ast.FeatureBlock):
                continue
            if stmt.name not in VIEWABLE_FEATURES:
                continue
            viewable.setdefault(stmt.name, []).append(stmt)
        return tuple(Feature.from_feature_blocks(viewable[tag]) for tag in sorted(viewable))


@dataclasses.dataclass(kw_only=True)
class Feature:
    tag: str
    lookups: tuple["Lookup", ...]

    @classmethod
    def from_feature_blocks(cls, feature_blocks: Sequence[ast.FeatureBlock]):
        tags = frozenset(fb.name for fb in feature_blocks)
        if len(tags) != 1:
            raise ValueError("All feature blocks must be of the same tag")
        tag = feature_blocks[0].name
        lookups = []
        for fb in feature_blocks:
            current_script = None
            for stmt in fb.statements:
                if isinstance(stmt, ast.ScriptStatement):
                    current_script = ot_tag_to_script(stmt.script)
                elif isinstance(stmt, ast.LanguageStatement):
                    continue
                elif isinstance(stmt, ast.LookupReferenceStatement):
                    lookups.append(Lookup.from_lookup_reference(stmt, script=current_script))
                else:
                    logger.warning("Unexpected statement %r in feature %s", stmt, tag)

        return cls(tag=tag, lookups=tuple(lookups))


class LookupFlagValue(enum.IntFlag):
    RIGHT_TO_LEFT = 1
    IGNORE_BASE_GLYPHS = 2
    IGNORE_LIGATURES = 4
    IGNORE_MARKS = 8


@dataclasses.dataclass(kw_only=True)
class LookupFlag:
    flag: LookupFlagValue
    mark_attachment: Optional[ast.GlyphClass | ast.GlyphClassName]
    mark_filtering_set: Optional[ast.GlyphClass | ast.GlyphClassName]

    @classmethod
    def from_ast(cls, stmt: ast.LookupFlagStatement):
        return cls(flag=LookupFlagValue(stmt.value), mark_attachment=stmt.markAttachment, mark_filtering_set=stmt.markFilteringSet)


@dataclasses.dataclass(kw_only=True)
class Lookup:
    name: str
    flags: Optional[LookupFlag] = None
    script: Optional[str] = None
    rules: tuple[ast.Statement, ...]

    @classmethod
    def from_lookup_reference(cls, stmt: ast.LookupReferenceStatement, script: Optional[str] = None):
        lookup_block = cast("ast.LookupBlock", stmt.lookup)
        flags = None
        rules = []
        for rule in lookup_block.statements:
            if isinstance(rule, ast.LookupFlagStatement):
                flags = LookupFlag.from_ast(rule)
                continue
            rules.append(rule)
        return cls(name=lookup_block.name, flags=flags, script=script, rules=tuple(rules))
