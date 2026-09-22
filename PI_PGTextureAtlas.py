"""PI_PGTextureAtlas.py -- exercise the XPLMPanelGraphics texture-atlas API
(new in XPLM440 / X-Plane 12.4.4).

  The atlas is built at enable: it is assembled from 7 procedurally
  generated RGBA byte buffers and one PNG from Resources/bitmaps),
  baked, and its getImageWidth/getImageHeight queries are asserted
  self-consistent. Every frame the draw callback then draws each image
  via drawAt, drawIn, drawStretched, drawScaled (rotating) and
  drawMesh, in a labeled grid so each entry point can be eyeballed.

  A texture atlas is one big image that holds many small images packed together,
  so the GPU treats them as a single texture. You then draw sub-rectangles of it
  instead of many separate textures.

  The problem it solves: GPUs draw fastest when they can blast through lots of
  geometry without stopping. But every time you switch which texture is bound,
  the GPU pipeline has to flush and rebind — a "state change." State changes
  are expensive relative to the actual drawing.

  The general TextureAtlas API is:
  1. createTextureAtlas() — make an empty atlas (CPU-side collection).
  2. textureAtlasAddImage / AddImageFile / ...Set — throw in your sub-images;
     each gets a zero-based index (its handle). The *Set variants slice a
     sprite sheet into a grid automatically.
  3. textureAtlasBake() — the packer arranges everything into one GPU texture
     and uploads it. After baking you can't add more — that's why it must happen
     once, in XPluginEnable or single flightloop callback, not per-frame.
  4. Draw by index every frame: drawAt, drawIn, drawStretched (9-slice), drawScaled,
     drawMesh — all cheap, all sharing that one bound texture.
  5. destroyTextureAtlas() — free it.

  So the "idea" is: pay the creating/packing/upload cost once at load time, then draw many
  images per frame with almost no per-image overhead. It's the standard technique
  behind 2D UI, sprite-based games, and — here — instrument panels that may composite lots
  of little graphical pieces every frame.

  A secondary benefit worth noting: it also cuts down on wasted memory and mip-map/padding
  overhead versus dozens of tiny individual textures.


  Our packed Texture Atlas consists of:
  ┌─────┬────────────┬────────┬─────────────────┬────────────────────────────────────────────────────┐
  │ #   │   Name     │  Size  │     Source      │    Contents                                        │
  ├─────┼────────────┼────────┼─────────────────┼────────────────────────────────────────────────────┤
  │ 0   │ img_red    │ 48×48  │ _rgba_solid     │ Flat opaque red — every pixel (220, 40, 40, 255).  │
  │     │            │        │                 │ The simplest possible image; used to eyeball       │
  │     │            │        │                 │ drawAt at native size and tinting.                 │
  ├─────┼────────────┼────────┼─────────────────┼────────────────────────────────────────────────────┤
  │     │            │        │                 │ A two-axis gradient: horizontally, a blue→green    │
  │     │            │        │                 │ ramp (R=0, G climbs 0→255 left-to-right, B =       │
  │ 1   │ img_grad   │ 96×64  │ _rgba_gradient  │ 255−G); vertically, an alpha fade                  │
  │     │            │        │                 │ (top row ≈ transparent, bottom row opaque).        │
  │     │            │        │                 │ Exercises color interpolation and per-pixel        │
  │     │            │        │                 │ transparency.                                      │
  ├─────┼────────────┼────────┼─────────────────┼────────────────────────────────────────────────────┤
  │     │            │        │                 │ A 6-pixel opaque yellow frame (255, 220, 0, 255)   │
  │     │            │        │                 │ around a semi-transparent dark-blue center (40,    │
  │ 2   │ img_border │ 64×64  │ _rgba_border    │ 40, 90, 120). Shaped specifically for the 9-slice  │
  │     │            │        │                 │ drawStretched test — the frame should stay crisp   │
  │     │            │        │                 │ while the middle stretches.                        │
  ├─────┼────────────┼────────┼─────────────────┼────────────────────────────────────────────────────┤
  │     │            │        │                 │ One 80×80 sprite sheet cut into a 2×2 grid by      │
  │     │            │ 40×40  │                 │ AddImageSet, yielding 4 images: red, green, blue,  │
  │ 3–6 │ sprite0..  │ each   │ _rgba_sheet_2x2 │ yellow quadrants, each with a thin black diagonal  │
  │     │ sprite0+3  │        │                 │ stripe for orientation. Row-major, so index        │
  │     │            │        │                 │  = sprite0 + y*2 + x.                              │
  ├─────┼────────────┼────────┼─────────────────┼────────────────────────────────────────────────────┤
  │ 7   │ img_png    │ file's │ AddImageFile    │ X-Plane's own Resources/bitmaps/interface.png,     │
  │     │            │ size   │                 │ loaded from disk. The only non-procedural entry —  │
  │     │            │        │                 │ proves the PNG loader path works. (Skipped         │
  │     │            │        │                 │ gracefully if the file's missing.)                 │
  └─────┴────────────┴────────┴─────────────────┴────────────────────────────────────────────────────┘

  A few things worth noting:

  - All four input methods are covered on purpose: raw RGBA bytes (indices 0–2), a grid-sliced sprite
    sheet (AddImageSet, 3–6), and a PNG file (AddImageFile, 7). That's the whole "adding images"
    surface of the API. AddImageFileSet (a PNG sliced into a grid on load) is also exercised.
  - The 80×80 sprite sheet becomes 4 images, not 1. After AddImageSet there's no single "sprite sheet"
    handle — the packer treats each 40×40 cell as an independent image with its own index and UV
    rectangle. That's why spriteN = 4 and the sprite cell in the grid draws all four.
  - You don't control where they land in the baked texture. At textureAtlasBake() the packer arranges
    all 8 into one GPU texture however it likes (probably sorted by size to minimize wasted space).
    You never see that layout at all — you only ever refer to images by index, and there is no way
    to ask where an image landed. If you need to texture your own geometry from an atlas image, use
    textureAtlasDrawMesh: its (s, t) coordinates are normalized within the image, so knowing the
    packed position is unnecessary.
  - The consistency checks lean on knowing these sizes: the demo asserts getImageWidth/Height return
    48×48 for red, 96×64 for the gradient, and 40×40 for each sprite — i.e. the atlas preserves each
    image's original dimensions regardless of how it was packed.

Atlas creation, image add, and bake are done in XPluginEnable (createTextureAtlas
must NOT be called from within a draw callback); only the draw* routines run in
the draw phase.

Results go to XPPython3Log.txt, prefixed [PGTextureAtlas].

"""
from XPPython3 import xp

