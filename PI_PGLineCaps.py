"""PI_PGLineCaps.py -- exercise xp.setLineCap()

Self-contained. Two independent parts:

 VISUAL battery (every frame, in a PanelGraphics floating window).
 Draws thick lines in a labeled grid, one cap style per cell. Each
 cell also draws thin white ENDPOINT TICKS at the exact coordinates
 passed to the draw call, so the cap is readable rather than merely
 visible:

 Note how all "joined" vertices are rounded. Round and Square linecaps
 extend "past" the line endpoint (as expected).

  butt    -> the stroke stops flush at the tick
  round   -> a semicircle bulges HALF THE LINE WIDTH past the tick
  square  -> a square block extends HALF THE LINE WIDTH past
             the tick, with sharp corners

Round vs. square is easiest to judge in the "diag" cell.

Results go to XPPython3Log.txt, prefixed [PGLineCaps].

"""
from XPPython3 import xp

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 10.0

CELL = 104         # grid cell size, pixels -- roomy, caps need the space
PAD = 10           # inset within each cell
COLS = 4           # cells per row
TITLE_H = 24       # header strip inside the window

WIDTH = 16.0       # line width for the cap cells; cap sticks out WIDTH/2
INSET = 26         # horizontal inset of the line endpoints within the cell

# The stipple band (see stippleRows) gets the FULL window width instead of a
# grid cell: diagnosing per-dash cap behavior needs many dashes side by side,
# and a 104px cell only fits two or three.
STIP_ROW_H = 30    # vertical pitch of one stipple probe row
STIP_W = 6.0       # stipple line width -> round/square cap adds 3px per end
STIP_DASH = 14.0   # dash length: >> STIP_W so caps lengthen dashes without merging them into one another


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics LineCap test"
        self.Sig = "xppython3.pglinecaps"
        self.Desc = "Regression test of xp.setLineCap() (XPLMSetLineCap, XPLM440)"
        self._checks = 0
        self._errors = 0
        self.available = False
        self.winID = None
        self.font = None
        self.col = {}
        self.frames = 0
        self.badValueLogged = False

    # ---- tiny check/log helpers ---------------------------------------------

    def log(self, *args):
        s = args[0].format(*args[1:]) if args else ''
        print(f"[PGLineCaps]: {s}", flush=True)

    def error(self, *args):
        self._errors += 1
        s = args[0].format(*args[1:]) if args else ''
        print(f"[PGLineCaps]: ** ERROR ** {s}", flush=True)

    def checkVal(self, prompt, got, expected):
        self._checks += 1
        if got != expected:
            self.error(f'{prompt}: got {got!r}, expected {expected!r}')

    def expectError(self, label, excType, fn, *args, **kwargs):
        """Assert that fn(*args) raises excType. Counts as one check."""
        self._checks += 1
        try:
            fn(*args, **kwargs)
        except excType:
            return
        except Exception as e:  # noqa: BLE001 - we want the real type in the message
            self.error(f'{label}: raised {type(e).__name__} ({e!r}), expected {excType.__name__}')
            return
        self.error(f'{label}: no exception raised, expected {excType.__name__}')

    # ---- plugin lifecycle ----------------------------------------------------

    def XPluginStart(self):
        versions = xp.getVersions()  # (xplaneVersion, xplmVersion, hostID)
        self.log(f"X-Plane {versions[0]}, XPLM {versions[1]}")

        if not hasattr(xp, 'setLineCap'):
            self.log("xp.setLineCap is MISSING -- xp.py predates the XPLMSetLineCap wrapper.")
            return self.Name, self.Sig, self.Desc

        # Probe availability without touching GL: makeColor is pure (thread-safe
        # per SDK) and is the only routine safe to call outside a draw phase.
        try:
            xp.makeColor(1.0, 1.0, 1.0, 1.0)
            self.available = True
        except RuntimeError as e:
            self.log(f"XPLMPanelGraphics not available: {e}")

        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        if self.available:
            self.buildColors()
            self.createFont()
        self.createWindow()
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def XPluginStop(self):
        if self.winID is not None:
            xp.destroyWindow(self.winID)
            self.winID = None
        if self.font is not None:
            xp.destroyFont(self.font)
            self.font = None
        if self._errors == 0:
            self.log(f"module check OK ({self._checks} checks passed, {self.frames} frames drawn).")
        else:
            self.log(f"module check: {self._errors} error(s) of {self._checks} checks.")

    def buildColors(self):
        self.col = {
            'red': xp.makeColor(1, 0, 0, 1),
            'green': xp.makeColor(0, 1, 0, 1),
            'blue': xp.makeColor(0.3, 0.5, 1, 1),
            'yellow': xp.makeColor(1, 1, 0, 1),
            'cyan': xp.makeColor(0, 1, 1, 1),
            'magenta': xp.makeColor(1, 0, 1, 1),
            'white': xp.makeColor(1, 1, 1, 1),
            'grey': xp.makeColor(0.45, 0.45, 0.45, 1),
        }

    # ---- window --------------------------------------------------------------

    def createFont(self):
        ttf = xp.getSystemPath() + FONT_TTF
        self.font = xp.createFont(xp.CharSetASCII)
        xp.fontAddFace(self.font, ttf)
        self.log(f"font created from {ttf}")

    def createWindow(self):
        rows = (len(self.cells()) + COLS - 1) // COLS
        width = COLS * CELL + 2 * PAD
        height = (rows * CELL + TITLE_H + 2 * PAD
                  + len(self.stippleRows()) * STIP_ROW_H + PAD)

        (l, t, _r, _b) = xp.getScreenBoundsGlobal()
        left = l + 120
        top = t - 120
        params = [
            left, top, left + width, top - height,
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
        xp.setWindowTitle(self.winID, "PG LineCap test"
                          if self.available else "PG LineCap N/A (XPLM<440)")
        self.log(f"window {self.winID} ({width}x{height}, {len(self.cells())} cells)")

    # ---- Part B: visual battery ----------------------------------------------

    def cells(self):
        """List of (label, drawfn(ox, oy, s)) -- one per grid cell.

        'frameReset' MUST stay first: it is the per-callback default probe and
        is only meaningful if no other cell has set a cap yet this frame.
        """
        return [
            ("frameReset", self.c_frameReset),
            ("butt", self.c_butt),
            ("round", self.c_round),
            ("square", self.c_square),
            ("default()", self.c_default),
            ("persist", self.c_persist),
            ("diag-round", self.c_diagRound),
            ("diag-square", self.c_diagSquare),
            ("strip-butt", self.c_stripButt),
            ("strip-round", self.c_stripRound),
            ("loop-butt", self.c_loopButt),
            ("loop-round", self.c_loopRound),
            ("loop-square", self.c_loopSquare),
            ("defWidth", self.c_defWidth),
            ("colorW", self.c_colorW),
            ("scaled", self.c_scaled),
            ("badValue", self.c_badValue),
        ]

    def drawWindow(self, inWindowID, _inRefcon):
        if not self.available:
            return
        (l, t, r, _b) = xp.getWindowGeometry(inWindowID)
        self.frames += 1

        cells = self.cells()
        rows = (len(cells) + COLS - 1) // COLS
        grid_top = t - TITLE_H
        for i, (label, fn) in enumerate(cells):
            col = i % COLS
            row = i // COLS
            ox = l + PAD + col * CELL
            oy = grid_top - (row + 1) * CELL          # cell lower-left y
            s = CELL - 2 * PAD
            try:
                fn(ox + PAD, oy + PAD, s)
            except Exception as e:  # noqa: BLE001 - report once, keep drawing the rest
                self.error(f'draw {label}: {e!r}')
            if self.font is not None:
                xp.fontDrawString(self.font, self.col['white'], LABEL_SIZE,
                                  ox + 2, oy + CELL - 12, label, xp.JustLeft)

        try:
            self.drawStippleBand(l, r, grid_top - rows * CELL - PAD)
        except Exception as e:  # noqa: BLE001
            self.error(f'draw stipple band: {e!r}')

        # Deliberately leave a NON-default cap set as the callback ends. The
        # 'frameReset' cell (drawn first next frame, with no setLineCap of its
        # own) is what detects whether this leaks across callbacks.
        xp.setLineCap(xp.LineCapRound)
        return

    # ---- per-cell helpers ----------------------------------------------------

    def _ticks(self, x0, y0, x1, y1):
        """Thin white ticks perpendicular-ish at each endpoint, so the reader can
        see exactly where the line was asked to stop. Drawn with butt caps and
        width 1 so the ticks themselves are unambiguous."""
        xp.setLineCap(xp.LineCapButt)
        h = WIDTH * 0.75
        for (x, y) in ((x0, y0), (x1, y1)):
            xp.lines(self.col['white'], [(x, y - h), (x, y + h)])

    def _hline(self, ox, oy, s, cap, color='red', width=WIDTH):
        """Thick horizontal line across the cell with endpoint ticks. Ticks are
        drawn FIRST (they reset the cap), then the cap under test is applied."""
        y = oy + s / 2
        x0, x1 = ox + INSET, ox + s - INSET
        self._ticks(x0, y, x1, y)
        if cap is not None:
            xp.setLineCap(cap)
        xp.linesWithWidth(self.col[color], width, [(x0, y), (x1, y)])
        return x0, y, x1, y

    def _dline(self, ox, oy, s, cap, color='cyan'):
        """Thick diagonal -- the clearest round-vs-square discriminator."""
        x0, y0 = ox + INSET * 0.8, oy + INSET * 0.6
        x1, y1 = ox + s - INSET * 0.8, oy + s - INSET * 0.6
        xp.setLineCap(xp.LineCapButt)
        xp.lines(self.col['white'], [(x0 - 8, y0), (x0 + 8, y0)])
        xp.lines(self.col['white'], [(x1 - 8, y1), (x1 + 8, y1)])
        xp.setLineCap(cap)
        xp.linesWithWidth(self.col[color], WIDTH, [(x0, y0), (x1, y1)])

    # ---- per-cell draw functions (each draws within s x s at (ox, oy)) -------

    def c_frameReset(self, ox, oy, s):
        # No setLineCap at all -- but the ticks helper would set Butt, which
        # would defeat the probe. So draw the line FIRST, bare, then the ticks.
        y = oy + s / 2
        x0, x1 = ox + INSET, ox + s - INSET
        xp.linesWithWidth(self.col['yellow'], WIDTH, [(x0, y), (x1, y)])
        self._ticks(x0, y, x1, y)

    def c_butt(self, ox, oy, s):
        self._hline(ox, oy, s, xp.LineCapButt)

    def c_round(self, ox, oy, s):
        self._hline(ox, oy, s, xp.LineCapRound)

    def c_square(self, ox, oy, s):
        self._hline(ox, oy, s, xp.LineCapSquare)

    def c_default(self, ox, oy, s):
        # Set Round, then call setLineCap() with NO argument: our wrapper
        # defaults it to LineCapButt, so this must render flush like 'butt'.
        xp.setLineCap(xp.LineCapRound)
        xp.setLineCap()
        self._hline(ox, oy, s, None, color='green')

    def c_persist(self, ox, oy, s):
        # One setLineCap, two draw calls -- both must be round.
        x0, x1 = ox + INSET, ox + s - INSET
        yl, yu = oy + s / 3, oy + 2 * s / 3
        self._ticks(x0, yl, x1, yl)
        self._ticks(x0, yu, x1, yu)
        xp.setLineCap(xp.LineCapRound)
        xp.linesWithWidth(self.col['magenta'], WIDTH * 0.6, [(x0, yl), (x1, yl)])
        xp.linesWithWidth(self.col['magenta'], WIDTH * 0.6, [(x0, yu), (x1, yu)])

    def c_diagRound(self, ox, oy, s):
        self._dline(ox, oy, s, xp.LineCapRound)

    def c_diagSquare(self, ox, oy, s):
        self._dline(ox, oy, s, xp.LineCapSquare)

    # ---- JOIN behavior: does the cap setting affect interior vertices? -------
    #
    # There is NO join API in XPLMPanelGraphics -- XPLMSetLineCap is the only
    # line-state setter, and the header never mentions joins, corners, miter or
    # bevel.
    #
    # ANSWERED: the three loop-* cells render IDENTICALLY, all with rounded
    # corners. So joins are always round and are independent of the cap state.
    # The cap is not leaking into joins, and X-Plane is not stroking each
    # segment independently (that would have left a triangular notch at the
    # outer corner of loop-butt). Nothing to report but a doc clarification.
    #
    # These cells stay as a regression check: if loop-butt ever grows notches,
    # or the three loop cells ever stop matching, the cap has begun bleeding
    # into join generation.
    #
    # The apex is deliberately sharp (tall narrow triangle) and the stroke is
    # deliberately fat -- notches and fills are only legible at width.

    def _strip(self, ox, oy, s, cap, color):
        """Open 3-point chevron: 2 free ends (caps) + 1 interior vertex (join)."""
        pts = [(ox + 8, oy + 6), (ox + s / 2, oy + s - 6), (ox + s - 8, oy + 6)]
        xp.setLineCap(xp.LineCapButt)
        for (x, y) in (pts[0], pts[2]):          # ticks mark the two free ends
            xp.lines(self.col['white'], [(x - 7, y), (x + 7, y)])
        xp.setLineCap(cap)
        xp.lineStripWithWidth(self.col[color], WIDTH, pts)

    def _loop(self, ox, oy, s, cap, color):
        """Closed triangle: NO free ends, so every visible difference between
        these three cells is join behavior, not cap behavior."""
        xp.setLineCap(cap)
        xp.lineLoopWithWidth(self.col[color], WIDTH,
                             [(ox + 8, oy + 6), (ox + s - 8, oy + 6), (ox + s / 2, oy + s - 6)])

    def c_stripButt(self, ox, oy, s):
        self._strip(ox, oy, s, xp.LineCapButt, 'green')

    def c_stripRound(self, ox, oy, s):
        self._strip(ox, oy, s, xp.LineCapRound, 'green')

    def c_loopButt(self, ox, oy, s):
        self._loop(ox, oy, s, xp.LineCapButt, 'blue')

    def c_loopRound(self, ox, oy, s):
        self._loop(ox, oy, s, xp.LineCapRound, 'blue')

    def c_loopSquare(self, ox, oy, s):
        self._loop(ox, oy, s, xp.LineCapSquare, 'blue')

    def c_defWidth(self, ox, oy, s):
        # (because lines are so thin, it's difficult to actually see the end caps)
        x0, x1 = ox + INSET, ox + s - INSET
        for i, cap in enumerate((xp.LineCapButt, xp.LineCapRound, xp.LineCapSquare)):
            y = oy + s * (3 - i) / 4.0
            xp.setLineCap(xp.LineCapButt)
            for x in (x0, x1):                    # ticks clear of the stroke
                xp.lines(self.col['white'], [(x, y + 4), (x, y + 7)])
            xp.setLineCap(cap)
            xp.lines(self.col['white'], [(x0, y), (x1, y)])

    def c_colorW(self, ox, oy, s):
        # Per-vertex-color width variant -- same cap state, different entry point.
        y = oy + s / 2
        x0, x1 = ox + INSET, ox + s - INSET
        self._ticks(x0, y, x1, y)
        xp.setLineCap(xp.LineCapRound)
        xp.linescWithWidth(WIDTH, [(x0, y, self.col['red']), (x1, y, self.col['green'])])

    def c_scaled(self, ox, oy, s):
        # Does the cap go through the transform stack? Under a 2x scale the
        # round cap should scale with the (also-scaled) stroke width.
        y = oy + s / 2
        xp.transformPush()
        xp.transformTranslate(ox + INSET, y)
        xp.transformScale(2.0, 2.0)
        xp.setLineCap(xp.LineCapRound)
        xp.linesWithWidth(self.col['magenta'], WIDTH * 0.5, [(0, 0), ((s - 2 * INSET) / 2.0, 0)])
        xp.transformPop()
        self._ticks(ox + INSET, y, ox + s - INSET, y)

    def stippleRows(self):
        """(kind, label, cap, priorCap) -- priorCap is set first, then cap.

        kind 'stipple' uses linesStipple; kind 'plain' uses linesWithWidth, to
        establish whether the first-endpoint bug is stipple-specific.
        """
        return [
            ('stipple', "butt", xp.LineCapButt, None),
            ('stipple', "round", xp.LineCapRound, None),
            ('stipple', "square", xp.LineCapSquare, None),
            ('stipple', "butt after round (ctl)", xp.LineCapButt, xp.LineCapRound),
            ('plain', "butt", xp.LineCapButt, None),
            ('plain', "round", xp.LineCapRound, None),
            ('plain', "square", xp.LineCapSquare, None),
        ]

    def drawStippleBand(self, left, right, top):
        """Draw the full-width cap probe rows, topmost at 'top'."""
        x0 = left + PAD + 4
        x1 = right - PAD - 4
        for i, (kind, label, cap, prior) in enumerate(self.stippleRows()):
            y = top - i * STIP_ROW_H - STIP_ROW_H + 8
            if self.font is not None:
                xp.fontDrawString(self.font, self.col['white'], LABEL_SIZE,
                                  x0, y + 10, f"{kind} {label}", xp.JustLeft)
            # Endpoint ticks, always butt so they are unambiguous. Drawn as
            # SHORT verticals offset above/below the stroke so they never
            # overlap the ink whose extent we are measuring.
            xp.setLineCap(xp.LineCapButt)
            for x in (x0, x1):
                xp.lines(self.col['white'], [(x, y + 5), (x, y + 9)])
                xp.lines(self.col['white'], [(x, y - 9), (x, y - 5)])
            if prior is not None:
                xp.setLineCap(prior)
            xp.setLineCap(cap)
            if kind == 'stipple':
                xp.linesStipple(self.col['cyan'], [(x0, y), (x1, y)], STIP_DASH, STIP_W)
            else:
                xp.linesWithWidth(self.col['yellow'], STIP_W, [(x0, y), (x1, y)])

    def c_badValue(self, ox, oy, s):
        # Out-of-range int: the wrapper passes it through unvalidated. Log what
        # happens once, then draw so we can see which cap (if any) took effect.
        y = oy + s / 2
        x0, x1 = ox + INSET, ox + s - INSET
        self._ticks(x0, y, x1, y)
        try:
            xp.setLineCap(99)
            if not self.badValueLogged:
                self.badValueLogged = True
                self.log("setLineCap(99) accepted without error -- compare the cell "
                         "against butt/round/square to see what XPLM did with it.")
        except Exception as e:  # noqa: BLE001
            if not self.badValueLogged:
                self.badValueLogged = True
                self.log(f"setLineCap(99) raised {type(e).__name__}: {e}")
        xp.linesWithWidth(self.col['red'], WIDTH, [(x0, y), (x1, y)])
