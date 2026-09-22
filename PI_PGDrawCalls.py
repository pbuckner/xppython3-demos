"""
PI_PGDrawCalls.py -- exercise the XPLMPanelGraphics ImGui-style mesh drawing API
(new in XPLM440 / X-Plane 12.4.4): createTexture / destroyTexture / drawCalls.

Requires PIL python module.

  createTexture must not be called in a live GL context, so the texture is built
  during Enable, and mesh is  built lazily on the first frame (not at enable).
  Every frame the draw callback then issues drawCalls to render, in a labeled grid:
   - a texture is created using PIL python module
   - an untextured, per-vertex-colored triangle (tex=None);
   - the same texture clipped by a tight scissor rect.

  The ImGui vertex layout is exactly ImDrawVert: 20 bytes = pos.x, pos.y, uv.x,
  uv.y (float32) then RGBA8 packed as a little-endian uint32 (R is the low byte),
  colors pre-multiplied alpha. Indices are uint16. drawCalls() accepts either
  those raw buffers or, per argument, a Python sequence it packs for us:
  vertices as (x, y, u, v[, color]) tuples -- color defaulting to opaque white --
  and indices as plain ints. Both paths are exercised below: c_quad and c_tri
  pass sequences, c_scissor passes bytes. Each draw call is
  (tex|None, (left, top, right, bottom), idx_offset, element_count, vtx_offset)
  with window-LOCAL, TOP-LEFT-origin coordinates (the host flips Y).

Results go to XPPython3Log.txt, prefixed [PGDrawCalls].
"""
import struct
from XPPython3 import xp
from PIL import Image, ImageDraw

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
LABEL_SIZE = 10.0

CELL = 150
PAD = 12
COLS = 3
TITLE_H = 24

# one 20-byte ImDrawVert: pos.x, pos.y, uv.x, uv.y (f32) + packed RGBA8 (u32 LE)
VERT = struct.Struct("<ffffI")


