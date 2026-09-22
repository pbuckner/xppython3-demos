"""
PI_PGFonts.py -- exercise every font function of the XPLMPanelGraphics module
                 (new in XPLM440).

This plugin drives ALL twelve font entry points:

    createFont, destroyFont, fontAddFace,
    fontGetMetrics, fontMeasureString, fontGetLineCount,
    fontFitForward, fontFitReverse,
    fontDrawString, fontDrawStringFixedSpacing,
    fontDrawStringWordWrapped, fontDrawStringRotated

Two independent parts:

  Part A -- MEASUREMENT battery (runs once at enable).  Calls the measurement /
            fit / metrics functions and asserts self-consistent results:
            monotonicity, size scaling, and the fit<->measure invariant
            (the Nth character returned by fontFitForward is exactly the last
            one that still fits the given width).  These are the checks most
            likely to catch a Laminar-side bug in this brand-new API.
            Results -> XPPython3Log.txt prefixed [PGFonts].

  Part B -- VISUAL battery (every frame, floating PanelGraphics window).  Draws
            one labeled section per drawing function so each can be eyeballed,
            with guide lines derived from the measurement functions (e.g. an
            underline exactly fontMeasureString() wide, a word-wrap box exactly
            fontGetLineCount() lines tall) so a measurement bug shows up as a
            visible mismatch.
"""
from XPPython3 import xp

# Roboto-Regular ships with X-Plane under Resources/fonts/.
FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"

