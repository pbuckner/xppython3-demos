"""
PI_ObjAvionics.py -- exercise XPLMSetObjectAvionics / XPLMClearObjectAvionics
(new in XPLM440 / X-Plane 12.4.4): gluing a cockpit device you created with
createAvionicsEx() onto a 3-D object you loaded with loadObject(), so the
device's screen is drawn on that object out in the world.

The binding is matched BY DEVICE ID, not by handle: the .obj must mark its
screen polygons with

    ATTR_cockpit_device <deviceID> <bus> <rheostat> <auto-adjust>

using the same <deviceID> string passed to createAvionicsEx(). For purposes
of this demo, this plugin WRITES ITS OWN *.obj file at enable
-- a single 4:3 quad (makeObj) plus the black albedo it needs (makeTexture) --
and loads that.

Used here as similar to FOGGLES -- allowing you to see cockpit instruments but
largely unable to view out the window. The created instance is pinned AHEAD meters
in front of the aircraft datum in CoordSpace_AircraftExterior, so it rides with you like a
view-limiting hood instead of sitting out in the world. The screen draws a
labelled panel-graphics test pattern with a rolling green bar, so a frozen or
unbound screen is obvious at a glance.

The same quad also carries ATTR_manip_command, so CLICKING it toggles the
device's 2-D pop-up (command xppython3/foggles/popup). Both attributes apply to a
single TRIS -- they compose, no second draw needed. Note bezelDraw runs ONLY
while that pop-up is visible: on the object X-Plane draws the screen alone, since
ATTR_cockpit_device marks screen polygons and there is nowhere for a bezel to go.
bezelWidth/Height and screenOffsetX/Y likewise shape only the pop-up.

In case of error, An unbound or unmatched screen renders BLACK -- that, plus
a "returned 0" line in the log, is the signature of a deviceID mismatch.

The device does NOT need aircraft power: the brightness callback returns 1.0
unconditionally. Without such a callback X-Plane's default ties the screen to the
bus, and busVoltsRatio is -1 for an object-bound device, so it would stay dark.

Results go to XPPython3Log.txt, prefixed [ObjAvionics].
"""
import os
from PIL import Image

from XPPython3 import xp
from XPPython3.utils import commands

# Must match ATTR_cockpit_device in the generated .obj. Max 64 chars, unique,
# and NO SPACES (the OBJ attribute is whitespace-delimited) -- XPLMDisplay.h.
DEVICE_ID = "xppython3.objavionics"

OBJ_NAME = "pgobj_screen.obj"
TEX_NAME = "pgobj_black.png"

SCREEN_W = 400            # device screen, in device-local pixels
SCREEN_H = 300
BEZEL_PAD = 20

QUAD_W = 1.0              # meters; 4:3 to match the screen's aspect
QUAD_H = 0.75

# NOTE: this works if you're in a small aircraft (e.g., C172)
# otherwise, 0.6 meters is _behind_ you in a large aircraft, you
# won't see the object.
AHEAD = 0.6     # meters ahead of the aircraft datum (foggles distance)

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 20.0


