# Attribution and release licensing review

The original Pylon scripts and APIs were developed by Michelangelo Romeo,
engineer at IPCMS/CNRS, and Dr Joanna Wolff (RIKEN). This attribution was
provided by the project owner. The upstream driver credits below are
preserved alongside it.

This package adapts the supplied `Pylon_init.py`, `picamClass.py`, and
`picam_types.py`. The latter two credit Daniel R. Dietze and identify
Michelangelo Romeo as author, with "Copyright 2020, The HYRBID Python
formation Project" and `__license__ = "GPL"`. Those notices remain in
`src/simplepicam/_types.py`. The original driver is credited in `_driver.py`.
`Pylon_init.py` identifies a last update by Joanna Wolff, 20 September 2022.

Daniel Dietze's upstream repository declares GPL version 3 or later:
https://github.com/ddietze/Py-Hardware-Support
Copyright 2010, 2015 Daniel Dietze. The GPL text in LICENSE was obtained
from that repository's gpl.txt. New simplepicam adaptations are offered
under GPL-3.0-or-later, consistently with that upstream license.

Before public distribution, confirm that the supplied local modifications
may be distributed under GPL-3.0-or-later, including the Pylon_init.py work:
its header contains no explicit license grant, and the Romeo headers do not
specify a GPL version. The package metadata records the intended GPL release
license; it does not establish permission for third-party contributions.
Do not relicense these derivatives as MIT/BSD without the necessary rights.
This provenance review is a release prerequisite, not a claim that all
permissions have already been obtained.

The PICam SDK, camera drivers, and DLLs belong to their respective owners.
No vendor binaries, SDK headers, or HyperMap code are included in this
distribution. We have not established redistribution permission for the DLLs.
Users must install the vendor SDK separately under its own terms. Before
release, review any implications of distributing a GPL wrapper that loads
the proprietary SDK; no vendor linking exception is asserted here.

The working source copies in the local ignored `reference/` directory are
inspection material only. They are excluded from Git and release archives.

Changes in 2026: focused synchronous driver, package-relative imports,
explicit native signatures, corrected pibln/pibyte types, safe resource
cleanup, DLL discovery, detached NumPy buffers, normalized row-major output,
simple Camera API, packaging, documentation, and camera-free tests.
