"""
PI_PGStencil.py -- exercise the XPLMPanelGraphics stencil-mask API
(new in XPLM440 / X-Plane 12.4.4): beginSetupStencilMask / endSetupStencilMask /
useStencilMask / clearStencilMask.

WHAT IS DRAWN

Two overlapping squares are stamped into two INDEPENDENT stencil bit channels,
in two separate setup passes:

    square A (left,  shifted down) -> bit 0x01
    square B (right, shifted up)   -> bit 0x02

They overlap in the middle, so the window holds four distinguishable regions:
A-only, B-only, A-and-B, and neither. Each region is then painted by drawing a
FULL-WINDOW polygon under a different stencil test. The polygon always covers
the whole window, so the ONLY thing confining it to a region is the test:

    xp.useStencilMask(0x00, 0x03)  -> "outside"  : neither A nor B
    xp.useStencilMask(0x01, 0x01)  -> "A"        : all of A, incl. overlap
    xp.useStencilMask(0x02, 0x02)  -> "B"        : all of B, incl. overlap
    xp.useStencilMask(0x03, 0x03)  -> "A and B"  : the overlap only

THE STAR KNOCKOUT

A 5-point star is stamped into a THIRD channel, bit 0x04, centered so it cuts
across A, B, their overlap and the outside region. The star is a KNOCKOUT:
nothing at all is drawn inside it, so it reads as a hole punched through every
region, exposing the bare undrawn window beneath.

That costs no extra drawing pass and no change to any geometry. Each of the
four passes simply widens its test MASK to include the star bit while leaving
that bit 0 in its reference value, i.e. "...and the star bit must be CLEAR":

    pass 1  use(0x00, 0x07)        neither A nor B, not star
    pass 2  use(0x01, 0x01|0x04)   A set, star clear
    pass 3  use(0x02, 0x02|0x04)   B set, star clear
    pass 4  use(0x03, 0x07)        A and B set, star clear

NOTES ON THE API (all verified against X-Plane 12.4.4 / build 124404)

  - The test is an EQUALITY match: a pixel draws where
    (stencil & mask) == (bits & mask). That expresses AND and NOT, but NOT
    "or" -- for a union you must stamp a dedicated union bit at setup time.
  - Setup writes `bits & mask` into the mask-selected positions only. bits=0
    over a shape ERASES those channels there; it is the only partial clear the
    API offers, since clearStencilMask() wipes the whole buffer.
  - Only 8 bits are significant (0x01-0x80). Higher bits are silently dropped.
    The Python wrapper documents its arguments as 8-bit quantities.
  - The COLOR and ALPHA of setup geometry are both ignored -- only the
    rasterized footprint matters. A fully transparent fill still stamps.
  - A 5-point star is CONCAVE and xp.polygon fills only CONVEX polygons, so the
    star is stamped as a fan of 10 convex triangles. Overlapping fan triangles
    are harmless: setup REPLACEs the same value, so the union is what lands.
    xp.lineLoop draws lines rather than filling, so its white outline takes the
    concave perimeter directly.

EXPECTED RESULT

Three regions in their own colors (gray outside, red A, green B, yellow
overlap), with a star-shaped hole punched clean through all of them. Known-good
white outlines are drawn around both squares and the star AFTER
userStencilMask(0,0), which turns off stencil testing, so a blank or mispainted region reads unambiguously as a
stencil failure rather than as mispositioned geometry. If the stencil API did
nothing at all, the window would be a flat slab of the LAST color drawn
(yellow) with the outlines on top.

Results go to XPPython3Log.txt, prefixed [PGStencil].
"""
import math
from XPPython3 import xp

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 10.0
TITLE_SIZE = 12.0

WIN_W = 420
WIN_H = 340

# Stencil bit channels. Single bits, so the masks are independent and can be
# tested together (0x03) for the intersection.
BIT_A = 0x01
BIT_B = 0x02
BIT_AB = BIT_A | BIT_B
BIT_STAR = 0x04
BIT_ALL = BIT_A | BIT_B | BIT_STAR

