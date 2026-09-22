"""
PI_PGSVTFeatures.py -- interactive explorer for the XPLM440 SVT display API
(XPLMPanelGraphics: createSVTDisplay / svtDisplayDrawIn / destroySVTDisplay).

A single pop-out avionics device draws ONE SVT view plus a label block.

  SPACE  cycle through the nine XPLMSVTFeatures values (Terrain, Runways,
         Obstacles, FlightPath, Traffic, AirportSigns, ILSHoops,
         HorizonHeading, All).  The selected feature is the *only* feature
         passed to svtDisplayDrawIn().

  TAB    cycle through the ten dataOverride selections: the nine fields of
         XPLMSVTCustomData_t (pitchDeg, rollDeg, headingMagDeg, magVarDeg,
         indicatedAltFt, baroSettingInHg, hsiSource, hdefDots, vdefDots)
         plus "None".  With "None" selected no dataOverrides struct is passed
         at all (sim state is used) and every override value is reset to its
         default.

  + / -  add / subtract one step from the currently selected override field
         (1.0, except indicatedAltFt which steps by 100 ft).  No effect while
         "None" is selected.

  [ / ]  step pixelsPerDegree down / up through PPD_VALUES. (Keys are
         left-square-bracket / right-square-bracket.) Unlike `features`,
         pixelsPerDegree is a CREATE-time field of XPLMCreateSVT_t, not a
         per-draw argument, so there is no way to change it on a live handle:
         each step destroys the SVT display and creates a new one.  The new
         handle is created BEFORE the old one is destroyed, so a failed create
         leaves the current view untouched.

pixelsPerDegree is the vertical scale of the 3-D view at the center of the
display -- larger values zoom in.  It must be > 0; the G1000 PFD uses 14.

Four fields are backed by datarefs -- pitchDeg/theta, rollDeg/phi,
headingMagDeg/psi, indicatedAltFt/h_ind.  Such a field tracks its dataref live
every frame while it is not the selected override; selecting it seeds it from
the current dataref value and then freezes it so +/- can drive it.  The
remaining fields default to 0 except baroSettingInHg, which defaults to 29.92.

Keys are grabbed with a key sniffer, and only while the device's popup is
visible, so they behave normally everywhere else in the sim.

Terrain only appears once tiles are loaded -- be in a flight, not the main
menu.  Log output is prefixed [PGSVTFeatures].
"""
from XPPython3 import xp

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 15.0
LINE_H = 19.0

SCREEN_W = 900
SCREEN_H = 620
BEZEL_PAD = 20
MARGIN = 12

# SVT viewport occupies the top of the screen; labels live underneath it.
# TEXT_TOP allows four header lines plus the nine override fields; raising it by
# one LINE_H (over the original 232) makes room for the pixelsPerDegree line.
TEXT_TOP = 251                       # first text baseline
SVT_BOTTOM = TEXT_TOP + 26
SVT_TOP = SCREEN_H - MARGIN

# (constant name, attribute on xp) -- resolved at enable.
FEATURE_NAMES = ['SVT_Terrain', 'SVT_Runways', 'SVT_Obstacles', 'SVT_FlightPath',
                 'SVT_Traffic', 'SVT_AirportSigns', 'SVT_ILSHoops',
                 'SVT_HorizonHeading', 'SVT_All']

# The nine XPLMSVTCustomData_t fields, in struct order (which is the order
# svtDisplayDrawIn() expects the sequence in), with their units.
OVERRIDE_FIELDS = [('pitchDeg', 'deg'),
                   ('rollDeg', 'deg'),
                   ('headingMagDeg', 'deg'),
                   ('magVarDeg', 'deg'),
                   ('indicatedAltFt', 'ft'),
                   ('baroSettingInHg', 'inHg'),
                   ('hsiSource', 'enum'),
                   ('hdefDots', 'dots'),
                   ('vdefDots', 'dots')]
NONE_INDEX = len(OVERRIDE_FIELDS)     # the tenth selection

# Four of the nine fields have an obvious sim counterpart.  A field backed by a
# dataref tracks that dataref live every frame while it is NOT the selected
# override; selecting it seeds it from the dataref and freezes it for +/- edits.
DATAREF_PATHS = {0: 'sim/flightmodel/position/theta',     # pitchDeg
                 1: 'sim/flightmodel/position/phi',       # rollDeg
                 2: 'sim/flightmodel/position/psi',       # headingMagDeg
                 4: 'sim/flightmodel/misc/h_ind'}         # indicatedAltFt

