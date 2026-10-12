# Release checklist (no publication performed)

1. Resolve the local-contribution licensing questions in NOTICE.md and
   review GPL/proprietary SDK distribution compatibility. Keep all credits.
2. Run the package on the actual Windows Python 3.7 32-bit camera setup:
   install with that interpreter, verify SDK discovery, acquire at 100 ms,
   check shape (1340,), temperature, repeated acquisition, vertical ROI and
   binning. Compare values with the original framed acquisition under the
   same settings; sequential exposures are not expected to be identical.
3. Test timeout handling and unplug/reconnect behavior when experimentally
   safe. Confirm a fresh session can open after normal context exit.
4. Run the GitHub Actions matrix and inspect results. Test any newer
   Python/SDK combination on hardware before calling it supported.
5. Confirm the desired PyPI distribution name is available and belongs to
   the owner. Add real maintainer/contact and repository URLs to metadata
   once chosen; no identities or URLs have been invented.
6. Build with python -m build and check with
   python -m twine check dist/*.whl dist/*.tar.gz.
   Inspect archive contents: no DLL, SDK header, original private source,
   HyperMap, acquired data, credentials, or reference directory.
7. Obtain explicit owner approval before uploading to GitHub/PyPI or making
   any public release. No publishing workflow or credentials are configured.

The initial distribution version is 0.1.0. A local ZIP, wheel, and source
archive are preparation artifacts and do not imply publication or completed
hardware validation.
