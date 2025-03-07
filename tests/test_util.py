# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
from ufoLib2.objects import Point
from ufoLib2.objects.misc import BoundingBox

from elerium.util import equivalent_point


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
