# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
from fontTools.misc.transform import Transform
from ufoLib2.objects import Point
from ufoLib2.objects.misc import BoundingBox


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
