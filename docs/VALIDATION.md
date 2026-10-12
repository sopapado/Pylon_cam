# Validation results — 12 October 2026

## Completed locally

| Environment | Installation | Camera-free tests |
| --- | --- | --- |
| Windows, Python 3.7.9 **32-bit**, NumPy 1.21.6 | `pip install .` succeeded using isolated PEP 517 build | **21 passed** |
| Windows, Python 3.13.12 **64-bit**, NumPy 2.4.4 | Built wheel installed with pip | **21 passed** |

Python 3.7 was tested using the official portable pythonx86 3.7.9 NuGet
runtime, downloaded into the ignored artifacts directory. It did not replace
the user's installed Python. Python 3.13 used a repository-local virtual
environment. The tests exercised installed packages, not only source imports.

The wheel and source distribution built successfully with `python -m build`;
`python -m twine check` passed for both. Setuptools is bounded below 68 for
Python 3.7 and below 77 for newer versions to retain one compatible legacy
license metadata format across the target interpreters.

Coverage includes the 1344-to-1340 regression with sentinel padding values,
buffer ownership after SDK memory mutation, two-row image orientation,
configuration reuse, temperature reads, ROI/exposure validation, commit
failure allocations, acquisition errors/timeouts/incomplete data, camera-open
failure, existing SDK ownership, one-session enforcement, cleanup exceptions,
native signatures/boolean size, format rejection, DLL search, invalid DLL
headers, and architecture mismatch.

The initial sandboxed temporary-file tests encountered filesystem permission
errors; the complete suite passed with normal filesystem access. One newer
Python build attempt encountered a transient Windows build-folder lock; the
subsequent isolated build and installed-wheel test succeeded.

## Not verified

- A physical camera or installed vendor runtime was not exercised. The fake
  SDK cannot establish real driver, firmware, timing, ABI, or detector behavior.
- No measured spectrum was acquired or compared against the original camera.
- The configured GitHub Actions matrix has not run on GitHub.
- Python 3.11 and other interpreter/SDK combinations were not tested locally.
- PyPI name availability and distribution permissions are not established.

See RELEASE.md for the hardware acceptance and publication checklist.
