# SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
# SPDX-License-Identifier: MIT
import pathlib
from typing import Annotated, Optional

import typer
import ufoLib2
from rich.console import Console

from .mti_parser import Parser

app = typer.Typer(no_args_is_help=True)

err_console = Console(stderr=True)


@app.callback()
def callback():
    """
    Elerium helps you improve your UFOs!
    """


@app.command(no_args_is_help=True)
def mti_to_fea(
    output: Annotated[pathlib.Path, typer.Option(help="Path to write the AFDKO file", exists=False, dir_okay=False, writable=True)],
    plist: Annotated[
        Optional[pathlib.Path],
        typer.Option(help="Path to the plist file listing the Monotype-format files", exists=True, dir_okay=False, readable=True),
    ] = None,
    gdef: Annotated[
        Optional[pathlib.Path],
        typer.Option(help="Path to the Monotype-format GDEF file", exists=True, dir_okay=False, readable=True),
    ] = None,
    gsub: Annotated[
        Optional[pathlib.Path],
        typer.Option(help="Path to the Monotype-format GSUB file", exists=True, dir_okay=False, readable=True),
    ] = None,
    gpos: Annotated[
        Optional[pathlib.Path],
        typer.Option(help="Path to the Monotype-format GPOS file", exists=True, dir_okay=False, readable=True),
    ] = None,
    ufo: Annotated[Optional[pathlib.Path], typer.Option(help="Path to the UFO for the font", exists=True, readable=True)] = None,
    font_name: Annotated[
        Optional[str], typer.Option(help="Providing the font name is necessary if a plist contains entries for more than one font")
    ] = None,
):
    """
    Parse Monotype's internal OpenType feature format and convert to AFDKO FEA syntax.

    At least one of --plist, --gdef, --gsub, --gpos must be specified. If --plist is specified, its contents will override any specified --gdef, --gsub, or --gpos.
    """
    if plist is None and gdef is None and gsub is None and gpos is None:
        err_console.print("At least one input file is required.")
        typer.Abort()
    parser = Parser()
    if ufo is not None:
        parser.load_units_per_em_from_ufo(ufoLib2.Font.open(ufo))
    if gdef is not None:
        parser.add_GDEF(gdef)
    if gsub is not None:
        parser.add_GSUB(gsub)
    if gpos is not None:
        parser.add_GPOS(gpos)
    if plist is not None:
        parser.add_plist(plist, font_name)
    fea = parser.parse().asFea()
    output.write_text(fea)