SIZE = 16.0           # main demo text size
HDR = 12.0            # section-header text size
PAD = 12              # window inset
TITLE_H = 24          # header strip inside the window
WIN_W = 470
WIN_H = 640


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics Fonts test"
        self.Sig = "xppython3.pgfonts"
        self.Desc = "Regression test of the XPLMPanelGraphics font API"
        self._checks = 0
        self._errors = 0
        self.available = False
        self.validated = False
        self.winID = None
        self.font = None
        self.col = {}

    # ---- tiny check/log helpers ---------------------------------------------

    def log(self, *args):
        s = args[0].format(*args[1:]) if args else ''
        print(f"[PGFonts]: {s}", flush=True)

    def error(self, *args):
        self._errors += 1
        s = args[0].format(*args[1:]) if args else ''
        print(f"[PGFonts]: ** ERROR ** {s}", flush=True)

    def check(self, prompt, cond):
        self._checks += 1
        if not cond:
            self.error(prompt)

    def expectError(self, label, excType, fn, *args, **kwargs):
        """Assert that fn(*args) raises excType. Counts as one check."""
        self._checks += 1
        try:
            fn(*args, **kwargs)
        except excType:
            return
        except Exception as e:  # noqa: BLE001
            self.error(f'{label}: raised {type(e).__name__} ({e!r}), expected {excType.__name__}')
            return
        self.error(f'{label}: no exception raised, expected {excType.__name__}')

    # ---- plugin lifecycle ----------------------------------------------------

    def XPluginStart(self):
        versions = xp.getVersions()
        self.log(f"X-Plane {versions[0]}, XPLM {versions[1]}")
        try:
            xp.makeColor(1.0, 1.0, 1.0, 1.0)   # pure, safe outside a draw phase
            self.available = True
        except RuntimeError as e:
            self.available = False
            self.log(f"XPLMPanelGraphics not available: {e}")
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        if self.available:
            self.buildColors()
            self.createFont()
            self.runMeasurementBattery()
        self.createWindow()
        return 1

    def XPluginStop(self):
        if self.winID is not None:
            xp.destroyWindow(self.winID)
            self.winID = None
        if self.font is not None:
            xp.destroyFont(self.font)          # <-- destroyFont
            self.font = None
        if self._errors == 0:
            self.log(f"font check OK ({self._checks} checks passed).")
        else:
            self.log(f"font check: {self._errors} error(s) of {self._checks} checks.")

    # ---- setup ---------------------------------------------------------------

    def buildColors(self):
        self.col = {
            'red': xp.makeColor(1, 0, 0, 1),
            'green': xp.makeColor(0, 1, 0, 1),
            'blue': xp.makeColor(0.4, 0.6, 1, 1),
            'yellow': xp.makeColor(1, 1, 0, 1),
            'cyan': xp.makeColor(0, 1, 1, 1),
            'magenta': xp.makeColor(1, 0, 1, 1),
            'white': xp.makeColor(1, 1, 1, 1),
            'grey': xp.makeColor(0.5, 0.5, 0.5, 1),
        }

    def createFont(self):
        ttf = xp.getSystemPath() + FONT_TTF
        self.font = xp.createFont(xp.CharSetASCII)     # <-- createFont
        xp.fontAddFace(self.font, ttf)                 # <-- fontAddFace
        self.log(f"font created from {ttf}")

    # ---- Part A: measurement battery -----------------------------------------

    def runMeasurementBattery(self):
        if self.validated:
            return
        self.validated = True
        f = self.font

        # fontMeasureString: empty is zero, monotonic in length, scales with size.
        w_empty = xp.fontMeasureString(f, SIZE, "")
        w_i = xp.fontMeasureString(f, SIZE, "i")
        w_ii = xp.fontMeasureString(f, SIZE, "ii")
        w_wide = xp.fontMeasureString(f, SIZE, "WWWW")
        self.check(f"measure('') should be 0, got {w_empty:.2f}", abs(w_empty) < 0.01)
        self.check(f"measure monotonic: 'ii'({w_ii:.2f}) > 'i'({w_i:.2f})", w_ii > w_i)
        self.check(f"measure 'WWWW'({w_wide:.2f}) > 'ii'({w_ii:.2f})", w_wide > w_ii)
        w_small = xp.fontMeasureString(f, SIZE / 2, "Hamburgefonstiv")
        w_big = xp.fontMeasureString(f, SIZE, "Hamburgefonstiv")
        self.check(f"measure scales with size: {w_big:.2f} > {w_small:.2f}", w_big > w_small)

        # fontGetMetrics: positive line height and ascent.
        lh, asc, desc = xp.fontGetMetrics(f, SIZE)
        self.check(f"metrics lineHeight>0, got {lh:.2f}", lh > 0)
        self.check(f"metrics ascent>0, got {asc:.2f}", asc > 0)
        self.log(f"metrics @ {SIZE:.0f}px: lineHeight={lh:.2f} ascent={asc:.2f} descent={desc:.2f}")

        # fontGetLineCount: fits-on-one-line vs must-wrap.
        para = "The quick brown fox jumps over the lazy dog near the river."
        one = xp.fontGetLineCount(f, SIZE, para, 100000.0)
        many = xp.fontGetLineCount(f, SIZE, para, 120.0)
        self.check(f"lineCount huge width == 1, got {one}", one == 1)
        self.check(f"lineCount narrow width > 1, got {many}", many > 1)

        # fontFitForward / fontFitReverse: endpoints + the fit<->measure invariant.
        s = "abcdefghijklmnopqrstuvwxyz"
        full = xp.fontMeasureString(f, SIZE, s)
        self.check(f"fitForward(huge)==len, got {xp.fontFitForward(f, SIZE, s, full + 50)}",
                   xp.fontFitForward(f, SIZE, s, full + 50) == len(s))
        self.check(f"fitForward(0)==0, got {xp.fontFitForward(f, SIZE, s, 0.0)}",
                   xp.fontFitForward(f, SIZE, s, 0.0) == 0)

        # fontFitReverse: returns the START INDEX of the fitting suffix (offset
        # from the beginning of the string): the tail that fits within width is
        # s[idx:], and the trailing-char count is len(s) - idx.
        tail_w = xp.fontMeasureString(f, SIZE, s[-5:])          # room for ~5 trailing chars
        idx_huge = xp.fontFitReverse(f, SIZE, s, full + 50)
        idx_zero = xp.fontFitReverse(f, SIZE, s, 0.0)
        idx = xp.fontFitReverse(f, SIZE, s, tail_w)
        self.check(f"fitReverse(huge)==0 (whole suffix fits), got {idx_huge}", idx_huge == 0)
        self.check(f"fitReverse(0)==len (no suffix fits), got {idx_zero}", idx_zero == len(s))
        self.check(f"fitReverse invariant: measure(s[{idx}:]) <= {tail_w:.2f}",
                   xp.fontMeasureString(f, SIZE, s[idx:]) <= tail_w + 0.5)
        if idx > 0:
            self.check(f"fitReverse invariant: measure(s[{idx - 1}:]) > {tail_w:.2f}",
                       xp.fontMeasureString(f, SIZE, s[idx - 1:]) > tail_w - 0.5)
        self.log(f"fitReverse returns suffix START INDEX (not a count): "
                 f"huge->{idx_huge}, w={tail_w:.1f}->{idx} (tail {s[idx:]!r}), zero->{idx_zero}")

        # Invariant: with a partial width W, the prefix of length n=fitForward(W)
        # must fit (measure<=W) and n+1 must NOT fit (measure>W).
        W = full * 0.4
        n = xp.fontFitForward(f, SIZE, s, W)
        self.check(f"fitForward invariant lower: measure(s[:{n}]) <= {W:.2f}",
                   xp.fontMeasureString(f, SIZE, s[:n]) <= W + 0.5)
        if n < len(s):
            self.check(f"fitForward invariant upper: measure(s[:{n + 1}]) > {W:.2f}",
                       xp.fontMeasureString(f, SIZE, s[:n + 1]) > W - 0.5)

        # A wrong-typed argument should raise, not crash the sim.
        self.expectError("measure bad-size type", TypeError, xp.fontMeasureString, f, "big", "x")

        self.log(f"measurement battery complete ({self._checks} checks, {self._errors} errors so far).")

    # ---- window --------------------------------------------------------------

    def createWindow(self):
        (l, t, _r, _b) = xp.getScreenBoundsGlobal()
        left = l + 120
        top = t - 120
        params = [
            left, top, left + WIN_W, top - WIN_H,
            1,                       # visible
            self.drawWindow,
            None, None, None, None,
            [],                      # refcon
            xp.WindowDecorationRoundRectangle,
            xp.WindowLayerFloatingWindows,
            None,                    # right click
            xp.WindowContentTypePanelGraphics,
            None,
            None
        ]
        self.winID = xp.createWindowEx(params)
        xp.setWindowPositioningMode(self.winID, xp.WindowCenterOnMonitor, -1)
        xp.setWindowTitle(self.winID, "PanelGraphics Fonts"
                          if self.available else "PGFonts N/A (XPLM<440)")
        self.log(f"window {self.winID} created")

    # ---- tiny draw helpers ---------------------------------------------------

    def vline(self, x, y0, y1, color):
        xp.lines(color, [(x, y0), (x, y1)])

    def hline(self, x0, x1, y, color):
        xp.lines(color, [(x0, y), (x1, y)])

    def box(self, x0, y0, x1, y1, color):
        xp.lineLoop(color, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def header(self, x, y, text):
        xp.fontDrawString(self.font, self.col['cyan'], HDR, x, y, text, xp.JustLeft)

    # ---- Part B: visual battery ----------------------------------------------

    def drawWindow(self, inWindowID, _inRefcon):
        if not self.available or self.font is None:
            return
        (l, t, _r, _b) = xp.getWindowGeometry(inWindowID)
        x = l + PAD
        y = t - TITLE_H - PAD            # running baseline cursor, descends
        lh, asc, desc = xp.fontGetMetrics(self.font, SIZE)

        y = self.sec_justification(x, y)
        y = self.sec_fixed_spacing(x, y, lh)
        y = self.sec_word_wrap(x, y, lh, asc, desc, xp.JustLeft)
        y = self.sec_word_wrap(x, y, lh, asc, desc, xp.JustCenter)
        y = self.sec_word_wrap(x, y, lh, asc, desc, xp.JustRight)
        y = self.sec_rotated(x, y, lh)
        y = self.sec_measure_metrics(x, y, lh, asc, desc)
        return

    def sec_justification(self, x, y):
        """fontDrawString with JustLeft / JustCenter / JustRight around one guide."""
        self.header(x, y, "fontDrawString  justification (guide = anchor)")
        y -= 20
        cx = x + 200
        rows = [("JustLeft", xp.JustLeft), ("JustCenter", xp.JustCenter), ("JustRight", xp.JustRight)]
        top = y + 4
        for label, just in rows:
            xp.fontDrawString(self.font, self.col['white'], SIZE, cx, y, label, just)
            y -= 24
        self.vline(cx, top, y + 20, self.col['red'])     # the shared anchor line
        return y - 8

    def sec_fixed_spacing(self, x, y, _lh):
        """fontDrawStringFixedSpacing vs natural proportional spacing."""
        self.header(x, y, "fontDrawStringFixedSpacing (uniform advance)")
        y -= 20
        sample = "Illingworth 01234"
        xp.fontDrawString(self.font, self.col['grey'], SIZE, x, y, "natural: " + sample, xp.JustLeft)
        y -= 22
        base = x + xp.fontMeasureString(self.font, SIZE, "fixed:  ")
        xp.fontDrawString(self.font, self.col['white'], SIZE, x, y, "fixed:", xp.JustLeft)
        spacing = 14
        xp.fontDrawStringFixedSpacing(self.font, self.col['yellow'], SIZE,
                                      base, y, sample, spacing, xp.JustLeft)
        # Ticks every `spacing` px: each glyph should sit on a tick.
        for i in range(len(sample) + 1):
            self.vline(base + i * spacing, y - 4, y - 1, self.col['green'])
        return y - 20

    def sec_word_wrap(self, x, y, lh, asc, desc, just=xp.JustLeft):
        """fontDrawStringWordWrapped inside a box sized by fontGetLineCount."""
        self.header(x, y, "fontDrawStringWordWrapped + fontGetLineCount box")
        y -= 20
        para = ("The quick brown fox jumps over the lazy dog while the "
                "avionics panel redraws every frame.")
        wrap_w = 240
        n = xp.fontGetLineCount(self.font, SIZE, para, float(wrap_w))
        top = y + asc
        bottom = y - (n - 1) * lh - abs(desc)
        self.box(x, top, x + wrap_w, bottom, self.col['grey'])
        anchor_x = (x + 3) if just == xp.JustLeft else (x + 240) if just == xp.JustRight else (x + 120)
        xp.fontDrawStringWordWrapped(self.font, self.col['white'], SIZE,
                                     anchor_x, y, para, wrap_w - 6, just)
        xp.fontDrawString(self.font, self.col['green'], HDR, x + wrap_w + 8, y,
                          f"{n} lines", xp.JustLeft)
        return bottom - 16

    def sec_rotated(self, x, y, _lh):
        """fontDrawStringRotated fanned around one anchor."""
        self.header(x, y, "fontDrawStringRotated (CW degrees)")
        y -= 40
        ax = x + 110
        ay = y - 20
        self.hline(ax - 8, ax + 8, ay, self.col['red'])   # anchor crosshair
        self.vline(ax, ay - 8, ay + 8, self.col['red'])
        cols = ['white', 'yellow', 'cyan', 'green', 'magenta']
        for i, angle in enumerate((0, 45, 90, 135, 180)):
            xp.fontDrawStringRotated(self.font, self.col[cols[i]], SIZE,
                                     ax, ay, f"__ {angle}deg", float(angle), xp.JustLeft)
        return ay - 70

    def sec_measure_metrics(self, x, y, lh, asc, desc):
        """fontMeasureString underline, fontGetMetrics ascent/descent,
        fontFitForward / fontFitReverse markers."""
        self.header(x, y, "measure underline / metrics bracket / fit markers")
        y -= 24
        sample = "Measure & fit me"
        w = xp.fontMeasureString(self.font, SIZE, sample)
        xp.fontDrawString(self.font, self.col['white'], SIZE, x, y, sample, xp.JustLeft)
        self.hline(x, x + w, y - 3, self.col['yellow'])              # underline == measured width
        self.hline(x, x + w, y + asc, self.col['blue'])             # ascent line
        self.hline(x, x + w, y - abs(desc), self.col['blue'])       # descent line

        y -= (lh + 16)
        s = "abcdefghijklmnopqrstuvwxyz"
        fit_w = 110.0
        xp.fontDrawString(self.font, self.col['white'], SIZE, x, y, s, xp.JustLeft)
        nf = xp.fontFitForward(self.font, SIZE, s, fit_w)          # prefix COUNT: s[:nf] fits
        xf = x + xp.fontMeasureString(self.font, SIZE, s[:nf])
        self.vline(xf, y - 4, y + asc, self.col['green'])           # forward fit cut at width
        ri = xp.fontFitReverse(self.font, SIZE, s, fit_w)          # suffix START INDEX: s[ri:] fits
        xr = x + xp.fontMeasureString(self.font, SIZE, s[:ri])
        self.vline(xr, y - 4, y + asc, self.col['magenta'])        # reverse fit suffix start
        xp.fontDrawString(self.font, self.col['green'], HDR, x, y - 16,
                          f"{fit_w}px fits: FWD: first {nf} chars to green line / REV: suffix s[{ri}:] ({len(s) - ri} chars)",
                          xp.JustLeft)
        return y - 30
