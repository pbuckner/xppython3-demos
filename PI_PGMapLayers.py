"""
PI_PGMapLayers.py -- interactive explorer for the XPLM440 base-map display API
(XPLMPanelGraphics: createMapDisplay / mapDisplayDrawIn / destroyMapDisplay,
plus mapDisplayScaleMeter, mapDisplayGetNorthHeading and
mapDisplayGetTerrainAltitudes).

A single pop-out avionics device draws ONE map view plus a label block.

  SPACE  cycle through the eight XPLMMapLayers values (Nexrad, IR, Topo,
         Terrain, Water, EGPWS, raw_elev, safe_taxi).  The selected layer is
         the *only* layer passed to mapDisplayDrawIn().  Unlike SVT there is
         no "all" flag, and some layers are mutually exclusive (Nexrad with
         IR or EGPWS), which is another reason to show exactly one at a time.

  TAB    cycle through the sixteen dataOverride selections: the fifteen fields
         of XPLMMapCustomData_t (datLat, datLon, ctrX, ctrY, roseRadius,
         mapRange, orientation, terrainWarn, terrainCaution, acfAlt, gearDown,
         trueRotation, nearestRwyElev, egpwsBrightness, egpwsStyle) plus
         "None".  Shift-TAB walks the same list backwards.  With "None"
         selected no dataOverrides struct is passed at all (live sim state),
         but the values are kept, so cycling back to a field resumes where you
         left it.

  + / -  add / subtract one step from the currently selected override field.
         Step is per-field (0.1 deg for lat/lon, 5 nm for mapRange, 100 ft for
         altitudes, 10 px for the geometry fields, 1 otherwise).  No effect
         while "None" is selected.

  z      reset every override value to its default.  This is the ONLY thing
         that re-reads datLat/datLon from the aircraft -- they do not track it
         live and are not re-seeded on selection, so you can pan the map datum
         with +/- and have it stay where you put it.

Defaults come from three places: five fields track datarefs live (datLat,
datLon, acfAlt, gearDown, trueRotation) while they are not the selected
override; three are derived from the map rectangle (ctrX, ctrY, roseRadius);
the rest are constants.  Selecting a field seeds it from its default and then
freezes it so +/- can drive it.

The scale/north readouts under the map are queried with EXACTLY the arguments
the map is drawn with, as the SDK requires.  Terrain altitudes are only
available after a draw with Map_EGPWS, so that readout lags by one frame.

Terrain only appears once tiles are loaded -- be in a flight, not the main
menu.  Log output is prefixed [PGMapLayers].
"""
from XPPython3 import xp

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 14.0
LINE_H = 18.0

SCREEN_W = 900
SCREEN_H = 760
BEZEL_PAD = 20
MARGIN = 12

# Map viewport occupies the top of the screen; labels live underneath it.
TEXT_TOP = 402                       # first text baseline
MAP_BOTTOM = TEXT_TOP + 26
MAP_TOP = SCREEN_H - MARGIN
MAP_LEFT = MARGIN
MAP_RIGHT = int(MAP_LEFT + (MAP_TOP - MAP_BOTTOM) * 1.25)  # SCREEN_W - MARGIN

LAYER_NAMES = ['Map_Nexrad', 'Map_IR', 'Map_Topo', 'Map_Terrain',
               'Map_Water', 'Map_EGPWS', 'Map_raw_elev', 'Map_safe_taxi']

# The fifteen XPLMMapCustomData_t fields, in struct order (which is the order
# mapDisplayDrawIn() expects the sequence in), with their units.
OVERRIDE_FIELDS = [('datLat', 'deg'),
                   ('datLon', 'deg'),
                   ('ctrX', 'px'),
                   ('ctrY', 'px'),
                   ('roseRadius', 'px'),
                   ('mapRange', 'nm'),
                   ('orientation', '0N/1T/2H/3C'),
                   ('terrainWarn', 'ft'),
                   ('terrainCaution', 'ft'),
                   ('acfAlt', 'ft'),
                   ('gearDown', 'bool'),
                   ('trueRotation', 'deg'),
                   ('nearestRwyElev', 'ft'),
                   ('egpwsBrightness', '0-1'),
                   ('egpwsStyle', 'enum')]
NONE_INDEX = len(OVERRIDE_FIELDS)     # the sixteenth selection

# Fields backed by a dataref: (path, accessor).  Such a field tracks the sim
# live while it is NOT the selected override.
DATAREF_PATHS = {0: ('sim/flightmodel/position/latitude', 'd'),
                 1: ('sim/flightmodel/position/longitude', 'd'),
                 9: ('sim/flightmodel/misc/h_ind', 'f'),
                 10: ('sim/cockpit2/controls/gear_handle_down', 'i')}

