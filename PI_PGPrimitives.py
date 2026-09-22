"""
PI_PGPrimitives.py -- exercise the XPLMPanelGraphics primitive / transform /
scissor / stencil drawing module (new in XPLM440).

Results go to XPPython3Log.txt, prefixed [PGPrimitives].
"""
from XPPython3 import xp

# Labels are drawn with the PanelGraphics font API (XPLMDrawString does NOT
# render inside a WindowContentTypePanelGraphics window). Roboto-Regular ships
# with X-Plane under Resources/fonts/.
FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 10.0


CELL = 78          # grid cell size, pixels
PAD = 9            # inset within each cell
COLS = 5           # cells per row
TITLE_H = 24       # header strip inside the window


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics Primitives test"
        self.Sig = "xppython3.pgprimitives"
        self.Desc = "Regression test of the XPLMPanelGraphics primitive drawing API"
        self._checks = 0
        self._errors = 0
        self.available = False
        self.winID = None
        self.font = None
        self.col = {}

    # ---- tiny check/log helpers ---------------------------------------------

    def log(self, *args):
        s = args[0].format(*args[1:]) if args else ''
        print(f"[PGPrimitives]: {s}", flush=True)

    def error(self, *args):
        self._errors += 1
        s = args[0].format(*args[1:]) if args else ''
        print(f"[PGPrimitives]: ** ERROR ** {s}", flush=True)

    # ---- plugin lifecycle ----------------------------------------------------

    def XPluginStart(self):
        # Probe availability without touching GL: makeColor is pure (thread-safe
        # per SDK) and is the only routine safe to call outside a draw phase.
        try:
            xp.makeColor(1.0, 1.0, 1.0, 1.0)
            self.available = True
        except RuntimeError as e:
            self.available = False
            self.log(f"XPLMPanelGraphics not available: {e}")

        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        if self.available:
            self.buildColors()
            self.createFont()
        self.createWindow()
        return 1

    def XPluginStop(self):
        if self.winID is not None:
            xp.destroyWindow(self.winID)
            self.winID = None
        if self.font is not None:
            xp.destroyFont(self.font)
            self.font = None
        if self._errors == 0:
            self.log(f"module check OK ({self._checks} checks passed).")
        else:
            self.log(f"module check: {self._errors} error(s) of {self._checks} checks.")

        return

    def buildColors(self):
        self.col = {
            'red': xp.makeColor(1, 0, 0, 1),
            'green': xp.makeColor(0, 1, 0, 1),
            'blue': xp.makeColor(0, 0, 1, 1),
            'yellow': xp.makeColor(1, 1, 0, 1),
            'cyan': xp.makeColor(0, 1, 1, 1),
            'magenta': xp.makeColor(1, 0, 1, 1),
            'white': xp.makeColor(1, 1, 1, 1),
            'black': xp.makeColor(0, 0, 0, 1),
        }

    # ---- window --------------------------------------------------------------

    def createFont(self):
        ttf = xp.getSystemPath() + FONT_TTF
        self.font = xp.createFont(xp.CharSetASCII)
        xp.fontAddFace(self.font, ttf)
        # Exercise the measurement side of the API while we're here.
        w = xp.fontMeasureString(self.font, LABEL_SIZE, "lineStrip")
        lh, _asc, _desc = xp.fontGetMetrics(self.font, LABEL_SIZE)
        self.log(f"font created from {ttf} (measure='lineStrip'->{w:.1f}px, lineHeight={lh:.1f})")

    def createWindow(self):
        rows = (len(self.cells()) + COLS - 1) // COLS
        width = COLS * CELL + 2 * PAD
        height = rows * CELL + TITLE_H + 2 * PAD

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
            None,
            xp.WindowContentTypePanelGraphics,
            None,
            None
        ]
        self.winID = xp.createWindowEx(params)
        xp.setWindowPositioningMode(self.winID, xp.WindowCenterOnMonitor, -1)
        xp.setWindowTitle(self.winID, "PG Primitives test"
                          if self.available else "PG Primitives N/A (XPLM<440)")
        self.log(f"window {self.winID} ({width}x{height}, {len(self.cells())} cells)")

    def cells(self):
        """List of (label, drawfn(ox, oy, s)) -- one per grid cell."""
        return [
            ("lines", self.c_lines),
            ("linesW", self.c_linesWidth),
            ("lineStrip", self.c_lineStrip),
            ("lineStripW", self.c_lineStripWidth),
            ("lineLoop", self.c_lineLoop),
            ("lineLoopW", self.c_lineLoopWidth),
            ("poly-CW", self.c_polygon_cw),
            ("poly-CCW", self.c_polygon_ccw),
            # ("polyW-CW", self.c_polygonWidth_cw),
            # ("polyW-CCW", self.c_polygonWidth_ccw),
            ("quad-CW", self.c_quadstrip_cw),
            ("quad-CCW", self.c_quadstrip_ccw),
            # ("quadW-CW", self.c_quadstripWidth_cw),
            # ("quadW-CCW", self.c_quadstripWidth_ccw),
            ("linesStip", self.c_linesStipple),
            ("lStripStip", self.c_lineStripStipple),
            ("lLoopStip", self.c_lineLoopStipple),
            ("linesc", self.c_linesc),
            ("lineStripc", self.c_lineStripc),
            ("lineLoopc", self.c_lineLoopc),
            ("polyc-CW", self.c_polygonc_cw),
            ("polyc-CCW", self.c_polygonc_ccw),
            ("quadc-CW", self.c_quadstripc_cw),
            ("quadc-CCW", self.c_quadstripc_ccw),
            ("linescW", self.c_linescWidth),
            ("lStripcW", self.c_lineStripcWidth),
            ("lLoopcW", self.c_lineLoopcWidth),
            # ("polycW-CW", self.c_polygoncWidth_cw),
            # ("polycW-CCW", self.c_polygoncWidth_ccw),
            # ("quadcW-CW", self.c_quadstripcWidth_cw),
            # ("quadcW-CCW", self.c_quadstripcWidth_ccw),
            ("transform", self.c_transform),
            ("scissor", self.c_scissor),
            ("stencil", self.c_stencil),
        ]

    def drawWindow(self, inWindowID, _inRefcon):
        if not self.available:
            return
        (l, t, _r, _b) = xp.getWindowGeometry(inWindowID)

        cells = self.cells()
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
                # Baseline near the top of the cell; left-justified.
                xp.fontDrawString(self.font, self.col['white'], LABEL_SIZE,
                                  ox + 2, oy + CELL - 12, label, xp.JustLeft)
        return

    # ---- per-cell draw functions (each draws within s x s at (ox, oy)) -------

    def c_lines(self, ox, oy, s):
        xp.lines(self.col['red'], [(ox, oy), (ox + s, oy + s), (ox, oy + s), (ox + s, oy)])

    def c_linesWidth(self, ox, oy, s):
        xp.linesWithWidth(self.col['red'], 3.0, [(ox, oy), (ox + s, oy + s), (ox, oy + s), (ox + s, oy)])

    def c_lineStrip(self, ox, oy, s):
        xp.lineStrip(self.col['green'], [(ox, oy), (ox + s / 2, oy + s), (ox + s, oy), (ox + s, oy + s)])

    def c_lineStripWidth(self, ox, oy, s):
        xp.lineStripWithWidth(self.col['green'], 3.0,
                              [(ox, oy), (ox + s / 2, oy + s), (ox + s, oy), (ox + s, oy + s)])

    def c_lineLoop(self, ox, oy, s):
        xp.lineLoop(self.col['blue'], [(ox, oy), (ox + s, oy), (ox + s / 2, oy + s)])

    def c_lineLoopWidth(self, ox, oy, s):
        xp.lineLoopWithWidth(self.col['blue'], 3.0, [(ox, oy), (ox + s, oy), (ox + s / 2, oy + s)])

    # Filled polygons are winding-agnostic: the same shape wound clockwise and
    # counter-clockwise must both fill. The pair is drawn side by side so a
    # blank cell is immediately visible.
    def _diamond_cw(self, ox, oy, s):
        # bottom -> left -> top -> right  (clockwise)
        return [(ox + s / 2, oy), (ox, oy + s / 2), (ox + s / 2, oy + s), (ox + s, oy + s / 2)]

    def _diamond_ccw(self, ox, oy, s):
        # bottom -> right -> top -> left  (counter-clockwise)
        return [(ox + s / 2, oy), (ox + s, oy + s / 2), (ox + s / 2, oy + s), (ox, oy + s / 2)]

    def _colorize(self, pts, color=None):
        # attach per-vertex colors to a list of (x, y) points
        cols = (self.col['red'], self.col['green'], self.col['blue'], self.col['yellow']) if color is None else 4 * [color]
        return [(x, y, cols[i % len(cols)]) for i, (x, y) in enumerate(pts)]

    def c_polygon_cw(self, ox, oy, s):
        xp.polygon(self.col['yellow'], self._diamond_cw(ox, oy, s))

    def c_polygon_ccw(self, ox, oy, s):
        xp.polygon(self.col['yellow'], self._diamond_ccw(ox, oy, s))

    # Quad strips are winding-agnostic too: both cells of this pair must fill,
    # same as the polygon pair above.
    def _quad_ccw(self, ox, oy, s):
        # GL_QUAD_STRIP pairs (BL,BR),(TL,TR) -> CCW quad
        return [(ox, oy), (ox + s, oy), (ox, oy + s), (ox + s, oy + s)]

    def _quad_cw(self, ox, oy, s):
        # swap each vertex pair to reverse winding -> CW quad
        return [(ox + s, oy), (ox, oy), (ox + s, oy + s), (ox, oy + s)]

    def c_quadstrip_cw(self, ox, oy, s):
        xp.quadstrip(self.col['magenta'], self._quad_cw(ox, oy, s))

    def c_quadstrip_ccw(self, ox, oy, s):
        xp.quadstrip(self.col['magenta'], self._quad_ccw(ox, oy, s))

    def c_linesStipple(self, ox, oy, s):
        xp.linesStipple(self.col['cyan'], [(ox, oy), (ox + s, oy + s)], 4.0, 2.0)

    def c_lineStripStipple(self, ox, oy, s):
        xp.lineStripStipple(self.col['cyan'],
                            [(ox, oy), (ox + s / 2, oy + s), (ox + s, oy)], 4.0, 2.0)

    def c_lineLoopStipple(self, ox, oy, s):
        xp.lineLoopStipple(self.col['cyan'], [(ox, oy), (ox + s, oy), (ox + s / 2, oy + s)], 4.0, 2.0)

    def _tri_c(self, ox, oy, s):
        return [(ox, oy, self.col['red']),
                (ox + s, oy, self.col['green']),
                (ox + s / 2, oy + s, self.col['blue'])]

    def c_linesc(self, ox, oy, s):
        xp.linesc([(ox, oy, self.col['red']), (ox + s, oy + s, self.col['green']),
                   (ox, oy + s, self.col['blue']), (ox + s, oy, self.col['yellow'])])

    def c_lineStripc(self, ox, oy, s):
        xp.lineStripc(self._tri_c(ox, oy, s) + [(ox, oy, self.col['white'])])

    def c_lineLoopc(self, ox, oy, s):
        xp.lineLoopc(self._tri_c(ox, oy, s))

    def c_polygonc_cw(self, ox, oy, s):
        xp.polygonc(self._colorize(self._diamond_cw(ox, oy, s)))  # interpolated gradient fill

    def c_polygonc_ccw(self, ox, oy, s):
        xp.polygonc(self._colorize(self._diamond_ccw(ox, oy, s)))

    def c_quadstripc_cw(self, ox, oy, s):
        xp.quadstripc(self._colorize(self._quad_cw(ox, oy, s)))

    def c_quadstripc_ccw(self, ox, oy, s):
        xp.quadstripc(self._colorize(self._quad_ccw(ox, oy, s)))

    def c_linescWidth(self, ox, oy, s):
        xp.linescWithWidth(3.0, [(ox, oy, self.col['red']), (ox + s, oy + s, self.col['green'])])

    def c_lineStripcWidth(self, ox, oy, s):
        xp.lineStripcWithWidth(3.0, self._tri_c(ox, oy, s) + [(ox, oy, self.col['white'])])

    def c_lineLoopcWidth(self, ox, oy, s):
        xp.lineLoopcWithWidth(3.0, self._tri_c(ox, oy, s))

    def c_transform(self, ox, oy, s):
        # transformScale/Rotate operate about the coordinate ORIGIN (0,0), so to
        # transform a shape in place we translate the origin to the shape's pivot
        # first, then draw the shape in coordinates RELATIVE to that pivot.
        h = s / 3.0
        # Red reference triangle, untransformed (drawn at absolute coords).
        xp.lineLoop(self.col['red'], self._tri_c(ox, oy, h))
        # Cyan triangle: same shape, scaled 1.5x about its own center.
        xp.transformPush()
        xp.transformTranslate(ox + h / 2, oy + h / 2)   # origin -> triangle center
        xp.polygonc(self._colorize([(1, 1), (1, -1), (-1, -1), (-1, 1)], self.col['white']))
        xp.transformRotate(0.0, 0.0, 30.0)              # rotates about the pivot
        xp.transformScale(1.5, 1.5)
        xp.lineLoop(self.col['cyan'], [(-h / 2, -h / 2), (h / 2, -h / 2), (0, h / 2)])
        xp.transformPop()

    def c_scissor(self, ox, oy, s):
        # Clip a big polygon to the cell; shrink and overdraw in another color.
        xp.scissorPush()
        xp.scissorSet(left=int(ox), top=int(oy + s), right=int(ox + s), bottom=int(oy))   # left, top, right, bottom
        big = [(ox - 30, oy - 30), (ox - 30, oy + s + 30), (ox + s + 30, oy + s + 30), (ox + s + 30, oy - 30)]
        xp.polygon(self.col['yellow'], big)
        xp.scissorIntersect(left=int(ox) + 10, top=int(oy + s) - 10,
                            right=int(ox + s) + 20, bottom=int(oy) + 10)   # left, top, right, bottom
        xp.polygon(self.col['red'], big)
        xp.scissorPop()

    def c_stencil(self, ox, oy, s):
        # Define a triangular mask, then fill a rect that only shows through it.
        # Winding does not matter for either polygon, so a blank cell here means
        # the stencil is broken rather than the geometry.  Expected: a
        # triangular slice of the green square (the overlap of the mask triangle
        # and the full square).
        xp.clearStencilMask()
        mask_tri = [(ox, oy), (ox + s / 2, oy + s), (ox + s, oy)]        # CW
        green_quad = [(ox, oy), (ox, oy + s), (ox + s, oy + s), (ox + s, oy)]  # CW perimeter
        with xp.setupStencilMask(1, 1):
            xp.polygon(self.col['white'], mask_tri)
        xp.useStencilMask(1, 1)
        xp.polygon(self.col['green'], green_quad)
        xp.clearStencilMask()
