# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import dataclasses
import logging

from fontTools.misc.arrayTools import rectCenter
from fontTools.pens.svgPathPen import SVGPathPen
from lxml import etree
from ufoLib2.objects import Font, Glyph, Point
from ufoLib2.objects.misc import BoundingBox, unionBounds

from .util import find_glyph_codepoints

logger = logging.getLogger(__name__)

ORIGIN_STYLE = "stroke: blue; stroke-width: 5px"
ANCHOR_STYLE = "fill: red;"
ANCHOR_TEXT_STYLE = "font-size: 40pt; fill: red;"


@dataclasses.dataclass(kw_only=True, frozen=True)
class NamedAnchor:
    x: int
    y: int
    name: str

    @property
    def anchor_bounds(self):
        return BoundingBox(xMin=self.x - 100, xMax=self.x + 100, yMin=self.y - 100, yMax=self.y + 100)


@dataclasses.dataclass(kw_only=True)
class GlyphSvg:
    glyph: Glyph
    unicodes: tuple[int | tuple[int, ...], ...]
    bounds: BoundingBox
    d: str

    @classmethod
    def draw_glif(cls, ufo: Font, glyph_name: str):
        glyph = ufo[glyph_name]
        bounds = glyph.getBounds(ufo)
        if bounds is None:
            logger.warning("Glyph %r has no bounds", glyph_name)
            bounds = ufo[".notdef"].getBounds(ufo)

        svgpen = SVGPathPen(ufo)
        glyph.draw(svgpen)
        commands = svgpen.getCommands()

        try:
            unicodes = find_glyph_codepoints(ufo, glyph_name)
        except (KeyError, ValueError):
            logger.warning("Could not find codepoints for glyph %s", glyph_name)
            unicodes = ()

        return cls(glyph=glyph, bounds=bounds, d=commands, unicodes=unicodes)

    def draw_origin(self):
        return self.draw_origin_and_anchors()

    def draw_origin_and_anchors(self, *anchors: NamedAnchor):
        origin_bounds = BoundingBox(xMin=-100, xMax=100, yMin=-100, yMax=100)
        canvas_bounds = unionBounds(origin_bounds, self.bounds)

        if anchors:
            for anchor in anchors:
                canvas_bounds = unionBounds(anchor.anchor_bounds, canvas_bounds)
        canvas_xmin = canvas_bounds.xMin - 100
        canvas_xmax = canvas_bounds.xMax + 100
        canvas_ymin = canvas_bounds.yMin - 100
        canvas_ymax = canvas_bounds.yMax + 100

        canvas_height = canvas_ymax - canvas_ymin
        canvas_width = canvas_xmax - canvas_xmin

        origin = Point(x=abs(canvas_xmin), y=abs(canvas_ymax))
        svg = etree.Element(
            "svg",
            width=str(canvas_width),
            height=str(canvas_height),
            viewBox=f"0 0 {canvas_width} {canvas_height}",
            preserveAspectRatio="xMidYMid",
            xmlns="http://www.w3.org/2000/svg",
        )

        glyph_center = Point(*rectCenter(self.bounds))
        glyph_path = etree.Element("path", {"d": self.d})
        transform_group = etree.Element(
            "g",
            {
                "class": "glyph",
                "data-glyph-name": self.glyph.name,
                "data-glyph-height": str(self.bounds.yMax - self.bounds.yMin),
                "data-glyph-width": str(self.bounds.xMax - self.bounds.xMin),
                "data-glyph-center-x": str(glyph_center.x),
                "data-glyph-center-y": str(glyph_center.y),
                "transform": f"scale(1 -1) translate({-canvas_xmin}, {-canvas_ymax})",
            },
        )
        svg.append(transform_group)
        transform_group.append(glyph_path)

        origin_group = etree.Element(
            "g",
            {
                "class": "origin",
                "data-origin-x": str(origin.x),
                "data-origin-y": str(origin.y),
                "style": ORIGIN_STYLE,
            },
        )
        svg.append(origin_group)

        origin_group.append(
            etree.Element(
                "line",
                x1=str(origin.x),
                y1=str(origin.y - 50),
                x2=str(origin.x),
                y2=str(origin.y + 50),
            )
        )
        origin_group.append(
            etree.Element(
                "line",
                {
                    "x1": str(origin.x - 50),
                    "y1": str(origin.y),
                    "x2": str(origin.x + 50),
                    "y2": str(origin.y),
                },
            )
        )

        if anchors:
            for anchor in anchors:
                anchor_transform_group = etree.Element(
                    "g",
                    {
                        "class": "anchor",
                        "data-anchor-x": str(anchor.x),
                        "data-anchor-y": str(anchor.y),
                        "transform": f"scale(1 -1) translate({-canvas_xmin}, {-canvas_ymax})",
                    },
                )
                svg.append(anchor_transform_group)
                anchor_transform_group.append(
                    etree.Element(
                        "circle",
                        {
                            "cx": str(anchor.x),
                            "cy": str(anchor.y),
                            "r": "10",
                            "style": ANCHOR_STYLE,
                        },
                    )
                )
                anchor_label = etree.Element(
                    "text",
                    {
                        "x": str(origin.x + anchor.x + 20),
                        "y": str(origin.y - anchor.y + 50),
                        "class": "anchor-label",
                        "style": ANCHOR_TEXT_STYLE,
                    },
                )
                anchor_label.text = anchor.name
                svg.append(anchor_label)
        return svg
