# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import logging
import unicodedata
from typing import Optional, cast

import fontTools.unicodedata
import ufoLib2.objects
import webob.dec
from fontTools.feaLib import ast
from lxml.html import HtmlElement
from lxml.html import builder as E
from lxml.html import tostring as html_tostring
from webob.exc import HTTPBadRequest, HTTPNotFound
from webob.request import Request
from webob.response import Response

from .otufo import Font, LookupFlagValue
from .svg import GlyphSvg, NamedAnchor

logger = logging.getLogger(__name__)

PAGE_STYLES = """\
svg.rendered {
  max-height: 600px;
  max-width: 400px;
}
"""


def codepoint_info(codepoint: int) -> HtmlElement:
    try:
        charname = unicodedata.name(chr(codepoint))
    except ValueError:
        logger.warning("Codepoint U+%04X has no name in the unicode database.", codepoint)
        charname = "[No character name]"
    formatted = "U+{:04X}".format(codepoint)
    return E.DIV(
        E.CLASS("card"),
        E.DIV(
            E.CLASS("card-body"),
            E.H5(
                E.CLASS("card-title"),
                E.A(
                    formatted,
                    {
                        "class": "codepoint",
                        "href": f"https://codepoints.net/{formatted}",
                    },
                ),
            ),
            E.P(E.CLASS("card-text character-name"), charname),
        ),
    )


def ligature_info(codepoints: tuple[int, ...]) -> HtmlElement:
    return E.DIV(E.CLASS("card-group"), *[codepoint_info(codepoint) for codepoint in codepoints])


def glyph_unicode_info(glyph_svg: GlyphSvg) -> HtmlElement:
    codepoints = []
    for alternative in glyph_svg.unicodes:
        if isinstance(alternative, int):
            codepoints.append(codepoint_info(alternative))
        else:
            # tuple of ints: a ligature
            codepoints.append(ligature_info(alternative))

    container = E.DIV(E.CLASS("hstack gap-3 glyph-info"), E.SPAN(E.CLASS("glyphname"), glyph_svg.glyph.name))
    if codepoints:
        container.append(E.DIV(E.CLASS("vr")))
        if len(codepoints) == 1:
            container.append(codepoints[0])
        else:
            container.append(E.DIV(E.CLASS("vstack gap-2"), *codepoints))
    return container