FONT_TTF = "Resources/fonts/Roboto-Regular.ttf"
PNG_FILE = "Resources/bitmaps/interface.png"     # ships with X-Plane
LABEL_SIZE = 10.0

CELL = 150         # grid cell size, pixels (atlas images are larger than shapes)
PAD = 12           # inset within each cell
COLS = 3           # cells per row
TITLE_H = 24       # header strip inside the window


class PythonInterface(object):
    def __init__(self):
        self.Name = "PanelGraphics TextureAtlas test"
        self.Sig = "xppython3.pgtextureatlas"
        self.Desc = "Regression test of the XPLMPanelGraphics texture-atlas API"
        self._checks = 0
        self._errors = 0
        self.available = False
        self.built = False
        self.winID = None
        self.font = None
        self.atlas = None
        self.col = {}
        # image indices, filled in when the atlas is built
        self.img_red = None
        self.img_grad = None
        self.img_border = None     # for 9-slice DrawStretched
        self.img_png = None
        self.sprite0 = None        # first cell of a 2x2 set added via AddImageSet
        self.spriteN = 0
        self.fileset0 = None       # first cell of a grid sliced from a PNG by AddImageFileSet
        self.filesetN = 0

    # ---- tiny check/log helpers ---------------------------------------------

    def log(self, msg=''):
        print(f"[PGTextureAtlas]: {msg}", flush=True)

    def error(self, msg=''):
        self._errors += 1
        print(f"[PGTextureAtlas]: ** ERROR ** {msg}", flush=True)

    def check(self, prompt, ok):
        self._checks += 1
        if not ok:
            self.error(prompt)

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

        # Probe availability without touching GL. makeColor is pure and is the
        # only routine safe to call outside a draw phase.
        try:
            xp.makeColor(1.0, 1.0, 1.0, 1.0)
            self.available = True
        except RuntimeError as e:
            self.available = False
            self.log(f"XPLMPanelGraphics not available: {e}")

        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        self.buildColors()
        if self.available:
            self.createFont()
            self.buildAtlas()
        self.createWindow()
        return 1

    def XPluginStop(self):
        if self.winID is not None:
            xp.destroyWindow(self.winID)
            self.winID = None
        if self.atlas is not None:
            xp.destroyTextureAtlas(self.atlas)
            self.atlas = None
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
            'magenta': xp.makeColor(1, 0, 1, 1),
            'white': xp.makeColor(1, 1, 1, 1),
            'dim': xp.makeColor(0.5, 0.5, 0.5, 1),
            'black': xp.makeColor(0, 0, 0, 1),
        }

    # ---- procedural RGBA image generators (rows top-to-bottom) ---------------

    @staticmethod
    def _rgba_solid(w, h, r, g, b, a=255):
        return bytes((r, g, b, a)) * (w * h)

    @staticmethod
    def _rgba_gradient(w, h):
        """Horizontal blue->green ramp, vertical alpha fade."""
        out = bytearray(w * h * 4)
        i = 0
        for y in range(h):
            a = int(255 * (y + 1) / h)
            for x in range(w):
                g = int(255 * x / max(1, w - 1))
                out[i:i + 4] = bytes((0, g, 255 - g, a))
                i += 4
        return bytes(out)

    @staticmethod
    def _rgba_border(w, h, edge=6):
        """Opaque yellow frame around a semi-transparent center (for 9-slice)."""
        out = bytearray(w * h * 4)
        i = 0
        for y in range(h):
            for x in range(w):
                if x < edge or y < edge or x >= w - edge or y >= h - edge:
                    out[i:i + 4] = bytes((255, 220, 0, 255))
                else:
                    out[i:i + 4] = bytes((40, 40, 90, 120))
                i += 4
        return bytes(out)

    @staticmethod
    def _rgba_sheet_2x2(cell):
        """A 2x2 sprite sheet: four solid-color cells with a diagonal stripe."""
        w = h = cell * 2
        quads = [(230, 30, 30), (30, 200, 30), (40, 40, 220), (220, 200, 30)]
        out = bytearray(w * h * 4)
        i = 0
        for y in range(h):
            for x in range(w):
                q = (0 if y < cell else 2) + (0 if x < cell else 1)
                r, g, b = quads[q]
                # thin dark diagonal for orientation
                if (x + y) % cell < 2:
                    r, g, b = 0, 0, 0
                out[i:i + 4] = bytes((r, g, b, 255))
                i += 4
        return w, h, bytes(out)

    # ---- atlas construction (at enable; must NOT run in a draw callback) -----

    def buildAtlas(self):
        self.built = True
        try:
            self.atlas = xp.createTextureAtlas()
        except Exception as e:  # noqa: BLE001
            self.error(f'createTextureAtlas: {e!r}')
            self.atlas = None
            return
        self.check('createTextureAtlas returns handle', self.atlas is not None)

        # Single images from raw RGBA bytes.
        self.img_red = xp.textureAtlasAddImage(self.atlas, self._rgba_solid(48, 48, 220, 40, 40), 48, 48)
        self.img_grad = xp.textureAtlasAddImage(self.atlas, self._rgba_gradient(96, 64), 96, 64)
        self.img_border = xp.textureAtlasAddImage(self.atlas, self._rgba_border(64, 64), 64, 64)

        # A 2x2 image set -> 4 sprites, row-major from sprite0.
        sw, sh, sheet = self._rgba_sheet_2x2(40)  # (solid colors with black diagonal)
        self.sprite0 = xp.textureAtlasAddImageSet(self.atlas, sheet, sw, sh, 2, 2)
        self.spriteN = 4

        # An image loaded from a PNG file that ships with X-Plane.
        try:
            png = xp.getSystemPath() + PNG_FILE
            self.img_png = xp.textureAtlasAddImageFile(self.atlas, png)
            self.check('addImageFile returns index >= 0',
                       isinstance(self.img_png, int) and self.img_png >= 0)
        except Exception as e:  # noqa: BLE001
            self.img_png = None
            self.log(f"addImageFile skipped ({e!r})")

        # The same PNG, but sliced into a 2x2 grid on load (file + set path).
        try:
            png = xp.getSystemPath() + PNG_FILE
            self.fileset0 = xp.textureAtlasAddImageFileSet(self.atlas, png, 2, 2)
            self.filesetN = 4
            self.check('addImageFileSet returns index >= 0',
                       isinstance(self.fileset0, int) and self.fileset0 >= 0)
        except Exception as e:  # noqa: BLE001
            self.fileset0 = None
            self.filesetN = 0
            self.log(f"addImageFileSet skipped ({e!r})")

        # Distinct indices for distinct images.
        idxs = [self.img_red, self.img_grad, self.img_border, self.sprite0]
        self.check('distinct image indices assigned', len(set(idxs)) == len(idxs))
        self.check('sprite set is contiguous',
                   self.sprite0 is not None and self.sprite0 >= 0)

        # Bake before any draw call.
        xp.textureAtlasBake(self.atlas)

        # Post-bake queries must be self-consistent with what we submitted.
        self.checkVal('img_red width', xp.textureAtlasGetImageWidth(self.atlas, self.img_red), 48)
        self.checkVal('img_red height', xp.textureAtlasGetImageHeight(self.atlas, self.img_red), 48)
        self.checkVal('img_grad width', xp.textureAtlasGetImageWidth(self.atlas, self.img_grad), 96)
        self.checkVal('img_grad height', xp.textureAtlasGetImageHeight(self.atlas, self.img_grad), 64)

        for k in range(self.spriteN):
            self.checkVal(f'sprite {k} width',
                          xp.textureAtlasGetImageWidth(self.atlas, self.sprite0 + k), 40)
            self.checkVal(f'sprite {k} height',
                          xp.textureAtlasGetImageHeight(self.atlas, self.sprite0 + k), 40)

        self.log(f"atlas built: red={self.img_red} grad={self.img_grad} border={self.img_border} "
                 f"sprites={self.sprite0}..{self.sprite0 + self.spriteN - 1 if self.sprite0 is not None else None} "
                 f"png={self.img_png} fileset={self.fileset0}..{self.fileset0 + self.filesetN - 1 if self.fileset0 is not None else None}")

    # ---- window --------------------------------------------------------------

    def createFont(self):
        # A font with no faces draws nothing but is not an error, so on failure
        # we drop the handle and let the label calls be skipped.
        ttf = xp.getSystemPath() + FONT_TTF
        self.font = xp.createFont(xp.CharSetASCII)
        ok = xp.fontAddFace(self.font, ttf)
        self.checkVal('fontAddFace succeeds', ok, 1)
        if not ok:
            self.log(f"no face loaded from {ttf}; labels disabled")
            xp.destroyFont(self.font)
            self.font = None

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
        xp.setWindowTitle(self.winID, "TextureAtlas test"
                          if self.available else "TextureAtlas N/A (XPLM<440)")
        self.log(f"window {self.winID} ({width}x{height}, {len(self.cells())} cells)")

    def cells(self):
        """List of (label, drawfn(ox, oy, s)) -- one per grid cell."""
        return [
            ("drawAt (native)", self.c_drawAt),   # small red square 48x48 in 126x126 cell
            ("drawIn (fill)", self.c_drawIn),     # gradient 96x64 stretched to fill 126x126 cell
            ("drawStretched 9-slice", self.c_drawStretched),  # 6-pixel yellow frame in 64x64 image stretched to cell: frame remains 6-pixel wide
            ("drawScaled (rotating)", self.c_drawScaled),  # rotate center of image around center of cell, scaled half height.
            ("drawMesh (trapezoid)", self.c_drawMesh),  # gradient image drawn as trapezoid
            ("sprite set 2x2", self.c_sprites),   # four colored squares, with diagonal black line
            ("PNG file", self.c_png),             # PNG from bitmap
            ("PNG set 2x2", self.c_fileset),      # PNG but sliced 2x2 and reordered
            ("tint (green)", self.c_tint),        # tinted green gradient
            ("gradient alpha", self.c_gradient),  # blue/green gradient over solid red,
            ("texSource radar (fill)", self.c_textureSource),      # radar square (use 737, with engine on)
            ("texSource radar (mesh)", self.c_textureSourceMesh),  # radar (trapezoid) ""
        ]

    def drawWindow(self, inWindowID, _inRefcon):
        if not self.available or self.atlas is None:
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
                xp.fontDrawString(self.font, self.col['white'], LABEL_SIZE,
                                  ox + 2, oy + CELL - 12, label, xp.JustLeft)
        return

    # ---- per-cell draw functions (each draws within s x s at (ox, oy)) -------

    @property
    def no_tint(self):
        return self.col['white']    # multiply identity

    def noteMissing(self, ox, oy, s):
        """Mark a cell whose image could not be loaded. Falls back to an outline
        when there is no font -- fontAddFace can legitimately fail (returns 0 as
        of d4), and drawing text with a faceless font would draw nothing at all.
        """
        if self.font is not None:
            xp.fontDrawString(self.font, self.col['dim'], LABEL_SIZE, ox, oy + s / 2,
                              "(no PNG)", xp.JustLeft)
        else:
            xp.lineLoop(self.col['dim'],
                        [(ox, oy), (ox + s, oy), (ox + s, oy + s), (ox, oy + s)])

    def c_drawAt(self, ox, oy, s):
        # Native resolution (i.e., 48x48), top-left corner at (ox, oy + s) so it stays in cell 126x126.
        xp.textureAtlasDrawAt(self.atlas, self.img_red, self.no_tint, ox, oy + s)

    def c_drawIn(self, ox, oy, s):
        # Stretch the gradient to fill the whole cell rectangle.
        # Note gradient is 96x64, so you're stretching in different amounts vertically and
        # horizontally to fit the 126x126 space.
        xp.textureAtlasDrawIn(self.atlas, self.img_grad, self.no_tint,
                              ox, oy + s, ox + s, oy)   # left, top, right, bottom

    def c_drawStretched(self, ox, oy, s):
        # 9-slice: the yellow border stays crisp while the center stretches.
        # the 64x64 image is sliced into a 3x3 grid of images. Four corner
        # images are drawn as-is in native size. the four edge (non-corner)
        # images are stretched along one axis, but not the other, the central
        # image is stretched in both dimensions:
        #    ┌─┬─┬─┐          ┌─┬──────┬─┐
        #    ├─┼─┼─┤          ├─┼──────┼─┤
        #    ├─┼─┼─┤   ->     │ │      │ │
        #    └─┴─┴─┘          │ │      │ │
        #                     ├─┼──────┼─┤
        #                     └─┴──────┴─┘

        xp.textureAtlasDrawStretched(self.atlas, self.img_border, self.no_tint,
                                     ox, oy + s, ox + s, oy)

    def c_drawScaled(self, ox, oy, s):
        # Rotate about the image center; angle sweeps over time.
        # img_grad is 96x64 natively, we're scaling it. Negative
        # scaling stretches in opposite direction.

        angle = (xp.getElapsedTime() * 45.0) % 360.0
        cx, cy = ox + s / 2, oy + s / 2
        pivotx, pivoty = 48, 32  # 48., 32. #  = image center (96x64)
        xp.textureAtlasDrawScaled(self.atlas, self.img_grad, self.no_tint,
                                  cx, cy,          # panel pivot
                                  pivotx, pivoty,  # atlas pivot
                                  -1, .5,          # scale
                                  angle)           # clockwise degrees
        # add a dot at the pivot point: here we re-use the img_red solid image scaled small.
        xp.textureAtlasDrawIn(self.atlas, self.img_red, self.no_tint,
                              cx - 2, cy + 2, cx + 2, cy - 2)

    def c_drawMesh(self, ox, oy, s):
        # Map the full image (s,t in 0..1) onto a trapezoid triangle strip.
        verts = [
            (ox + s * 0.8, oy,     1.0, 0.0),
            (ox + s * 0.2, oy,     0.0, 0.0),
            (ox + s,       oy + s, 1.0, 1.0),
            (ox,           oy + s, 0.0, 1.0),
        ]
        xp.textureAtlasDrawMesh(self.atlas, self.img_grad, self.no_tint, verts)

    def c_sprites(self, ox, oy, s):
        # Draw the four cells of the 2x2 set in a small 2x2 layout.
        half = s / 2
        for k in range(self.spriteN):
            cx = ox + (k % 2) * half
            cy = oy + (1 - k // 2) * half        # top row first
            xp.textureAtlasDrawIn(self.atlas, self.sprite0 + k, self.no_tint,
                                  cx, cy + half, cx + half - 2, cy + 2)

    def c_png(self, ox, oy, s):
        if self.img_png is None:
            self.noteMissing(ox, oy, s)
            return
        xp.textureAtlasDrawIn(self.atlas, self.img_png, self.no_tint,
                              ox, oy + s, ox + s, oy)

    def c_fileset(self, ox, oy, s):
        # The four cells produced by AddImageFileSet slicing interface.png into a
        # 2x2 grid, drawn in a small 2x2 layout (mirrors the sprite-set cell, but
        # sourced from a file rather than raw bytes). Row-major from fileset0.
        if self.fileset0 is None:
            self.noteMissing(ox, oy, s)
            return
        half = s / 2
        for k in range(self.filesetN):
            cx = ox + (k % 2) * half
            cy = oy + (1 - k // 2) * half        # top row first
            xp.textureAtlasDrawIn(self.atlas, self.fileset0 + k, self.no_tint,
                                  cx, cy + half, cx + half - 2, cy + 2)

    def c_tint(self, ox, oy, s):
        # Tint is a per-channel multiply (modulate). The gradient is a blue->green
        # ramp (0, g, 255-g); multiplying by green (0,1,0) zeroes the blue channel
        # and leaves a black->green ramp -- clearly modulated vs. the untinted
        # gradient shown in the "gradient alpha" cell. (Tinting img_red here is a
        # poor demo: red has no green/blue content, so it can only stay red or go
        # black -- no visible tint.)
        xp.textureAtlasDrawIn(self.atlas, self.img_grad, self.col['green'],
                              ox, oy + s, ox + s, oy)

    def c_gradient(self, ox, oy, s):
        # Show the gradient's vertical alpha fade as actual transparency: draw an
        # opaque backing first (img_red, a solid opaque red), then the gradient
        # over it. The gradient is opaque at top and fades to ~transparent at
        # bottom, so the red shows through more toward the bottom -- unlike the
        # "drawIn (fill)" cell, which fades into the window background instead.
        # (No solid-white image exists in the atlas, and tint only darkens, so
        # red is used as the contrasting opaque backing.)
        xp.textureAtlasDrawIn(self.atlas, self.img_red, self.no_tint,
                              ox, oy + s, ox + s, oy)          # opaque red backing
        xp.textureAtlasDrawIn(self.atlas, self.img_grad, self.no_tint,
                              ox, oy + s, ox + s, oy)          # gradient over it

    def c_textureSource(self, ox, oy, s):
        # textureSource draws a LIVE simulator texture (here the pilot-side
        # weather radar), unlike the atlas which draws images you supplied. If
        # the current aircraft has no weather radar the SDK silently skips the
        # draw, so we first outline the cell -- an empty frame then means "no
        # radar hardware", not a wrapper failure. Coords are ints (not floats
        # like the atlas variants): left, top, right, bottom.
        xp.polygon(xp.makeColor(1, 1, 1, 1), [(ox, oy), (ox + s, oy), (ox + s, oy + s), (ox, oy + s)])
        xp.lineLoop(self.col['dim'], [(ox, oy), (ox + s, oy), (ox + s, oy + s), (ox, oy + s)])
        xp.textureSourceDrawIn(xp.Texture_WeatherRadar1, self.no_tint,
                               int(ox), int(oy + s), int(ox + s), int(oy))  # left, top, right, bottom

    def c_textureSourceMesh(self, ox, oy, s):
        # Same live radar texture mapped onto a trapezoid triangle strip, mirroring
        # the atlas drawMesh cell. Each vertex is (x, y, s, t); (s, t) is the
        # normalized coordinate within the source texture. Blank => no radar.
        xp.polygon(xp.makeColor(1, 1, 1, 1), [(ox, oy), (ox + s, oy), (ox + s, oy + s), (ox, oy + s)])
        xp.lineLoop(self.col['dim'], [(ox, oy), (ox + s, oy), (ox + s, oy + s), (ox, oy + s)])
        verts = [
            (ox + s * 0.8, oy,     1.0, 0.0),
            (ox + s * 0.2, oy,     0.0, 0.0),
            (ox + s,       oy + s, 1.0, 1.0),
            (ox,           oy + s, 0.0, 1.0),
        ]
        xp.textureSourceDrawMesh(xp.Texture_WeatherRadar1, self.no_tint, verts)
