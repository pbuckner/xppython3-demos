# https://developer.x-plane.com/code-sample/texturedraw/
from typing import Self, Any, Optional

from OpenGL import GL
from XPPython3 import xp
from XPPython3.xp_typing import XPLMDrawingPhase
try:
    from numpy import put, zeros, uint8
    use_numpy = True
except Exception:  # pylint: disable=broad-exception-caught
    use_numpy = False


# Our texture dimensions.  Textures MUST be powers of 2 in OpenGL - if you don't need that much space,
# just round up to the nearest power of 2.
WIDTH = 128
HEIGHT = 128

# This is our texture ID.  Texture IDs in OpenGL are just ints...but this is a global for the life of our plugin.
g_tex_num = 0

# We use this memory to prep the buffer.  Note that this memory DOES NOT have to be global - the memory is FULLY
# read by OpenGL before glTexSubImage2D or glTexImage2D return, so you could use local or temporary storage, or
# change the image AS SOON as the call returns!  4 bytes for R,G,B,A 32-bit pixels.
buffer = bytearray(WIDTH * HEIGHT * 4)

sx, sy = xp.getScreenSize()
initialized = False
ssx = 255 / sx
ssy = 255 / sy


def my_draw_tex(_inPhase: XPLMDrawingPhase, _inIsBefore: int, refCon: Any) -> None:
    # A really dumb bitmap generator - just fill R and G with x and Y based color watch, and the B and alpha channels
    # based on mouse position.
    global initialized  # pylint: disable=global-statement
    mx, my = xp.getMouseLocationGlobal()
    mx = max(0, mx)
    my = max(0, my)
    mx = min(sx, mx)
    my = min(sy, my)
    if not use_numpy:  # simple port... slow
        i = 0
        for y in range(HEIGHT):
            for x in range(WIDTH):
                buffer[i] = int(x * 255 / WIDTH)
                buffer[i + 1] = int(y * 255 / HEIGHT)
                buffer[i + 2] = int(mx * 255 / sx)
                buffer[i + 3] = int(my * 255 / sy)
                i += 4
    else:
        # a) Note that [i] and [i+1] depend only WIDTH and HEIGHT and
        #    do not change based on mouse position or screen width, so
        #    initilize once and be done with it.
        # b) Note that [i+2] and [i+3] depend in mouse position relative
        #    the screen width/height and therefore do not change during
        #    execution of this function, so calculate once and then
        #    assign it.
        i = 0
        mmx = int(mx * ssx)
        mmy = int(my * ssy)
        if initialized:
            put(refCon['buffer'], refCon['array'], [mmx, mmy])
        else:
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    refCon['buffer'][i] = int(x * 255 / WIDTH)
                    refCon['buffer'][i + 1] = int(y * 255 / HEIGHT)
                    refCon['buffer'][i + 2] = mmx
                    refCon['buffer'][i + 3] = mmy
                    i += 4
        initialized = True

    xp.bindTexture2d(g_tex_num, 0)
    # Note: if the tex size is not changing, glTexSubImage2D is faster than glTexImage2D.

    GL.glTexSubImage2D(GL.GL_TEXTURE_2D,
                       0,                       # mipmap level
                       0,                       # x-offset
                       0,                       # y-offset
                       WIDTH,
                       HEIGHT,
                       GL.GL_RGBA,                 # color of data we are seding
                       GL.GL_UNSIGNED_BYTE,        # encoding of data we are sending
                       refCon['buffer'].tobytes() if use_numpy else buffer)

    # The drawing part.
    xp.setGraphicsState(
        0,        # No fog, equivalent to glDisable(GL_FOG);
        1,        # One texture, equivalent to glEnable(GL_TEXTURE_2D);
        0,        # No lighting, equivalent to glDisable(GL_LIGHT0);
        0,        # No alpha testing, e.g glDisable(GL_ALPHA_TEST);
        1,        # Use alpha blending, e.g. glEnable(GL_BLEND);
        0,        # No depth read, e.g. glDisable(GL_DEPTH_TEST);
        0)        # No depth write, e.g. glDepthMask(GL_FALSE);

    GL.glColor3f(1, 1, 1)        # Set color to white.
    x1 = 420
    y1 = 20
    x2 = x1 + WIDTH
    y2 = y1 + HEIGHT
    GL.glBegin(GL.GL_QUADS)

    # We draw one textured quad.  Note: the first numbers 0,1 are texture coordinates, which are ratios.
    # lower left is 0,0, upper right is 1,1.  So if we wanted to use the lower half of the texture, we
    # would use 0,0 to 0,0.5 to 1,0.5, to 1,0.  Note that for X-Plane front facing polygons are clockwise
    # unless you change it; if you change it, change it back!
    GL.glTexCoord2f(0, 0)
    GL.glVertex2f(x1, y1)
    GL.glTexCoord2f(0, 1)
    GL.glVertex2f(x1, y2)
    GL.glTexCoord2f(1, 1)
    GL.glVertex2f(x2, y2)
    GL.glTexCoord2f(1, 0)
    GL.glVertex2f(x2, y1)
    GL.glEnd()