# Square geometry. The squares MUST overlap horizontally for the intersection
# pass to have anything to paint: with WIN_W 420 and SQ_INSET 45, A spans
# x=[45, 45+SQ_SIZE] and B spans x=[375-SQ_SIZE, 375], so SQ_SIZE must exceed
# (420 - 2*45)/2 = 165. At 200 the squares share a 70px-wide column.
SQ_SIZE = 200.0
SQ_INSET = 45.0
SQ_OFFSET = 35.0  # vertical stagger of A (down) vs B (up)

# Star geometry: centered, large enough to cut across A, B, the overlap and
# the outside region.
STAR_POINTS = 5
STAR_R_OUTER = 120.0
STAR_R_INNER = 46.0  # ~0.382 * outer, the classic 5-point ratio
STAR_START = math.pi * 0.5  # angle of the first vertex: point straight up


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics Stencil test"
        self.Sig = "xppython3.pgstencil"
        self.Desc = "Stencil-mask demo: two channels, an intersection, and a star knockout"
        self.winID = None
        self.font = None
        self.available = False
        self.logged_once = False

    # ---------------------------------------------------------------- logging

    def log(self, msg):
        xp.log(f"[PGStencil] {msg}")

    # --------------------------------------------------------------- geometry

    def rect(self, left, bottom, right, top):
        """Four CCW-wound corners of a rectangle, as xp.polygon wants them."""
        return [(left, bottom), (right, bottom), (right, top), (left, top)]

    def starVertices(self, cx, cy):
        """2*STAR_POINTS perimeter vertices, alternating outer/inner radius,
        first point straight up."""
        pts = []
        for i in range(2 * STAR_POINTS):
            ang = STAR_START + i * math.pi / STAR_POINTS
            rad = STAR_R_INNER if (i & 1) else STAR_R_OUTER
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        return pts

    # ---------------------------------------------------------------- stencil

    def stampRect(self, bit, left, bottom, right, top):
        """Stamp a rectangle into stencil channel `bit`. The fill color is
        irrelevant (color and alpha are both ignored during setup) but a
        visible opaque magenta is used so that an implementation leaking setup
        geometry to the screen would be obvious."""
        with xp.setupStencilMask(bit, bit):
            xp.polygon(xp.makeColor(1.0, 0.0, 1.0, 1.0),
                       self.rect(left, bottom, right, top))

    def stampStar(self, bit, cx, cy):
        """Stamp a star into channel `bit` as a fan of CONVEX triangles.

        10 triangles (center, p[i], p[i+1]), each one convex. This is REQUIRED,
        not defensive: xp.polygon fills only convex polygons, and handing it
        the concave 10-vertex perimeter directly does not fail loudly -- it
        silently fills a different region (a triangle fan anchored on the FIRST
        vertex, so the result even changes if the vertex list is reordered).

        Overlapping fan triangles are harmless because the setup pass REPLACEs
        the same bit value, so the union of the triangles is what lands."""
        pts = self.starVertices(cx, cy)
        n = len(pts)
        magenta = xp.makeColor(1.0, 0.0, 1.0, 1.0)
        with xp.setupStencilMask(bit, bit):
            for i in range(n):
                xp.polygon(magenta, [(cx, cy), pts[i], pts[(i + 1) % n]])

    # ------------------------------------------------------------------- draw

    def drawWindow(self, windowID, _refCon):
        if not self.available:
            return

        (left, top, right, bottom) = xp.getWindowGeometry(windowID)
        fl, ft, fr, fb = float(left), float(top), float(right), float(bottom)

        white = xp.makeColor(1.0, 1.0, 1.0, 1.0)
        outside = xp.makeColor(0.15, 0.15, 0.15, 1.0)   # dark gray
        colorA = xp.makeColor(1.0, 0.0, 0.0, 1.0)       # red
        colorB = xp.makeColor(0.0, 1.0, 0.0, 1.0)       # green
        colorAB = xp.makeColor(1.0, 1.0, 0.0, 1.0)      # yellow

        midY = (fb + ft) * 0.5

        # Square A: left, shifted DOWN. Square B: right, shifted UP.
        aL = fl + SQ_INSET
        aR = aL + SQ_SIZE
        aB = midY - SQ_SIZE * 0.5 - SQ_OFFSET
        aT = aB + SQ_SIZE

        bR = fr - SQ_INSET
        bL = bR - SQ_SIZE
        bB = midY - SQ_SIZE * 0.5 + SQ_OFFSET
        bT = bB + SQ_SIZE

        starCX = (fl + fr) * 0.5
        starCY = midY

        # --- setup: stamp each shape into its own bit channel ---
        self.stampRect(BIT_A, aL, aB, aR, aT)
        self.stampRect(BIT_B, bL, bB, bR, bT)
        self.stampStar(BIT_STAR, starCX, starCY)

        # --- paint each region with a full-window polygon under a test ---
        # Every pass additionally requires the star bit to be CLEAR, which is
        # what makes the star a hole through all four regions.
        full = self.rect(fl, fb, fr, ft)

        xp.useStencilMask(0x00, BIT_ALL)            # neither A nor B, not star
        xp.polygon(outside, full)

        xp.useStencilMask(BIT_A, BIT_A | BIT_STAR)  # all of A, minus the star
        xp.polygon(colorA, full)

        xp.useStencilMask(BIT_B, BIT_B | BIT_STAR)  # all of B, minus the star
        xp.polygon(colorB, full)

        xp.useStencilMask(BIT_AB, BIT_ALL)          # the overlap, minus the star
        xp.polygon(colorAB, full)

        # --- done: disable testing before the known-good overlay ---
        xp.useStencilMask(0, 0)
        xp.clearStencilMask()

        xp.lineLoop(white, self.rect(aL, aB, aR, aT))
        xp.lineLoop(white, self.rect(bL, bB, bR, bT))
        xp.lineLoop(white, self.starVertices(starCX, starCY))

        if self.font:
            xp.fontDrawString(self.font, white, TITLE_SIZE,
                              fl + 8.0, ft - 18.0,
                              "gray/red/green/yellow + star knockout",
                              xp.JustLeft)
            xp.fontDrawString(self.font, white, LABEL_SIZE,
                              fl + 8.0, fb + 8.0,
                              "A=0x01 B=0x02 star=0x04 knocked out "
                              "(mask 0x07, star bit always 0)",
                              xp.JustLeft)

        if not self.logged_once:
            self.logged_once = True
            self.log(f"first frame drawn: window {int(fr - fl)}x{int(ft - fb)}, "
                     f"A=({aL:.0f},{aB:.0f})-({aR:.0f},{aT:.0f}) "
                     f"B=({bL:.0f},{bB:.0f})-({bR:.0f},{bT:.0f}) "
                     f"star=({starCX:.0f},{starCY:.0f}) r={STAR_R_OUTER:.0f}")

    # ---------------------------------------------------------------- plumbing

    def createFont(self):
        ttf = xp.getSystemPath() + FONT_TTF
        self.font = xp.createFont(xp.CharSetASCII)
        xp.fontAddFace(self.font, ttf)

    def createWindow(self):
        (l, t, _r, _b) = xp.getScreenBoundsGlobal()
        left = l + 120
        top = t - 120
        params = [
            left, top, left + WIN_W, top - WIN_H,
            1,
            self.drawWindow,
            None, None, None, None,
            [],
            xp.WindowDecorationRoundRectangle,
            xp.WindowLayerFloatingWindows,
            None,
            xp.WindowContentTypePanelGraphics,
            None,
            None
        ]
        self.winID = xp.createWindowEx(params)
        xp.setWindowPositioningMode(self.winID, xp.WindowCenterOnMonitor, -1)
        xp.setWindowTitle(self.winID, "Stencil Demo"
                          if self.available else "Stencil N/A (XPLM<440)")
        self.log(f"window {self.winID} ({WIN_W}x{WIN_H})")

    # ------------------------------------------------------------- lifecycle

    def XPluginStart(self):
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        # The stencil calls exist only in XPLM440 and up; the wrapper raises
        # RuntimeError rather than crashing if the SDK is older.
        self.available = hasattr(xp, 'beginSetupStencilMask')
        if self.available:
            try:
                self.createFont()
            except Exception as e:
                self.log(f"font unavailable: {e}")
                self.font = None
        else:
            self.log("stencil API not available (needs XPLM440 / X-Plane 12.4)")
        self.createWindow()
        return 1

    def XPluginStop(self):
        if self.winID:
            xp.destroyWindow(self.winID)
            self.winID = None
        if self.font:
            xp.destroyFont(self.font)
            self.font = None