class PythonInterface:
    def __init__(self):
        self.Name = "Object avionics test"
        self.Sig = "xppython3.objavionics"
        self.Desc = "Foggles: a cockpit device bound to a 3-D object with setObjectAvionics"
        self._checks = 0
        self._errors = 0
        self.dev = None           # our device, bound to the object
        self.obj = None           # loaded XPLMObjectRef
        self.instance = None      # instance drawn in the world
        self.font = None
        self.bound = False        # setObjectAvionics succeeded
        self.frames = 0
        self.objPath = None
        self.cmd = None           # session-global, created in XPluginStart

    def log(self, msg=''):
        print(f"[ObjAvionics]: {msg}", flush=True)

    def error(self, msg=''):
        self._errors += 1
        print(f"[ObjAvionics]: ** ERROR ** {msg}", flush=True)

    def check(self, prompt, ok):
        self._checks += 1
        if not ok:
            self.error(prompt)

    # ---- lifecycle -----------------------------------------------------------

    def XPluginStart(self):
        versions = xp.getVersions()
        self.log(f"X-Plane {versions[0]}, XPLM {versions[1]}")
        xp.makeColor(1.0, 1.0, 1.0, 1.0)         # panel graphics, for the screen draw
        # Session-global: create ONCE, not per enable -- a second create_command on
        # the same name would register a duplicate handler. Nothing to undo at
        # stop; XPPython3 clears each module's handlers on unload.
        self.cmd = commands.create_command("xppython3/foggles/popup", "Popup Foggles", self.command)
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        self.createFont()
        self.makeTexture()
        self.makeObj()
        self.buildAndBind()
        return 1

    def XPluginDisable(self):
        """Tear down everything XPluginEnable built.

        Enable/Disable are the symmetric pair: X-Plane can disable and re-enable a
        plugin without stopping it, and doing that while holding these handles
        would orphan an instance (which keeps drawing), a font and a loaded
        object, and would create a SECOND device with the same deviceID -- which
        the SDK requires to be unique.
        """
        if self.instance is not None:
            xp.destroyInstance(self.instance)
            self.instance = None
        # clearObjectAvionics before destroyAvionics is not strictly required --
        # destroying the device clears its bindings -- but do it explicitly so the
        # call is exercised on a LIVE binding.
        if self.bound and self.obj is not None and self.dev is not None:
            try:
                xp.clearObjectAvionics(self.obj, self.dev)
                self._checks += 1
            except Exception as e:  # noqa: BLE001
                self.error(f'clearObjectAvionics(live binding): {e!r}')
            self.bound = False
        if self.dev is not None:
            xp.destroyAvionics(self.dev)
            self.dev = None
        if self.obj is not None:
            xp.unloadObject(self.obj)
            self.obj = None
        if self.font is not None:
            xp.destroyFont(self.font)
            self.font = None

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def XPluginStop(self):
        # Nothing to release here: XPluginDisable always runs first and owns the
        # teardown. Command handlers are cleared by XPPython3 itself on unload
        # (clearInstanceCommands in utilities.cpp).
        if self._errors == 0:
            self.log(f"module check OK ({self._checks} checks passed).")
        else:
            self.log(f"module check: {self._errors} error(s) of {self._checks} checks.")

    # ---- the .obj ------------------------------------------------------------

    def makeObj(self):
        """Write a single-quad OBJ8 whose one polygon IS the device screen.

        Written fresh every enable so edits to DEVICE_ID/QUAD_* take effect on a
        plugin reload. Geometry: a QUAD_W x QUAD_H quad in the XY plane, origin at
        its bottom-centre, front face toward +Z, wound counterclockwise as seen
        from +Z. ATTR_no_cull so it is visible from behind too.

        The TEXTURE matters more than it looks. The device screen is composited
        OVER the object's lit albedo, it does not replace it -- so an object with
        no TEXTURE shows a sunlit WHITE surface under the screen content: black
        reads as grey and saturated colours wash out. Real devices avoid this by
        making the screen area of their albedo black; Laminar's
        garmin430_screen.dds samples (0,1,0)/(2,2,2)/(8,8,8) there. So we write a
        tiny all-black PNG (see makeTexture) and reference it.
        """
        half = QUAD_W / 2.0
        obj = f"""A
800
OBJ

TEXTURE {TEX_NAME}
POINT_COUNTS 4 0 0 6
VT {-half:.4f} 0.0000 0.0000  0.0 0.0 1.0  0.0 0.0
VT {half:.4f} 0.0000 0.0000  0.0 0.0 1.0  1.0 0.0
VT {half:.4f} {QUAD_H:.4f} 0.0000  0.0 0.0 1.0  1.0 1.0
VT {-half:.4f} {QUAD_H:.4f} 0.0000  0.0 0.0 1.0  0.0 1.0
IDX 0
IDX 1
IDX 2
IDX 0
IDX 2
IDX 3
ATTR_no_cull
ATTR_cockpit_device {DEVICE_ID} 2 1 1
ATTR_manip_command button xppython3/foggles/popup Popup Foggles
TRIS 0 6
"""
        self.objPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), OBJ_NAME)
        try:
            with open(self.objPath, 'w', encoding='utf-8') as fp:
                fp.write(obj)
            self._checks += 1
        except OSError as e:
            self.error(f'writing {self.objPath}: {e!r}')
            self.objPath = None
            return
        self.log(f"wrote {OBJ_NAME} (ATTR_cockpit_device {DEVICE_ID})")

    def makeTexture(self):
        """Write the all-black albedo the .obj references.

        8x8 is plenty: it is uniform, so the UV mapping does not matter. Without
        it the screen content is composited over an unlit-white, sun-lit surface
        -- see makeObj().
        """
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEX_NAME)
        try:
            Image.new("RGB", (8, 8), (0, 0, 0)).save(path)
            self._checks += 1
        except Exception as e:  # noqa: BLE001
            self.error(f'writing {path}: {e!r}')
            return
        self.log(f"wrote {TEX_NAME} (black albedo under the screen)")

    def createFont(self):
        self.font = xp.createFont(xp.CharSetASCII)
        xp.fontAddFace(self.font, xp.getSystemPath() + FONT_TTF)

    def command(self, phase, _duration):
        """Toggle the device's 2-D pop-up. Bound to the quad by ATTR_manip_command.

        The command exists for the whole session, so it can fire while the plugin
        is disabled (no device) -- hence the guard.
        """
        if phase == 0 and self.dev is not None:
            xp.setAvionicsPopupVisible(self.dev, not xp.isAvionicsPopupVisible(self.dev))

    def buildAndBind(self):
        if self.objPath is None:
            return
        try:
            self.dev = xp.createAvionicsEx(
                screenWidth=SCREEN_W,
                screenHeight=SCREEN_H,
                bezelWidth=SCREEN_W + 2 * BEZEL_PAD,
                bezelHeight=SCREEN_H + 2 * BEZEL_PAD,
                screenOffsetX=BEZEL_PAD,
                screenOffsetY=BEZEL_PAD,
                drawOnDemand=0,                # draw every frame
                bezelDraw=self.bezelDraw,
                screenDraw=self.screenDraw,
                brightness=self.brightness,
                deviceID=DEVICE_ID,
                deviceName="Object avionics test",
                # REQUIRED for the panel-graphics calls in screenDraw; the default
                # OpenGL content type raises "Panel graphics violation".
                contentType=xp.WindowContentTypePanelGraphics,
            )
            self.check('createAvionicsEx returns device', self.dev is not None)
        except Exception as e:  # noqa: BLE001
            self.error(f'createAvionicsEx: {e!r}')
            return

        try:
            self.obj = xp.loadObject(self.objPath)
            self.check('loadObject (bind target) returns objectRef', self.obj is not None)
        except Exception as e:  # noqa: BLE001
            self.error(f'loadObject: {e!r}')
            return
        if self.obj is None:
            return

        res = xp.setObjectAvionics(self.obj, self.dev)
        self.check(f'setObjectAvionics with matching deviceID returns 1 (got {res})', res == 1)
        self.bound = bool(res)
        if not self.bound:
            self.error(f"binding failed: no screen in {OBJ_NAME} matches deviceID '{DEVICE_ID}'")
            return

        try:
            self.instance = xp.createInstance(self.obj)
            self.check('createInstance returns instance', self.instance is not None)
        except Exception as e:  # noqa: BLE001
            self.error(f'createInstance: {e!r}')
            return

        # Pin the instance AHEAD meters ahead of the aircraft, riding with it.
        # CoordSpace_AircraftExterior makes the position aircraft-relative, so it
        # only ever needs setting once -- hence the return 0, which unschedules this
        # callback after the first call.

        xp.instanceSetCoordinateSpace(self.instance, xp.CoordSpace_AircraftExterior)
        xp.instanceSetPosition(self.instance, (0, 0, -AHEAD, 0, 0, 0))

        self.log(f"bound and instanced; foggles pinned {AHEAD} m ahead of the aircraft datum")

    # ---- the device's screen draw -------------------------------------------

    def brightness(self, _rheoValue, _ambientBrightness, _busVoltsRatio, _refCon):
        """Full brightness, always.

        Without this callback X-Plane's default ties the screen to the aircraft
        bus -- and busVoltsRatio is -1 here, because an object-bound device is not
        bound to the aircraft. That is why the screen previously needed Master on
        or Standby Battery in ARM. XPLMSetObjectAvionics' docs say brightness on
        the object follows the device's own callback, independent of any
        electrical system, which is exactly this.

        Returning 1.0 rather than ambientBrightness keeps a test object
        unambiguous: it will not dim at night, which is unrealistic but removes a
        variable. Switch to ambientBrightness for realistic behavior.
        """
        return 1.0

    def bezelDraw(self, _r, _g, _b, _refCon):
        bezelWidth = SCREEN_W + 2 * BEZEL_PAD
        bezelHeight = SCREEN_H + 2 * BEZEL_PAD
        xp.polygon(xp.makeColor(0, 0, 0, 1), [(0, 0), (bezelWidth, 0), (bezelWidth, bezelHeight), (0, bezelHeight)])

    def screenDraw(self, _refcon):
        """Drawn into the device screen, which the object displays.

        Device-local pixels, BOTTOM-LEFT origin (panel-graphics convention). The
        moving bar makes a frozen or unbound screen obvious.
        """
        self.frames += 1
        white = xp.makeColor(1, 1, 1, 1)
        green = xp.makeColor(0.1, 0.9, 0.3, 1)
        dim = xp.makeColor(0.4, 0.45, 0.5, 1)

        xp.polygon(xp.makeColor(0, 0, 0, 1),
                   [(0, 0), (SCREEN_W, 0), (SCREEN_W, SCREEN_H), (0, SCREEN_H)])
        xp.lineLoop(dim, [(4, 4), (SCREEN_W - 4, 4), (SCREEN_W - 4, SCREEN_H - 4), (4, SCREEN_H - 4)])

        # Corner ticks: prove orientation (and catch a flipped UV mapping in the
        # .obj -- if the label reads upside down or mirrored, swap the VT u/v).
        xp.lines(green, [(8, SCREEN_H - 8), (48, SCREEN_H - 8), (8, SCREEN_H - 8), (8, SCREEN_H - 48)])

        progress_bar = (self.frames % 120) / 120.0
        xp.polygon(green, [(10, 150), (10 + progress_bar * (SCREEN_W - 20), 150),
                           (10 + progress_bar * (SCREEN_W - 20), 175), (10, 175)])

        if self.font is not None:
            xp.fontDrawString(self.font, white, LABEL_SIZE, 12, SCREEN_H - 40,
                              "FOGGLES: OBJ AVIONICS", xp.JustLeft)
            xp.fontDrawString(self.font, white, LABEL_SIZE * 0.7, 12, SCREEN_H - 64,
                              f"{DEVICE_ID}  f{self.frames}", xp.JustLeft)