def navbar(font: Font) -> HtmlElement:
    nav_elements = []
    scripts = sorted(font.supported_scripts, key=fontTools.unicodedata.Scripts.VALUES.index)
    all_glyphs_scripts = [
        E.LI(E.A(E.CLASS("dropdown-item"), fontTools.unicodedata.script_name(script), href=f"/glyphs?script={script}"))
        for script in scripts
    ]
    nav_elements.append(
        E.LI(
            E.CLASS("nav-item dropdown"),
            E.A(
                E.CLASS("nav-link dropdown-toggle"),
                "Glyphs",
                {"href": "#", "role": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"},
            ),
            E.UL(
                E.CLASS("dropdown-menu"),
                E.LI(E.A(E.CLASS("dropdown-item"), "All Glyphs", href="/glyphs")),
                E.LI(E.HR(E.CLASS("dropdown-divider"))),
                *all_glyphs_scripts,
            ),
        )
    )
    for feature in font.viewable_features:
        lookup_lis = [
            E.LI(
                E.A(
                    E.CLASS("dropdown-item"),
                    " — ".join([lookup.name, fontTools.unicodedata.script_name(lookup.script)])
                    if lookup.script is not None
                    else lookup.name,
                    href=f"/lookup?feature={feature.tag}&name={lookup.name}",
                )
            )
            for lookup in feature.lookups
        ]
        nav_elements.append(
            E.LI(
                E.CLASS("nav-item dropdown"),
                E.A(
                    E.CLASS("nav-link dropdown-toggle"),
                    f"Feature: {feature.tag}",
                    {"href": "#", "role": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"},
                ),
                E.UL(
                    E.CLASS("dropdown-menu"),
                    *lookup_lis,
                ),
            )
        )

    return E.E.nav(
        E.CLASS("navbar navbar-expand sticky-top bg-body-tertiary"),
        E.DIV(
            E.CLASS("container-fluid"),
            E.A(E.CLASS("navbar-brand"), font.font_name, href="/"),
            E.DIV(E.CLASS("collapse navbar-collapse"), E.UL(E.CLASS("navbar-nav me-auto"), *nav_elements)),
        ),
    )


def page_structure(font: Font, content: HtmlElement) -> str:
    doc = E.HTML(
        E.HEAD(
            E.META(charset="utf-8"),
            E.META(name="viewport", content="width=device-width, initial-scale=1"),
            E.TITLE(f"{font.font_name} OpenType Features"),
            E.LINK(
                rel="stylesheet",
                crossorigin="anonymous",
                href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
            ),
            E.STYLE(PAGE_STYLES),
        ),
        E.BODY(
            navbar(font),
            content,
            E.SCRIPT(
                crossorigin="anonymous",
                src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
            ),
        ),
        lang="en",
    )
    return html_tostring(doc, doctype="<!doctype html>", pretty_print=True)


def render_mark_to_base(font: Font, rule: ast.MarkBasePosStatement):
    row = E.DIV(E.CLASS("row"))
    anchors = []
    for anchor, mark_class in rule.marks:
        anchors.append(NamedAnchor(x=anchor.x, y=anchor.y, name=mark_class.name))
    glyphs = []
    if isinstance(rule.base, ast.GlyphName):
        glyphs.append(rule.base.glyph)
    elif isinstance(rule.base, ast.GlyphClass):
        glyphs.extend(rule.base.glyphs)
    else:
        raise TypeError(type(rule.base))
    for glyphname in glyphs:
        glyph_svg = font[glyphname]
        svg_el = glyph_svg.draw_origin_and_anchors(*anchors)
        svg_el.set("class", "card-img-bottom rendered")
        svg_card = E.DIV(
            E.CLASS("card"),
            E.DIV(E.CLASS("card-body"), glyph_unicode_info(glyph_svg)),
            svg_el,
        )
        row.append(E.DIV(E.CLASS("col"), svg_card))

    return row


def render_mark_class(font: Font, mark_class: ast.MarkClass):
    container = E.DIV(E.P(mark_class.name))
    row = E.DIV(E.CLASS("row"))
    for definition in mark_class.definitions:
        definition = cast("ast.MarkClassDefinition", definition)
        anchor = NamedAnchor(x=definition.anchor.x, y=definition.anchor.y, name=mark_class.name)
        assert isinstance(definition.glyphs, ast.GlyphClass)
        for glyphname in definition.glyphs.glyphs:
            glyph_svg = font[glyphname]
            svg_el = glyph_svg.draw_origin_and_anchors(anchor)
            svg_el.set("class", "card-img-bottom rendered")
            svg_card = E.DIV(
                E.CLASS("card"),
                E.DIV(E.CLASS("card-body"), glyph_unicode_info(glyph_svg), E.DIV(E.CLASS("card-text"), f"({anchor.x}, {anchor.y})")),
                svg_el,
            )
            row.append(E.DIV(E.CLASS("col"), svg_card))
    container.append(row)
    return container


def render_unsupported_rule(rule: ast.Statement):
    return E.P(f"Rules of type {type(rule)} are not yet supported.", E.BR(), E.CODE(rule.asFea()))


def render_lookup(font: Font, feature: str, lookup: str):
    logger.debug("Looking for lookup %s in feature %s", lookup, feature)
    lookup_obj = None
    for feature_obj in font.viewable_features:
        if feature_obj.tag != feature:
            continue
        for candidate in feature_obj.lookups:
            if candidate.name == lookup:
                lookup_obj = candidate
                break
    if lookup_obj is None:
        raise KeyError(f"Cannot find feature {feature} with lookup {lookup}")
    container = E.DIV(E.CLASS("container"))
    container.append(E.H1(lookup_obj.name))
    if lookup_obj.flags:
        lookup_flags = []
        if lookup_obj.flags.flag & LookupFlagValue.RIGHT_TO_LEFT:
            lookup_flags.append(E.LI("Right-to-Left"))
        if lookup_obj.flags.flag & LookupFlagValue.IGNORE_BASE_GLYPHS:
            lookup_flags.append(E.LI("Ignore Base Glyphs"))
        if lookup_obj.flags.flag & LookupFlagValue.IGNORE_LIGATURES:
            lookup_flags.append(E.LI("Ignore Ligatures"))
        if lookup_obj.flags.flag & LookupFlagValue.IGNORE_MARKS:
            lookup_flags.append(E.LI("Ignore Marks"))
        if lookup_obj.flags.mark_attachment:
            lookup_flags.append(E.LI(f"Mark Attachment: {lookup_obj.flags.mark_attachment.asFea()}"))
        if lookup_obj.flags.mark_filtering_set:
            lookup_flags.append(E.LI(f"Mark Filtering Set: {lookup_obj.flags.mark_filtering_set.asFea()}"))
        if lookup_flags:
            container.append(E.UL(*lookup_flags))
    mark_classes = []
    for rule in lookup_obj.rules:
        if isinstance(rule, ast.MarkBasePosStatement):
            for _anchor, mark_class in rule.marks:
                if mark_class not in mark_classes:
                    mark_classes.append(mark_class)
    for mark_class in mark_classes:
        container.append(render_mark_class(font, mark_class))

    for rule in lookup_obj.rules:
        if isinstance(rule, ast.MarkBasePosStatement):
            container.append(render_mark_to_base(font, rule))
        else:
            container.append(render_unsupported_rule(rule))
    return page_structure(font, container)


def render_all_glyphs(font: Font, script: Optional[str] = None):
    container = E.DIV(E.CLASS("container"))

    script_glyphs = None if script is None else font.script_glyphs(script)

    for glyphname in font.all_glyphs:
        if glyphname not in font.typeable_glyphs:
            continue
        if script_glyphs is not None and glyphname not in script_glyphs:
            continue
        glyph_svg = font[glyphname]
        svg_el = glyph_svg.draw_origin()
        svg_el.set("class", "rendered")
        container.append(E.DIV(glyph_unicode_info(glyph_svg), svg_el))
    return page_structure(font, container)


def render_font_info(font: Font):
    container = E.DIV(E.CLASS("container"))
    scripts = sorted(font.supported_scripts, key=fontTools.unicodedata.Scripts.VALUES.index)
    script_names = ", ".join(fontTools.unicodedata.script_name(script) for script in scripts)
    container.append(
        E.DIV(
            E.CLASS("card"),
            E.DIV(
                E.CLASS("card-body"),
                E.H5(E.CLASS("card-title"), font.font_name),
                E.P(
                    E.CLASS("card-text"),
                    E.UL(
                        E.CLASS("list-group list-group-flush"),
                        E.LI(E.CLASS("list-group-item"), f"Glyphs: {len(font.all_glyphs)}"),
                        E.LI(E.CLASS("list-group-item"), f"Supported Scripts: {script_names}"),
                    ),
                ),
            ),
        )
    )
    return page_structure(font, container)


class Viewer:
    def __init__(self, ufo: ufoLib2.objects.Font):
        self.font = Font(ufo)

    @webob.dec.wsgify
    def __call__(self, req: Request):
        match req.path_info:
            case "/":
                return Response(render_font_info(self.font))
            case "/glyphs":
                script = None
                if "script" in req.GET:
                    try:
                        script = req.GET.getone("script")
                    except KeyError:
                        return HTTPBadRequest()
                return Response(render_all_glyphs(self.font, script=script))
            case "/lookup":
                feature = req.GET.getone("feature")
                lookup = req.GET.getone("name")
                try:
                    return Response(render_lookup(self.font, feature, lookup))
                except KeyError:
                    return HTTPBadRequest()
        return HTTPNotFound(comment=req.path_info)

    def serve(self, port: int):
        import waitress

        waitress.serve(self, port=port)
