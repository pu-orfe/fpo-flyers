"""System libraries WeasyPrint needs must be installed wherever it runs.

WeasyPrint warns at import when libharfbuzz-subset is missing and says
future versions will require it. That warning appeared on every CI run.
The import runs in a fresh interpreter because WeasyPrint loads its
libraries once per process.
"""

from __future__ import annotations

import subprocess
import sys

PROBE = """
import warnings
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    import weasyprint  # noqa: F401
for w in caught:
    print(w.message)
"""


def test_weasyprint_finds_harfbuzz_subset() -> None:
    result = subprocess.run(
        [sys.executable, "-c", PROBE], capture_output=True, text=True, check=True
    )
    assert "HarfBuzz-Subset" not in result.stdout, result.stdout
