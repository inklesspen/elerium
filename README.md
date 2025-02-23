<!--
SPDX-FileCopyrightText: 2025 Rose Davidson <rose@metaclassical.com>
SPDX-License-Identifier: CC-BY-ND-4.0
-->

# Elerium

Elerium is a library for working with [UFOs (Unified Font Objects)](https://unifiedfontobject.org/).

## MTI to FEA

Certain OFL-licensed fonts (particularly those from the Noto and Croscore projects) have OpenType features specified using [Monotype's format](https://monotype.github.io/OpenType_Table_Source/otl_source.html). The open font community seems to be standardized around [AFDKO syntax](https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html).

`elerium mti-to-fea` is capable of translating from Monotype syntax to AFDKO syntax.

## Licensing

The code in this library is licensed under the [MIT license](https://spdx.org/licenses/MIT.html). Some test data is sourced from upstream repositories and is licensed under their licenses; see `tests/data/mti/README.md` and `tests/data/nototools/README.md` for details.
