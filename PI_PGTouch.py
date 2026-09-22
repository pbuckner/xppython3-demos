"""PI_PGTouch.py -- exercise the XPLMPanelGraphics touch-zone API (new in XPLM440 /
X-Plane 12.4.4): accumulateTouchZone / windowSetTouchEventHandler /
avionicsSetTouchEventHandler and the TouchZone_* constants.

INTERACTIVE battery (in a floating PanelGraphics window).  Each frame
the draw callback registers an Identifier-type touch zone over a drawn
button via accumulateTouchZone and colors it by the returned
held-state. Clicking the button should fire the window touch handler,
which logs (identifier, status, x, y, dx, dy, button, refcon) and
records the last event for on-screen display. This validates the
XPLMTouchEvent_f callback + refcon passthrough end to end.

Results go to XPPython3Log.txt, prefixed [PGTouch].

"""
from XPPython3 import xp

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 12.0
ZONE_ID = 42


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics Touch test"
        self.Sig = "xppython3.pgtouch"
        self.Desc = "Regression test of the XPLMPanelGraphics touch-zone API"
        self._checks = 0
        self._errors = 0
        self.available = False
        self.winID = None
        self.font = None
        self.refcon = ["touch-refcon-sentinel"]
        self.lastEvent = None
        self.eventCount = 0
        self.handlerSet = False

    def log(self, msg=''):
        print(f"[PGTouch]: {msg}", flush=True)

    def error(self, msg=''):
        self._errors += 1
        print(f"[PGTouch]: ** ERROR ** {msg}", flush=True)

    def check(self, prompt, ok):
        self._checks += 1
        if not ok:
            self.error(prompt)

    def expectError(self, label, excType, fn, *args, **kwargs):
        self._checks += 1
        try:
            fn(*args, **kwargs)
        except excType:
            return
        except Exception as e:  # noqa: BLE001
            self.error(f'{label}: raised {type(e).__name__} ({e!r}), expected {excType.__name__}')
            return
        self.error(f'{label}: no exception raised, expected {excType.__name__}')

    def expectOk(self, label, fn, *args, **kwargs):
        self._checks += 1
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            self.error(f'{label}: raised {type(e).__name__} ({e!r}), expected success')
        return None

    # ---- lifecycle -----------------------------------------------------------

    def XPluginStart(self):
        versions = xp.getVersions()
        self.log(f"X-Plane {versions[0]}, XPLM {versions[1]}")
        try:
            xp.makeColor(1.0, 1.0, 1.0, 1.0)
            self.available = True
        except RuntimeError as e:
            self.available = False
            self.log(f"XPLMPanelGraphics not available: {e}")
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        self.createWindow()          # window first: needed for handler registration
        if self.available:
            self.createFont()
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def XPluginStop(self):
        # Remove our handler before the window goes away.
        if self.available and self.winID is not None and self.handlerSet:
            try:
                xp.windowSetTouchEventHandler(self.winID, None)
            except Exception as e:  # noqa: BLE001
                self.error(f'windowSetTouchEventHandler(None) at stop: {e!r}')
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

    # ---- the touch event handler --------------------------------------------

    def onTouch(self, identifier, status, x, y, dx, dy, button, refcon):
        self.eventCount += 1
        self.lastEvent = (identifier, status, x, y, dx, dy, button)
        # Verify our refcon object is delivered unchanged (identity).
        if refcon is not self.refcon:
            self.error(f'touch handler refcon mismatch: got {refcon!r}')
        self.log(f"touch id={identifier} status={status} xy=({x},{y}) d=({dx},{dy}) btn={button} refcon={refcon!r}")
        return

    # ---- window --------------------------------------------------------------

    def createFont(self):
        ttf = xp.getSystemPath() + FONT_TTF
        self.font = xp.createFont(xp.CharSetASCII)
        xp.fontAddFace(self.font, ttf)

    def createWindow(self):
        width, height = 320, 200
        (l, t, _r, _b) = xp.getScreenBoundsGlobal()
        left = l + 180
        top = t - 180
        params = [
            left, top, left + width, top - height,
            1,
            self.drawWindow,
            None, None, None, None,
            [],
            xp.WindowDecorationRoundRectangle,
            xp.WindowLayerFloatingWindows,
            None,
            xp.WindowContentTypePanelGraphics,
            None, None
        ]
        self.winID = xp.createWindowEx(params)
        xp.setWindowPositioningMode(self.winID, xp.WindowCenterOnMonitor, -1)
        xp.setWindowTitle(self.winID, "Touch test"
                          if self.available else "Touch N/A (XPLM<440)")
        xp.windowSetTouchEventHandler(self.winID, self.onTouch, self.refcon)

    def drawWindow(self, inWindowID, _inRefcon):
        if self.font is None or not self.available:
            return
        (l, t, _r, _b) = xp.getWindowGeometry(inWindowID)
        white = xp.makeColor(1, 1, 1, 1)
        dim = xp.makeColor(0.5, 0.5, 0.5, 1)

        # Button rectangle (a bit inside the window).
        bx0, by1 = l + 30, t - 44
        bx1, by0 = bx0 + 120, by1 - 44

        try:
            held = xp.accumulateTouchZone(xp.TouchZone_Identifier,
                                          bx0, by1, bx1, by0, None, ZONE_ID)
        except Exception as e:  # noqa: BLE001
            held = False
            self.error(f'accumulateTouchZone in draw: {e!r}')

        # Draw the button, filled by held-state.
        rectcol = xp.makeColor(1, 0.6, 0.1, 1) if held else xp.makeColor(0.2, 0.3, 0.6, 1)
        xp.polygon(rectcol, [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)])
        xp.lineLoop(white, [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)])
        xp.fontDrawString(self.font, white, LABEL_SIZE, bx0 + 12, by0 + 16,
                          "HELD" if held else "click me", xp.JustLeft)

        # Status text.
        y = t - 120
        xp.fontDrawString(self.font, white, LABEL_SIZE, l + 12, y,
                          f"events: {self.eventCount}  held: {held}", xp.JustLeft)
        if self.lastEvent is not None:
            xp.fontDrawString(self.font, dim, LABEL_SIZE, l + 12, y - 20,
                              f"last: id={self.lastEvent[0]} st={self.lastEvent[1]} xy=({self.lastEvent[2]}"
                              f"{self.lastEvent[3]}) btn={self.lastEvent[6]}",
                              xp.JustLeft)
        else:
            xp.fontDrawString(self.font, dim, LABEL_SIZE, l + 12, y - 20,
                              "(no touch events yet)", xp.JustLeft)