# Fallback defaults for the fields with no dataref behind them.
STATIC_DEFAULTS = {3: 0.0,       # magVarDeg
                   5: 29.92,     # baroSettingInHg
                   6: 0.0,       # hsiSource
                   7: 0.0,       # hdefDots
                   8: 0.0}       # vdefDots

# +/- step per field (altitude moves in feet, so 1.0 is uselessly small).
STEPS = {4: 100.0}
DEFAULT_STEP = 1.0

# createSVTDisplay(pilotIndex, pixelsPerDegree).  pilotIndex 0 = pilot-side AHRS,
# 1 = copilot; this explorer stays on the pilot side.
PILOT_INDEX = 0

# pixelsPerDegree values to step through with [ and ].  Doubling either side of
# the G1000's 14 makes the zoom change obvious; the smallest and largest are
# deliberately extreme to show the horizon compress / expand.
PPD_VALUES = [3.5, 7.0, 14.0, 28.0, 56.0]
PPD_DEFAULT_INDEX = PPD_VALUES.index(14.0)


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics SVT feature explorer"
        self.Sig = "xppython3.pgsvtfeatures"
        self.Desc = "Interactive SVT features / dataOverrides explorer (XPLM440)"
        self.available = False
        self.dev = None
        self.svt = None
        self.font = None
        self.sniffer = None
        self.featureIndex = 0
        self.overrideIndex = NONE_INDEX          # start on "None"
        self.ppdIndex = PPD_DEFAULT_INDEX        # index into PPD_VALUES
        self.recreates = 0                       # SVT handles created after the first
        self.values = [0.0] * len(OVERRIDE_FIELDS)
        self.refs = {}                           # field index -> dataref, at enable
        self.features = []                       # int values, filled at enable

    def log(self, msg=''):
        print(f"[PGSVTFeatures]: {msg}", flush=True)

    # ---- lifecycle -----------------------------------------------------------

    def XPluginStart(self):
        versions = xp.getVersions()
        self.log(f"X-Plane {versions[0]}, XPLM {versions[1]}")
        try:
            xp.makeColor(1.0, 1.0, 1.0, 1.0)
            self.available = True
        except RuntimeError as e:
            self.log(f"XPLMPanelGraphics not available: {e}")
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        if not self.available:
            return 1
        self.features = [getattr(xp, name) for name in FEATURE_NAMES]
        for i, path in DATAREF_PATHS.items():
            ref = xp.findDataRef(path)
            if ref is None:
                self.log(f"dataref not found: {path} (field {OVERRIDE_FIELDS[i][0]} will stay 0)")
            else:
                self.refs[i] = ref
        self.resetValues()
        self.createFont()
        self.buildDevice()
        self.sniffer = xp.registerKeySniffer(self.keySniffer, before=1)
        return 1

    def XPluginStop(self):
        if self.sniffer is not None:
            xp.unregisterKeySniffer(self.keySniffer, before=1)
            self.sniffer = None
        if self.svt is not None:
            xp.destroySVTDisplay(self.svt)
            self.svt = None
        if self.dev is not None:
            xp.destroyAvionics(self.dev)
            self.dev = None
        if self.font is not None:
            xp.destroyFont(self.font)
            self.font = None

    # ---- setup ---------------------------------------------------------------

    def createFont(self):
        self.font = xp.createFont(xp.CharSetASCII)
        xp.fontAddFace(self.font, xp.getSystemPath() + FONT_TTF)

    def ppd(self):
        return PPD_VALUES[self.ppdIndex]

    def buildDevice(self):
        try:
            self.svt = xp.createSVTDisplay(PILOT_INDEX, self.ppd())
        except Exception as e:  # noqa: BLE001
            self.log(f"createSVTDisplay failed: {e!r}")
            return
        try:
            self.dev = xp.createAvionicsEx(
                screenWidth=SCREEN_W,
                screenHeight=SCREEN_H,
                bezelWidth=SCREEN_W + 2 * BEZEL_PAD,
                bezelHeight=SCREEN_H + 2 * BEZEL_PAD,
                screenOffsetX=BEZEL_PAD,
                screenOffsetY=BEZEL_PAD,
                drawOnDemand=0,
                screenDraw=self.screenDraw,
                bezelDraw=self.bezelDraw,
                deviceID="xppython3.pgsvtfeatures.device",
                deviceName="SVT features",
                refCon=None,
                # Required: panel-graphics calls (incl. svtDisplayDrawIn) are a
                # violation under the default OpenGL content type.
                contentType=xp.WindowContentTypePanelGraphics,
            )
        except Exception as e:  # noqa: BLE001
            self.log(f"createAvionicsEx failed: {e!r}")
            return
        try:
            xp.setAvionicsPopupVisible(self.dev)
        except Exception as e:  # noqa: BLE001
            self.log(f"setAvionicsPopupVisible failed ({e!r}); open it from the device menu")
        self.log(f"device built; SPACE=feature, TAB=override, +/- = value +/-1.0, "
                 f"[ / ] = pixelsPerDegree (now {self.ppd():g})")

    # ---- pixelsPerDegree -----------------------------------------------------

    def stepPPD(self, delta):
        """Move through PPD_VALUES, recreating the SVT display at the new scale.

        pixelsPerDegree is a create-time field of XPLMCreateSVT_t, so it cannot
        be changed on a live handle -- the display has to be rebuilt.  The new
        handle is created first: if createSVTDisplay raises, the old handle is
        left in place and the view keeps drawing at the previous scale.
        """
        newIndex = self.ppdIndex + delta
        if not 0 <= newIndex < len(PPD_VALUES):
            return                                  # already at an end; no-op
        oldIndex, oldSvt = self.ppdIndex, self.svt
        self.ppdIndex = newIndex
        try:
            newSvt = xp.createSVTDisplay(PILOT_INDEX, self.ppd())
        except Exception as e:  # noqa: BLE001
            self.ppdIndex = oldIndex                # keep the working handle
            self.log(f"createSVTDisplay(pixelsPerDegree={PPD_VALUES[newIndex]:g}) "
                     f"failed, staying at {self.ppd():g}: {e!r}")
            return
        self.svt = newSvt
        self.recreates += 1
        if oldSvt is not None:
            try:
                xp.destroySVTDisplay(oldSvt)
            except Exception as e:  # noqa: BLE001
                self.log(f"destroySVTDisplay (old handle): {e!r}")
        self.log(f"pixelsPerDegree -> {self.ppd():g} "
                 f"(SVT display recreated, {self.recreates} so far)")

    # ---- override values -----------------------------------------------------

    def defaultValue(self, i):
        """Current dataref value for a dataref-backed field, else its static default."""
        if i in self.refs:
            return xp.getDataf(self.refs[i])
        return STATIC_DEFAULTS.get(i, 0.0)

    def resetValues(self):
        self.values = [self.defaultValue(i) for i in range(len(OVERRIDE_FIELDS))]

    def trackDatarefs(self):
        """Every dataref-backed field except the selected one follows the sim."""
        for i in self.refs:
            if i != self.overrideIndex:
                self.values[i] = xp.getDataf(self.refs[i])

    # ---- keyboard ------------------------------------------------------------

    def visible(self):
        return self.dev is not None and xp.isAvionicsPopupVisible(self.dev)

    def keySniffer(self, key, flags, vKey, _refCon):
        if not (flags & xp.DownFlag) or not self.visible():
            return 1
        if vKey == xp.VK_SPACE:
            self.featureIndex = (self.featureIndex + 1) % len(self.features)
        elif vKey == xp.VK_TAB:
            self.overrideIndex = (self.overrideIndex + 1) % (NONE_INDEX + 1)
            # Newly selected field starts from its default (the live dataref
            # value where there is one); "None" resets every field.
            if self.overrideIndex == NONE_INDEX:
                self.resetValues()
            else:
                self.values[self.overrideIndex] = self.defaultValue(self.overrideIndex)
        elif key in (ord('+'), ord('=')) or vKey == xp.VK_ADD:
            self.bump(1)
        elif key in (ord('-'), ord('_')) or vKey == xp.VK_SUBTRACT:
            self.bump(-1)
        elif key == ord('['):
            self.stepPPD(-1)
        elif key == ord(']'):
            self.stepPPD(1)
        else:
            return 1
        return 0        # consume keys we acted on

    def bump(self, sign):
        if self.overrideIndex == NONE_INDEX:
            return
        self.values[self.overrideIndex] += sign * STEPS.get(self.overrideIndex, DEFAULT_STEP)

    # ---- drawing -------------------------------------------------------------

    def bezelDraw(self, _r, _g, _b, _refcon):
        dark = xp.makeColor(0.06, 0.06, 0.08, 1)
        xp.polygon(dark, [(0, 0), (SCREEN_W + 2 * BEZEL_PAD, 0),
                          (SCREEN_W + 2 * BEZEL_PAD, SCREEN_H + 2 * BEZEL_PAD),
                          (0, SCREEN_H + 2 * BEZEL_PAD)])

    def screenDraw(self, _refcon):
        if not self.available or self.svt is None:
            return

        self.trackDatarefs()

        white = xp.makeColor(1, 1, 1, 1)
        dim = xp.makeColor(0.55, 0.6, 0.65, 1)
        hot = xp.makeColor(1.0, 0.85, 0.2, 1)

        featureName = FEATURE_NAMES[self.featureIndex]
        featureValue = self.features[self.featureIndex]
        overrideName = ('None' if self.overrideIndex == NONE_INDEX
                        else OVERRIDE_FIELDS[self.overrideIndex][0])

        # Text and the frame go down FIRST: SVT installs its own 3-D projection
        # and is not documented to restore it, so anything drawn afterwards may
        # land in the wrong space.
        x0, x1 = MARGIN, SCREEN_W - MARGIN
        xp.lineLoop(dim, [(x0, SVT_BOTTOM), (x1, SVT_BOTTOM), (x1, SVT_TOP), (x0, SVT_TOP)])

        y = TEXT_TOP
        xp.fontDrawString(self.font, white, LABEL_SIZE, x0, y,
                          f"FEATURE  [{self.featureIndex + 1}/{len(self.features)}]  "
                          f"{featureName} = {featureValue}   (SPACE to cycle)",
                          xp.JustLeft)
        y -= int(LINE_H)
        step = STEPS.get(self.overrideIndex, DEFAULT_STEP)
        xp.fontDrawString(self.font, white, LABEL_SIZE, x0, y,
                          f"OVERRIDE [{self.overrideIndex + 1}/{NONE_INDEX + 1}]  "
                          f"{overrideName}   (TAB to cycle, +/- to adjust by {step:g})",
                          xp.JustLeft)
        y -= int(LINE_H)
        atEnd = ('  [min]' if self.ppdIndex == 0
                 else '  [max]' if self.ppdIndex == len(PPD_VALUES) - 1
                 else '')
        xp.fontDrawString(self.font, white, LABEL_SIZE, x0, y,
                          f"PPD      [{self.ppdIndex + 1}/{len(PPD_VALUES)}]  "
                          f"pixelsPerDegree = {self.ppd():g}{atEnd}   "
                          f"([ / ] to step -- recreates the display, "
                          f"{self.recreates} so far)",
                          xp.JustLeft)
        y -= int(LINE_H)
        xp.fontDrawString(self.font, dim, LABEL_SIZE, x0, y,
                          ("dataOverrides = None (sim state)"
                           if self.overrideIndex == NONE_INDEX
                           else "dataOverrides = the nine values below"),
                          xp.JustLeft)
        y -= int(LINE_H * 1.4)

        for i, (name, units) in enumerate(OVERRIDE_FIELDS):
            selected = i == self.overrideIndex
            marker = '>' if selected else ' '
            color = hot if selected else dim
            if i not in self.refs:
                source = ''
            elif selected:
                source = f"held (seeded from {DATAREF_PATHS[i]})"
            else:
                source = f"live <- {DATAREF_PATHS[i]}"
            xp.fontDrawString(self.font, color, LABEL_SIZE, x0, y,
                              f"{marker} {name:<16} {self.values[i]:9.1f} {units:<5} {source}",
                              xp.JustLeft)
            y -= int(LINE_H)

        # One SVT view, with only the currently-selected feature enabled.
        overrides = None if self.overrideIndex == NONE_INDEX else list(self.values)
        if overrides is not None:
            overrides[6] = int(overrides[6])        # hsiSource is an int field
        try:
            xp.svtDisplayDrawIn(self.svt, featureValue,
                                x0, SVT_TOP, x1, SVT_BOTTOM, overrides)
        except Exception as e:  # noqa: BLE001
            self.log(f"svtDisplayDrawIn: {e!r}")
            self.svt = None
