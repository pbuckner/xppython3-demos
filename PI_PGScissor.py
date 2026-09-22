"""
PI_PGScissor.py -- minimal scissor (clip rectangle) example for the
XPLMPanelGraphics API, derived from the scissorDraw() snippet at
https://xppython3.rtfd.io/en/latest/development/modules/panelgraphics_state.html

ONE floating PanelGraphics window. The draw callback is the doc example
verbatim in structure:

    - translate the origin to the window's bottom-left corner, so all drawing
      can use window-LOCAL coordinates;
    - fill the whole window with RED;
    - inside a scissor context, set a clip rectangle and fill the whole window
      again with GREEN.

The green polygon covers the entire window, so the ONLY thing that can confine
it to a sub-rectangle is the scissor. Anything less than "green exactly inside
the scissor rect, red everywhere else" is a scissor failure, not a geometry
mistake.

Both xp.transformContext() and xp.scissorContext() are context managers that
push on entry and pop on exit, so the pairs stay balanced even if the drawing
between them raises.

    xp.scissorSet(left, top, right, bottom)

Note the argument values are absolute
panel coordinates -- not insets, and not width/height. xp.scissorIntersect()
takes the same four edges and shrinks the current clip to their intersection.

WORTH VERIFYING WHEN YOU RUN THIS

The doc snippet applies a transform (transformTranslate) and then gives
scissorSet window-LOCAL numbers, demonstrating scissor responds to translation
transform.

Results go to XPPython3Log.txt, prefixed [PGScissor].
"""
from XPPython3 import xp

WIN_W = 200
WIN_H = 100

# The scissor rectangle, in the same window-local coordinates the polygons use:
# (top, left, bottom, right) -- note the order.
SCISSOR_TOP = 80
SCISSOR_LEFT = 20
SCISSOR_BOTTOM = 20
SCISSOR_RIGHT = 180


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics Scissor test"
        self.Sig = "xppython3.pgscissor"
        self.Desc = "Minimal scissor clip-rectangle example"
        self.winID = None
        self.available = False
        self.logged_once = False

    def log(self, msg):
        xp.log(f"[PGScissor] {msg}")

    def scissorDraw(self, windowID, _refCon):
        if not self.available:
            return

        left, _top, _right, bottom = xp.getWindowGeometry(windowID)

        # Window-local: (0, 0) is the bottom-left corner once translated.
        fullWindow = [(0, 0), (0, WIN_H), (WIN_W, WIN_H), (WIN_W, 0)]

        with xp.transformContext():
            xp.transformTranslate(left, bottom)

            # 1. the whole window, red.
            xp.polygon(xp.makeColor(1, 0, 0, 1), fullWindow)

            # 2. the whole window again, green -- but clipped by the scissor.
            with xp.scissorContext():
                xp.scissorSet(SCISSOR_LEFT, SCISSOR_TOP,
                              SCISSOR_RIGHT, SCISSOR_BOTTOM)
                xp.polygon(xp.makeColor(0, 1, 0, 1), fullWindow)

        if not self.logged_once:
            self.logged_once = True
            self.log(f"first frame: window origin ({left}, {bottom}), "
                     f"scissor (top={SCISSOR_TOP}, left={SCISSOR_LEFT}, "
                     f"bottom={SCISSOR_BOTTOM}, right={SCISSOR_RIGHT})")

    def createWindow(self):
        (l, t, _r, _b) = xp.getScreenBoundsGlobal()
        left = l + 140
        top = t - 140
        self.winID = xp.createWindowEx(
            left=left, top=top, right=left + WIN_W, bottom=top - WIN_H,
            visible=1,
            draw=self.scissorDraw,
            decoration=xp.WindowDecorationRoundRectangle,
            layer=xp.WindowLayerFloatingWindows,
            contentType=xp.WindowContentTypePanelGraphics)
        xp.setWindowPositioningMode(self.winID, xp.WindowCenterOnMonitor, -1)
        xp.setWindowTitle(self.winID, "Scissor Demo"
                          if self.available else "Scissor N/A (XPLM<440)")
        self.log(f"window {self.winID} ({WIN_W}x{WIN_H})")

    def XPluginStart(self):
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        self.available = hasattr(xp, 'scissorSet')
        if not self.available:
            self.log("scissor API not available (needs XPLM440 / X-Plane 12.4)")
        self.createWindow()
        return 1

    def XPluginStop(self):
        if self.winID:
            xp.destroyWindow(self.winID)
            self.winID = None
