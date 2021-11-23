# https://developer.x-plane.com/code-sample/texturedraw/

from OpenGL import GL
import xp

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


def my_draw_tex(_inPhase, _inIsBefore, _inRefcon):
    # A really dumb bitmap generator - just fill R and G with x and Y based color watch, and the B and alpha channels
    # based on mouse position.
    global buffer
    mx, my = xp.getMouseLocationGlobal()
    mx = max(0, mx)
    my = max(0, my)
    mx = min(sx, mx)
    my = min(sy, my)
    if False:  # simple port... slow
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
        global initialized
        i = 0
        mmx = int(mx * ssx)
        mmy = int(my * ssy)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if not initialized:
                    buffer[i] = int(x * 255 / WIDTH)
                    buffer[i + 1] = int(y * 255 / HEIGHT)

                buffer[i + 2] = mmx
                buffer[i + 3] = mmy
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
                       buffer)

    # The drawing part.
    xp.setGraphicsState(
        0,        # No fog, equivalent to glDisable(GL_FOG);
        1,        #  One texture, equivalent to glEnable(GL_TEXTURE_2D);
        0,        #  No lighting, equivalent to glDisable(GL_LIGHT0);
        0,        #  No alpha testing, e.g glDisable(GL_ALPHA_TEST);
        1,        #  Use alpha blending, e.g. glEnable(GL_BLEND);
        0,        #  No depth read, e.g. glDisable(GL_DEPTH_TEST);
        0)        #  No depth write, e.g. glDepthMask(GL_FALSE);

    GL.glColor3f(1, 1, 1)        # Set color to white.
    x1 = 420
    y1 = 20
    x2 = x1 + WIDTH
    y2 = y1 + HEIGHT
    GL.glBegin(GL.GL_QUADS);
    GL.glTexCoord2f(0, 0); GL.glVertex2f(x1, y1)  # We draw one textured quad.  Note: the first numbers 0,1 are texture coordinates, which are ratios.
    GL.glTexCoord2f(0, 1); GL.glVertex2f(x1, y2)  # lower left is 0,0, upper right is 1,1.  So if we wanted to use the lower half of the texture, we
    GL.glTexCoord2f(1, 1); GL.glVertex2f(x2, y2)  # would use 0,0 to 0,0.5 to 1,0.5, to 1,0.  Note that for X-Plane front facing polygons are clockwise
    GL.glTexCoord2f(1, 0); GL.glVertex2f(x2, y1)  # unless you change it; if you change it, change it back!
    GL.glEnd()


class PythonInterface:
    def XPluginStart(self):
        # Initialization: allocate a textiure number.
        global g_tex_num, buffer
        g_tex_num = xp.generateTextureNumbers(1)[0]
        xp.bindTexture2d(g_tex_num, 0)
        # Init to black for now.
        buffer = bytearray(WIDTH * HEIGHT * 4)
        # The first time we must use glTexImage2D.
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,                   # mipmap level
            GL.GL_RGBA,          # internal format for the GL to use.  (We could ask for a floating point tex or 16-bit tex if we were crazy!)
            WIDTH,
            HEIGHT,
            0,                   # border size
            GL.GL_RGBA,          # format of color we are giving to GL
            GL.GL_UNSIGNED_BYTE, # encoding of our data
            buffer)

        # Note: we must set the filtering params to SOMETHING or OpenGL won't draw anything!
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

        xp.registerDrawCallback(my_draw_tex, xp.Phase_FirstCockpit, 0, None)
        return "Texture example", "xppython3.test.texture_example", "Shows how to use textures."

    def XPluginStop(self):
        xp.unregisterDrawCallback(my_draw_tex, xp.Phase_FirstCockpit, 0, None)
        xp.bindTexture2d(g_tex_num, 0)
        GL.glDeleteTextures(1, g_tex_num)

    def XPluginEnable(self):
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, *args):
        pass