class PythonInterface:
    def __init__(self: Self) -> None:
        self.refCon: Optional[dict] = None

    def XPluginStart(self: Self) -> tuple[str, str, str]:
        # Initialization: allocate a textiure number.
        global g_tex_num, buffer  # pylint: disable=global-statement
        g_tex_num = xp.generateTextureNumbers(1)[0]
        xp.bindTexture2d(g_tex_num, 0)
        # Init to black for now.
        buffer = bytearray(WIDTH * HEIGHT * 4)
        # The first time we must use glTexImage2D.
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,                    # mipmap level
            GL.GL_RGBA,           # internal format for the GL to use.  (We could ask for a floating point tex or 16-bit tex if we were crazy!)
            WIDTH,
            HEIGHT,
            0,                    # border size
            GL.GL_RGBA,           # format of color we are giving to GL
            GL.GL_UNSIGNED_BYTE,  # encoding of our data
            buffer)

        # Note: we must set the filtering params to SOMETHING or OpenGL won't draw anything!
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

        if use_numpy:
            # create and pass a numpy buffer, rather than use global.
            # and, create array of indices, which we'll use each draw cycle for updates
            self.refCon = {'buffer': zeros(WIDTH * HEIGHT * 4, uint8),
                           'array': sorted(list(range(2, 4 * HEIGHT * WIDTH, 4)) + list(range(3, 4 * HEIGHT * WIDTH, 4)))}
        else:
            self.refCon = None
        # Note a change from original example:
        #  Phase_Window:
        #     Using this phase will result in a square floating "window" to be drawn, visible for any aircraft.
        #  Phase_FirstCockpit:
        #     Using this phase will result in a square floating "window" to be drawn, visible for any aircraft.
        #     **IF** X-Plane is running in OpenGL mode. If Vulkan/Metal, this will not be draw.
        #  Phase_Gauges:
        #     This phase will result in drawing on the underlying gauge "screens" of the aircraft.
        #     Cessna 172 has no applicable gauge textures, so NOTHING WILL BE DRAWN!
        #     737-800 _does_ have gauge texture, so the drawing will be displayed across
        #     all of the screens & move in 3d. It is VERY SLOW, you have been warned.
        xp.registerDrawCallback(my_draw_tex, xp.Phase_Window, 0, refCon=self.refCon)
        return "Texture example v1.0", "xppython3.test.texture_example", "Shows how to use textures."

    def XPluginStop(self: Self) -> None:
        xp.unregisterDrawCallback(my_draw_tex, xp.Phase_Window, 0, refCon=self.refCon)
        xp.bindTexture2d(g_tex_num, 0)
        GL.glDeleteTextures(1, [g_tex_num])

    def XPluginEnable(self: Self) -> int:
        return 1
