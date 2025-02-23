# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import pathlib

from elerium.mti_parser import Parser

DATA_BASE_PATH = pathlib.Path(__file__).parent / "data"


def test_parse_plist():
    parser = Parser()
    parser.add_plist(DATA_BASE_PATH / "plist/Example.plist")
    assert parser.gdef is not None
    assert parser.gpos is not None
    assert parser.gsub is not None

    result = parser.parse()
    actual = result.asFea()
    expected = (DATA_BASE_PATH / "plist/Example.fea").read_text()
    assert actual == expected