# Dataref-backed fields that do NOT track live and are not re-seeded when
# selected: they take the dataref value only on an explicit reset ('z', and
# once at enable), so the map datum stays put while you pan it with +/-.
RESET_ONLY_FIELDS = {0, 1}       # datLat, datLon

# Fields derived from the map rectangle, computed at reset time.
GEOMETRY_DEFAULTS = {
    2: lambda: (MAP_LEFT + MAP_RIGHT) / 2.0,                       # ctrX
    3: lambda: (MAP_BOTTOM + MAP_TOP) / 2.0,                       # ctrY
    4: lambda: min(MAP_RIGHT - MAP_LEFT, MAP_TOP - MAP_BOTTOM) / 4.0,
}

# Everything else.
STATIC_DEFAULTS = {5: 12.5,      # mapRange, nm to the rose (EFIS range knob)
                   6: 2.0,       # orientation: north up
                   7: 2000.0,    # terrainWarn (red) ft
                   8: 1000.0,    # terrainCaution (yellow) ft
                   12: 0.0,      # nearestRwyElev ft
                   13: 1.0,      # egpwsBrightness
                   14: 0.0}      # egpwsStyle: Blocky

STEPS = {0: 0.1, 1: 0.1,         # lat/lon
         2: 10.0, 3: 10.0, 4: 10.0,   # geometry, pixels
         5: 1.0,                 # mapRange, nm
         7: 100.0, 8: 100.0, 9: 100.0, 12: 100.0,   # altitudes, ft
         11: 5.0,                # trueRotation
         13: 0.1}                # brightness
DEFAULT_STEP = 1.0

