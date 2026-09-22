"""PI_PGRetained.py -- exercise the XPLMPanelGraphics *retained drawing* API
                    (XPLMBeginRetainedDrawing / EndRetainedDrawing /
                     DrawRetained / DestroyRetainedDrawing, new in XPLM440).

Retained drawing records a batch of panel-graphics calls once into an opaque
handle, then replays it cheaply any number of times per frame and across
frames. This plugin is a standalone regression test for the wrapper and a
visual check that replay matches immediate-mode drawing.

RECORD + REPLAY visual battery (in a floating window draw callback).
On the first frame it records a small motif into a retained drawing
(inside the draw phase, where the GL/panel context is valid), then
every frame replays that one handle across several tiles under
different transforms. A "reference" tile draws the same motif in
immediate mode; the plain-replay tile must match it pixel-for-pixel.
The first frame also exercises the live guards that DO touch the SDK
(nested begin, unbalanced end) now that we are in a draw phase.

Results go to XPPython3Log.txt, prefixed [PGRetained].

"""
from XPPython3 import xp

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 10.0

CELL = 84          # grid cell size, pixels
PAD = 12           # inset within each cell
MOTIF = CELL - 2 * PAD   # motif drawn in local coords 0..MOTIF
TITLE_H = 24       # header strip inside the window


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics retained-drawing test"
        self.Sig = "xppython3.pgretained"
        self.Desc = "Regression test of the XPLMPanelGraphics retained-drawing API"
        self._checks = 0
        self._errors = 0
        self.available = False
        self.recorded = False
        self.winID = None
        self.font = None
        self.col = {}
        self.retained = None      # handle for the primary motif

    # ---- tiny check/log helpers ---------------------------------------------

    def log(self, msg=''):
        print(f"[PGRetained]: {msg}", flush=True)

    def error(self, msg=''):
        self._errors += 1
        print(f"[PGRetained]: ** ERROR ** {msg}", flush=True)

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

        # Probe availability without touching GL: makeColor is pure and is the
        # only routine safe to call outside a draw phase.
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
        # Destroy retained drawings BEFORE the font/atlas they may reference.
        if self.retained is not None:
            xp.destroyRetainedDrawing(self.retained)
            self.retained = None
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

    def buildColors(self):
        self.col = {
            'red': xp.makeColor(1, 0, 0, 1),
            'green': xp.makeColor(0, 1, 0, 1),
            'blue': xp.makeColor(0, 0, 1, 1),
            'yellow': xp.makeColor(1, 1, 0, 1),
            'cyan': xp.makeColor(0, 1, 1, 1),
            'white': xp.makeColor(1, 1, 1, 1),
        }

    # ---- window --------------------------------------------------------------

    def createFont(self):
        ttf = xp.getSystemPath() + FONT_TTF
        self.font = xp.createFont(xp.CharSetASCII)
        xp.fontAddFace(self.font, ttf)
        self.log(f"font created from {ttf}")

    def tiles(self):
        """List of (label, kind) -- one per grid cell, left to right."""
        t = [
            ("reference", "ref"),       # immediate-mode motif -- the ground truth
            ("replay", "plain"),        # drawRetained, no transform -> must match ref
            ("replay+rot", "rot"),      # replayed, rotated about its center
            ("replay+scale", "scale"),  # replayed, scaled up about its center
        ]
        return t

    def createWindow(self):
        n = len(self.tiles())
        width = n * CELL + 2 * PAD
        height = CELL + TITLE_H + 2 * PAD

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
            None, None
        ]
        self.winID = xp.createWindowEx(params)
        xp.setWindowPositioningMode(self.winID, xp.WindowCenterOnMonitor, -1)
        xp.setWindowTitle(self.winID, "PG retained test"
                          if self.available else "PG retained N/A (XPLM<440)")
        self.log(f"window {self.winID} ({width}x{height}, {n} tiles)")

    # ---- the motif (drawn in LOCAL coords 0..MOTIF) --------------------------

    def draw_motif(self):
        """The unit of work we record once and replay many times. Drawn in
        local coordinates 0..MOTIF so a translate places it at any tile."""
        m = MOTIF
        # CW-wound filled diamond (green). CW to dodge the XP 12.4 XPLMPolygon
        # CW-only fill bug -- a blank fill here means retained/replay dropped it,
        # not a winding problem.
        diamond = [(m / 2, 0), (0, m / 2), (m / 2, m), (m, m / 2)]  # bottom,left,top,right = CW
        xp.polygon(self.col['green'], diamond)
        # White triangular border (lineLoop) so the outline is easy to compare.
        xp.lineLoop(self.col['white'], [(0, 0), (m, 0), (m / 2, m)])
        # Per-vertex-colored cross so orientation under rotate/scale is obvious.
        xp.linesc([(0, 0, self.col['red']), (m, m, self.col['blue'])])
        # A recorded glyph -- fonts are captured by retained drawing too.
        if self.font is not None:
            xp.fontDrawString(self.font, self.col['white'], LABEL_SIZE,
                              m / 2 - 3, m / 2 - 5, "R", xp.JustLeft)

    # ---- Part B: record once, replay every frame -----------------------------

    def record(self):
        """First-frame recording. Runs inside the draw callback so the GL/panel
        context is valid. Also exercises the live guards that reach the SDK."""
        self.recorded = True

        xp.beginRetainedDrawing()
        # Live nesting guard: a second begin while recording must be rejected.
        self.expectError('nested begin', RuntimeError, xp.beginRetainedDrawing)
        self.draw_motif()
        self.retained = xp.endRetainedDrawing()
        # After a balanced end there is no active recording again.
        self.expectError('end after balanced end', RuntimeError, xp.endRetainedDrawing)

        got_handle = self.retained is not None
        self._checks += 1
        if not got_handle:
            self.error('endRetainedDrawing returned None (expected a handle)')
        else:
            self.log(f"recorded motif -> retained handle {self.retained!r}")

    def drawWindow(self, inWindowID, _inRefcon):
        if not self.available:
            return
        (l, t, _r, _b) = xp.getWindowGeometry(inWindowID)

        if not self.recorded:
            self.record()

        grid_top = t - TITLE_H
        for i, (label, kind) in enumerate(self.tiles()):
            ox = l + PAD + i * CELL
            oy = grid_top - CELL          # tile lower-left y
            try:
                self.draw_tile(kind, ox + PAD, oy + PAD)
            except Exception as e:  # noqa: BLE001 - report once, keep drawing the rest
                self.error(f'draw {label}: {e!r}')
            if self.font is not None:
                xp.fontDrawString(self.font, self.col['white'], LABEL_SIZE,
                                  ox + 2, oy + CELL - 12, label, xp.JustLeft)
        return

    def draw_tile(self, kind, ox, oy):
        """Draw one tile. (ox, oy) is the motif's lower-left in panel coords."""
        m = MOTIF
        if kind == "ref":
            # Immediate-mode ground truth: translate origin to the tile, draw.
            xp.transformPush()
            xp.transformTranslate(ox, oy)
            self.draw_motif()
            xp.transformPop()
            return

        if self.retained is None:
            return

        if kind == "plain":
            xp.transformPush()
            xp.transformTranslate(ox, oy)
            xp.drawRetained(self.retained)
            xp.transformPop()
        elif kind == "rot":
            # Rotate about the motif's center: translate to center, rotate, then
            # back off by half so local (0..m) lands centered on the pivot.
            xp.transformPush()
            xp.transformTranslate(ox + m / 2, oy + m / 2)
            xp.transformRotate(0.0, 0.0, 25.0)
            xp.transformTranslate(-m / 2, -m / 2)
            xp.drawRetained(self.retained)
            xp.transformPop()
        elif kind == "scale":
            xp.transformPush()
            xp.transformTranslate(ox + m / 2, oy + m / 2)
            xp.transformScale(1.3, 1.3)
            xp.transformTranslate(-m / 2, -m / 2)
            xp.drawRetained(self.retained)
            xp.transformPop()