def rgba(r, g, b, a=255):
    """Pack straight RGBA8 into the little-endian uint32 ImGui expects (R low)."""
    return (r & 0xFF) | ((g & 0xFF) << 8) | ((b & 0xFF) << 16) | ((a & 0xFF) << 24)


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics DrawCalls test"
        self.Sig = "xppython3.pgdrawcalls"
        self.Desc = "Regression test of the XPLMPanelGraphics ImGui mesh-drawing API"
        self._checks = 0
        self._errors = 0
        self.available = False
        self.built = False
        self.winID = None
        self.font = None
        self.tex = None
        self.col = {}

    # ---- tiny check/log helpers ---------------------------------------------

    def log(self, msg=''):
        print(f"[PGDrawCalls]: {msg}", flush=True)

    def error(self, msg=''):
        self._errors += 1
        print(f"[PGDrawCalls]: ** ERROR ** {msg}", flush=True)

    def check(self, prompt, ok):
        self._checks += 1
        if not ok:
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
        # Everything that must NOT run inside a draw callback happens here:
        # createTexture() needs to be outside a live GL context, so both the
        # texture battery and the real textures are built now. The drawCalls
        # battery is the mirror case -- it must run INSIDE a draw callback --
        # and so is deferred to the first frame.
        self.buildColors()
        if self.available:
            self.createFont()
        self.buildTexture()
        self.createWindow()
        return 1

    def XPluginStop(self):
        if self.winID is not None:
            xp.destroyWindow(self.winID)
            self.winID = None
        if self.tex is not None:
            xp.destroyTexture(self.tex)
            self.tex = None
        if self.font is not None:
            xp.destroyFont(self.font)
            self.font = None
        if self._errors == 0:
            self.log(f"module check OK ({self._checks} checks passed).")
        else:
            self.log(f"module check: {self._errors} error(s) of {self._checks} checks.")

    def buildColors(self):
        self.col = {
            'white': xp.makeColor(1, 1, 1, 1),
            'dim': xp.makeColor(0.5, 0.5, 0.5, 1),
            'red': xp.makeColor(1, 0, 0, 1),
        }

    # ---- procedural texture --------------------------------------------------

    @staticmethod
    def _checkerboard(w, h, cell=8):
        """RGBA8 checkerboard: opaque magenta / cyan squares."""
        out = bytearray(w * h * 4)
        i = 0
        for y in range(h):
            for x in range(w):
                if ((x // cell) + (y // cell)) & 1:
                    out[i:i + 4] = bytes((230, 40, 200, 255))   # magenta
                else:
                    out[i:i + 4] = bytes((40, 200, 220, 255))   # cyan
                i += 4
        return bytes(out)

    # ---- window --------------------------------------------------------------

    def createFont(self):
        ttf = xp.getSystemPath() + FONT_TTF
        self.font = xp.createFont(xp.CharSetASCII)
        xp.fontAddFace(self.font, ttf)

    def createWindow(self):
        rows = (len(self.cells()) + COLS - 1) // COLS
        width = COLS * CELL + 2 * PAD
        height = rows * CELL + TITLE_H + 2 * PAD
        (l, t, _r, _b) = xp.getScreenBoundsGlobal()
        left = l + 140
        top = t - 140
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
            None,
            None
        ]
        self.winID = xp.createWindowEx(params)
        xp.setWindowPositioningMode(self.winID, xp.WindowCenterOnMonitor, -1)
        xp.setWindowTitle(self.winID, "DrawCalls test"
                          if self.available else "DrawCalls N/A (XPLM<440)")
        self.log(f"window {self.winID} ({width}x{height}, {len(self.cells())} cells)")

    # ---- lazy build (must not be within needs GL context, so during enable) ------------

    def buildTexture(self):
        """Call ONLY from Enable -- createTexture() must not run inside a live
        GL context, i.e. never from the draw callback."""
        self.built = True
        if not self.available:
            self.tex = None
            return
        try:
            # draw magenta 180 degree arc, white horizontal, red vertical chords
            # PIL draws (0, 0) is upper left!!!!
            img = Image.new("RGBA", (300, 300))
            draw = ImageDraw.Draw(img)
            draw.arc([(0, 0), (300, 300)], 180, 0, fill="magenta", width=20)
            draw.line([(150, 0), (150, 300)], fill="red", width=5)
            draw.line([(0, 150), (300, 150)], fill="white", width=10)
            draw.circle([0, 0], radius=10, fill="yellow", width=2)
            draw.circle([300, 300], radius=10, fill="blue", width=2)
            self.tex = xp.createTexture(img.tobytes(), *img.size)
            self.check('createTexture returns handle', self.tex is not None)
        except Exception as e:  # noqa: BLE001
            self.tex = None
            self.error(f'createTexture: {e!r}')

    # ---- Part B: visual battery ----------------------------------------------

    def cells(self):
        return [
            ("textured quad", self.c_quad),
            ("colored tri (no tex)", self.c_tri),
            ("textured + scissor", self.c_scissor),
        ]

    def drawWindow(self, inWindowID, _inRefcon):
        if not self.available:
            return
        if not self.built:
            # buildTexture() calls createTexture(), which must not run here.
            self.error('drawWindow: texture was not built during Enable')
            return
        (l, t, _r, _b) = xp.getWindowGeometry(inWindowID)
        cells = self.cells()
        grid_top = t - TITLE_H
        for i, (label, fn) in enumerate(cells):
            col = i % COLS
            row = i // COLS
            ox = l + PAD + col * CELL
            oy = grid_top - (row + 1) * CELL
            s = CELL - 2 * PAD
            # window-local, top-left origin (ImGui convention)
            lx = ox - l
            ty = t - (oy + s)     # top edge, local
            try:
                fn(lx, ty, s)
            except Exception as e:  # noqa: BLE001
                self.error(f'draw {label}: {e!r}')
                raise
            if self.font is not None:
                xp.fontDrawString(self.font, self.col['white'], LABEL_SIZE,
                                  ox + 2, oy + CELL - 12, label, xp.JustLeft)
        return

    def _quad_verts(self, lx, ty, s, color=None):
        """Two-triangle quad at window-local (lx, ty)=top-left, size s, full UV.

        With color=None the vertices are 4-tuples and drawCalls() supplies opaque
        white (no tint); otherwise 5-tuples carrying the packed color.
        """
        rx, by = lx + s, ty + s
        quad = [
            (lx, ty, 0.0, 0.0),   # 0 TL
            (rx, ty, 1.0, 0.0),   # 1 TR
            (rx, by, 1.0, 1.0),   # 2 BR
            (lx, by, 0.0, 1.0),   # 3 BL
        ]
        if color is None:
            return quad
        return [v + (color,) for v in quad]

    def _pack(self, verts, indices):
        """Pack to the raw ImDrawVert/uint16 buffers drawCalls() also accepts."""
        vbuf = b''.join(VERT.pack(*v) for v in verts)
        ibuf = struct.pack(f"<{len(indices)}H", *indices)
        return vbuf, ibuf

    def c_quad(self, lx, ty, s):
        # 4-tuple vertices: color omitted, so drawCalls() defaults to no tint.
        if self.tex is None:
            return
        verts = self._quad_verts(lx, ty, s)
        xp.drawCalls(verts, [0, 1, 2, 0, 2, 3],
                     [(self.tex, (lx, ty, lx + s, ty + s), 0, 6, 0)])

    def c_tri(self, lx, ty, s):
        # Untextured (tex=None): per-vertex color interpolation across a triangle.
        # 5-tuple vertices, passed as a sequence -- no struct packing needed.
        verts = [
            (lx + s / 2, ty,     0.0, 0.0, rgba(255, 40, 40)),    # red top
            (lx + s,     ty + s, 0.0, 0.0, rgba(40, 255, 40)),    # green BR
            (lx,         ty + s, 0.0, 0.0, rgba(40, 40, 255)),    # blue BL
        ]
        xp.drawCalls(verts, [0, 1, 2],
                     [(None, (lx, ty, lx + s, ty + s), 0, 3, 0)])

    def c_scissor(self, lx, ty, s):
        # Same textured quad but clipped to its top-left quarter by the scissor
        # rect. Drawn from pre-packed bytes, so this cell covers the buffer path
        # while the two above cover the sequence path.
        if self.tex is None:
            return
        verts = self._quad_verts(lx, ty, s, xp.makeColor(1, 1, 1, 1))
        vbuf, ibuf = self._pack(verts, [0, 1, 2, 0, 2, 3])

        clip = (lx, ty, lx + s / 2, ty + s / 2)   # only TL quarter should show
        xp.drawCalls(vbuf, ibuf, [(self.tex, clip, 0, 6, 0)])