# Lat/lon and brightness want more precision than the default.
FORMATS = {0: '12.4f', 1: '12.4f', 13: '12.2f'}
DEFAULT_FORMAT = '12.1f'


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics map layer explorer"
        self.Sig = "xppython3.pgmaplayers"
        self.Desc = "Interactive map layers / dataOverrides explorer (XPLM440)"
        self.available = False
        self.dev = None
        self.map = None
        self.font = None
        self.sniffer = None
        self.layerIndex = 3                      # start on Map_Terrain: visible
        self.overrideIndex = NONE_INDEX          # start on "None"
        self.values = [0.0] * len(OVERRIDE_FIELDS)
        self.refs = {}                           # field index -> (dataref, kind)
        self.layers = []                         # int values, filled at enable
        # Readouts. terrainAlts lags one frame -- see screenDraw().
        self.scale = 0.0
        self.northHeading = 0.0
        self.terrainAlts = None

    def log(self, msg=''):
        print(f"[PGMapLayers]: {msg}", flush=True)

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
        self.layers = [getattr(xp, name) for name in LAYER_NAMES]
        for i, (path, kind) in DATAREF_PATHS.items():
            ref = xp.findDataRef(path)
            if ref is None:
                self.log(f"dataref not found: {path} (field {OVERRIDE_FIELDS[i][0]} stays 0)")
            else:
                self.refs[i] = (ref, kind)
        self.resetValues()
        self.createFont()
        self.buildDevice()
        self.sniffer = xp.registerKeySniffer(self.keySniffer, before=1)
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def XPluginStop(self):
        if self.sniffer is not None:
            xp.unregisterKeySniffer(self.keySniffer, before=1)
            self.sniffer = None
        if self.map is not None:
            xp.destroyMapDisplay(self.map)
            self.map = None
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

    def buildDevice(self):
        try:
            self.map = xp.createMapDisplay()
        except Exception as e:  # noqa: BLE001
            self.log(f"createMapDisplay failed: {e!r}")
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
                deviceID="xppython3.pgmaplayers.device",
                deviceName="Map layers",
                refCon=None,
                # Required: panel-graphics calls (incl. mapDisplayDrawIn) are a
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
        self.log("device built; SPACE=layer, TAB/Shift-TAB=override, +/- adjust, z=reset")

    # ---- override values -----------------------------------------------------

    def readRef(self, i):
        ref, kind = self.refs[i]
        if kind == 'd':
            return xp.getDatad(ref)
        if kind == 'i':
            return float(xp.getDatai(ref))
        return xp.getDataf(ref)

    def defaultValue(self, i):
        """Dataref value, else rectangle-derived value, else the constant."""
        if i in self.refs:
            return self.readRef(i)
        if i in GEOMETRY_DEFAULTS:
            return GEOMETRY_DEFAULTS[i]()
        return STATIC_DEFAULTS.get(i, 0.0)

    def resetValues(self):
        self.values = [self.defaultValue(i) for i in range(len(OVERRIDE_FIELDS))]

    def trackDatarefs(self):
        """Dataref-backed fields follow the sim, except the selected one and the
        reset-only fields (datLat/datLon -- a map datum that slid with the
        aircraft every frame would make panning it impossible)."""
        for i in self.refs:
            if i != self.overrideIndex and i not in RESET_ONLY_FIELDS:
                self.values[i] = self.readRef(i)

    # ---- keyboard ------------------------------------------------------------

    def visible(self):
        return self.dev is not None and xp.isAvionicsPopupVisible(self.dev)

    def keySniffer(self, key, flags, vKey, _refCon):
        if not (flags & xp.DownFlag) or not self.visible():
            return 1
        if vKey == xp.VK_SPACE:
            self.layerIndex = (self.layerIndex + 1) % len(self.layers)
            self.terrainAlts = None        # stale as soon as the layer changes
        elif vKey == xp.VK_TAB:
            # Shift-Tab walks the selection backwards.
            direction = -1 if (flags & xp.ShiftFlag) else 1
            self.overrideIndex = (self.overrideIndex + direction) % (NONE_INDEX + 1)
            # A newly selected field starts from its default, except the
            # reset-only ones. Cycling onto "None" leaves the values alone --
            # 'z' is the explicit reset.
            if self.overrideIndex != NONE_INDEX and self.overrideIndex not in RESET_ONLY_FIELDS:
                self.values[self.overrideIndex] = self.defaultValue(self.overrideIndex)
        elif key in (ord('z'), ord('Z')):
            self.resetValues()
        elif key in (ord('+'), ord('=')) or vKey == xp.VK_ADD:
            self.bump(1)
        elif key in (ord('-'), ord('_')) or vKey == xp.VK_SUBTRACT:
            self.bump(-1)
        else:
            return 1
        return 0        # consume keys we acted on

    def bump(self, sign):
        if self.overrideIndex == NONE_INDEX:
            return
        self.values[self.overrideIndex] += sign * STEPS.get(self.overrideIndex, DEFAULT_STEP)

    # ---- drawing -------------------------------------------------------------

    def bezelDraw(self, _r, _g, _b, _refcon):
        dark = xp.makeColor(.06, 0.06, 0.08, 1)
        xp.polygon(dark, [(0, 0), (SCREEN_W + 2 * BEZEL_PAD, 0),
                          (SCREEN_W + 2 * BEZEL_PAD, SCREEN_H + 2 * BEZEL_PAD),
                          (0, SCREEN_H + 2 * BEZEL_PAD)])

    def overrides(self):
        """The 15-value sequence, or None while "None" is selected."""
        return None if self.overrideIndex == NONE_INDEX else list(self.values)

    def screenDraw(self, _refcon):
        if not self.available or self.map is None:
            return

        self.trackDatarefs()

        white = xp.makeColor(1, 1, 1, 1)
        dim = xp.makeColor(0.55, 0.6, 0.65, 1)
        hot = xp.makeColor(1.0, 0.85, 0.2, 1)

        layerName = LAYER_NAMES[self.layerIndex]
        layerValue = self.layers[self.layerIndex]
        overrideName = ('None' if self.overrideIndex == NONE_INDEX
                        else OVERRIDE_FIELDS[self.overrideIndex][0])
        overrides = self.overrides()
        rect = (MAP_LEFT, MAP_TOP, MAP_RIGHT, MAP_BOTTOM)
        sampleX = (MAP_LEFT + MAP_RIGHT) / 2.0
        sampleY = (MAP_BOTTOM + MAP_TOP) / 2.0

        # Query the scale/north-up at the map center with EXACTLY the arguments
        # the map is drawn with -- that is the contract these two calls document.
        # Neither needs a drawing callback, but doing it here keeps them in step.
        try:
            self.scale = xp.mapDisplayScaleMeter(self.map, layerValue, *rect,
                                                 sampleX, sampleY, overrides)
            self.northHeading = xp.mapDisplayGetNorthHeading(self.map, layerValue, *rect,
                                                             sampleX, sampleY, overrides)
        except Exception as e:  # noqa: BLE001
            self.log(f"scale/north query: {e!r}")
            self.scale = self.northHeading = 0.0

        # Text and the frame go down FIRST: the map installs its own projection
        # and is not documented to restore it, so anything drawn afterwards may
        # land in the wrong space.
        xp.lineLoop(dim, [(MAP_LEFT, MAP_BOTTOM), (MAP_RIGHT, MAP_BOTTOM),
                          (MAP_RIGHT, MAP_TOP), (MAP_LEFT, MAP_TOP)])

        y = TEXT_TOP
        xp.fontDrawString(self.font, white, LABEL_SIZE, MAP_LEFT, y,
                          f"LAYER    [{self.layerIndex + 1}/{len(self.layers)}]  "
                          f"{layerName} = {layerValue}   (SPACE to cycle)",
                          xp.JustLeft)
        y -= int(LINE_H)
        step = STEPS.get(self.overrideIndex, DEFAULT_STEP)
        xp.fontDrawString(self.font, white, LABEL_SIZE, MAP_LEFT, y,
                          f"OVERRIDE [{self.overrideIndex + 1}/{NONE_INDEX + 1}]  "
                          f"{overrideName}   (TAB/Shift-TAB to cycle, "
                          f"+/- to adjust by {step:g}, z to reset all)",
                          xp.JustLeft)
        y -= int(LINE_H)
        xp.fontDrawString(self.font, dim, LABEL_SIZE, MAP_LEFT, y,
                          ("dataOverrides = None (live sim state)"
                           if overrides is None
                           else "dataOverrides = the fifteen values below"),
                          xp.JustLeft)
        y -= int(LINE_H * 1.4)

        for i, (name, units) in enumerate(OVERRIDE_FIELDS):
            selected = i == self.overrideIndex
            marker = '>' if selected else ' '
            color = hot if selected else dim
            if i in RESET_ONLY_FIELDS:
                source = f"z-only <- {DATAREF_PATHS[i][0]}"
            elif i in self.refs:
                source = (f"held (seeded from {DATAREF_PATHS[i][0]})" if selected
                          else f"live <- {DATAREF_PATHS[i][0]}")
            elif i in GEOMETRY_DEFAULTS:
                source = "from map rect"
            else:
                source = ''
            value = format(self.values[i], FORMATS.get(i, DEFAULT_FORMAT))
            xp.fontDrawString(self.font, color, LABEL_SIZE, MAP_LEFT, y,
                              f"{marker} {name:<16}{value} {units:<12} {source}",
                              xp.JustLeft)
            y -= int(LINE_H)

        y -= int(LINE_H * 0.4)
        mPerPx = (1.0 / self.scale) if self.scale else 0.0
        xp.fontDrawString(self.font, white, LABEL_SIZE, MAP_LEFT, y,
                          f"mapDisplayScaleMeter(center) = {self.scale:.6f} px/m"
                          f"   ({mPerPx:.1f} m/px)"
                          f"{'   [0 = tiles not loaded]' if not self.scale else ''}",
                          xp.JustLeft)
        y -= int(LINE_H)
        xp.fontDrawString(self.font, white, LABEL_SIZE, MAP_LEFT, y,
                          f"mapDisplayGetNorthHeading(center) = {self.northHeading:.2f} deg "
                          "(add to a true heading to get its screen angle)",
                          xp.JustLeft)
        y -= int(LINE_H)
        if self.terrainAlts is None:
            terrain = ("mapDisplayGetTerrainAltitudes = None "
                       "(needs a draw with Map_EGPWS)")
        else:
            terrain = (f"mapDisplayGetTerrainAltitudes = min {self.terrainAlts[0]:.0f} ft, "
                       f"max {self.terrainAlts[1]:.0f} ft")
        xp.fontDrawString(self.font, dim, LABEL_SIZE, MAP_LEFT, y, terrain, xp.JustLeft)

        # The map itself, with only the currently-selected layer enabled.
        try:
            xp.mapDisplayDrawIn(self.map, layerValue, *rect, overrides)
        except Exception as e:  # noqa: BLE001
            self.log(f"mapDisplayDrawIn: {e!r}")
            self.map = None
            return

        # Terrain altitudes describe the EGPWS terrain that was just drawn, so
        # this has to come AFTER the draw -- which means the text above shows
        # the previous frame's answer. Fine at 30+ fps.
        if layerValue == xp.Map_EGPWS:
            try:
                self.terrainAlts = xp.mapDisplayGetTerrainAltitudes(self.map)
            except Exception as e:  # noqa: BLE001
                self.log(f"mapDisplayGetTerrainAltitudes: {e!r}")
                self.terrainAlts = None
        else:
            self.terrainAlts = None
