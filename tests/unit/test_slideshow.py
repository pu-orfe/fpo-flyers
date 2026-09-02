"""Guards for docs/slideshow.html.

SOURCE ASSERTIONS, deliberately. This repo has no JS test runner and adding Node tooling for
one file is not worth it, so the behaviour was verified by driving the real page in a browser
against the published flyers (see the plan's verification notes) and the properties that
verification depends on are pinned here. Each one below is a bug that was actually observed
and fixed, not a hypothetical.
"""

from pathlib import Path

import pytest

SLIDESHOW = Path(__file__).resolve().parents[2] / "docs" / "slideshow.html"


@pytest.fixture(scope="module")
def html() -> str:
    return SLIDESHOW.read_text(encoding="utf-8")


def test_flyers_render_at_a_fixed_viewport_and_are_scaled(html):
    """The flyer's own type is clamp()ed WITH FLOORS - 36px headline, 14px body. Shrink the
    iframe and the floors take over, so type grows proportionally as the box shrinks: at
    nine-up that clipped "Announcement" off the top and pushed text outside the border.
    A constant viewport plus a transform keeps the clamps evaluating identically, which is
    what holds the headline at ~7.8% of flyer width - the printed proportion.
    """
    assert "width: 850px" in html and "height: 1100px" in html, \
        "the flyer viewport is no longer fixed; clamp floors will distort small boards"
    assert "transform: scale(var(--scale" in html, \
        "flyers are being resized rather than scaled"


def test_scale_never_exceeds_one(html):
    """Above 1 the flyer is enlarged past the viewport its type was measured for, which
    softens it for no gain. A larger source viewport would make type proportionally SMALLER,
    since the clamps cap at 52px regardless of viewport."""
    assert "ch / PAGE_H, 1)" in html, "scale is uncapped; 1-up and 2-up will upscale"


def test_the_grid_is_computed_not_fixed(html):
    """Three across is not always best: nine flyers are 39% larger as 5x2 than as 3x3,
    because a 3x3 cell is height-limited and wastes width."""
    assert "function bestGrid" in html
    assert "for (var cols = 1; cols <= n; cols++)" in html, \
        "the column count is fixed again; flyers will be smaller than they need to be"


def test_past_examinations_are_filtered(html):
    """The live page was showing an FPO three weeks past, because the manifest carried no
    dates. A public display doing that is worse than the page it replaced."""
    assert "function upcoming" in html
    assert "GRACE_MS" in html, \
        "no grace period; an examination in progress would drop off the board"


def test_undated_entries_are_kept_not_dropped(html):
    """The old manifest format had no dates at all. Dropping undated entries would turn a
    format mismatch into an empty board rather than a slightly stale one."""
    assert "if (!e.start) return true;" in html


def test_both_manifest_shapes_are_accepted(html):
    """The manifest was an array of PDF filenames and is now an array of objects. A stale
    Pages deploy or a rolled-back generator must not blank a wall display."""
    assert "function normalise" in html
    assert "typeof item === 'string'" in html


def test_missing_flyers_are_dropped_before_rendering(html):
    """Observed: a flyer returned 200 one hour and 404 the next as the feed changed and the
    site redeployed. An iframe pointed at a missing file renders GitHub's 404 page full
    width on the display."""
    assert "function existing" in html
    assert "method: 'HEAD'" in html
    # A network failure must not empty the board - only a definite HTTP error drops a flyer.
    block = html[html.index("function existing"):]
    block = block[:block.index("fetch('manifest.json')")]
    assert "return e; })" in block or "return e;" in block, \
        "a failed request drops the flyer; a network blip would empty the board"


def test_the_cropped_top_band_is_honoured(html):
    """page-stream crops 64px off the top to remove Chromium's automation banner. Laying the
    board out over the full viewport centres flyers in a frame taller than the visible one,
    clipping the top row."""
    assert "topCrop" in html and "--top-crop" in html


def test_kiosk_mode_hides_the_operator_chrome(html):
    """Prev/pause/next and a counter are for a person with a pointer. The default keeps them
    so the index's "View All" link is unchanged."""
    assert "qs.has('kiosk')" in html
    assert "if (!kiosk && pages.length > 1) controls.style.display = '';" in html


def test_paper_colour_is_stable_per_candidate(html):
    """Cycling by position meant a flyer changed stock whenever the feed reordered or another
    FPO was added - every 30 minutes, on a wall."""
    assert "function colorFor" in html
    assert "charCodeAt" in html, "colour is positional again, so it will change on reorder"


def test_the_palette_is_not_duplicated(html):
    """The seven colours are the printed card stock. They already exist in view.html and
    flyer_ipad.html; a fourth copy is one more place to drift."""
    assert html.count("'gold'") == 1, "the palette appears more than once in this file"
