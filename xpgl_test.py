import pygame
import random
import sys
import os
import traceback
from enum import Enum
from OpenGL.GL import glClearColor, glClearDepth, glEnable, \
    GL_TEXTURE_2D, glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, \
    glLoadIdentity, glOrtho, GL_BLEND, GL_TRUE, glDepthMask, glFlush

# ==================================================================================
# SET SYSPATH to include XPPython3... If you're executing this from
# PythonPlugins, this will work to pull in XPPython3.
# Note we _also_ change current directory to "Root", so all file.open() relative
# paths will load same as within X-Plane.
#
XPlaneRootDir = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../..'))
os.chdir(XPlaneRootDir)
sys.path.insert(0, 'Resources/plugins')
sys.path.insert(0, 'Resources/plugins/XPPython3')
sys.path.insert(0, 'Resources/plugins/PythonPlugins')
# ==================================================================================

# pylint: disable=wrong-import-position
from XPPython3 import xpgl  # NOQA
from XPPython3.xpgl import Colors  # NOQA
from XPPython3.xpgl.mock_xp import xp  # NOQA
# pylint: enable=wrong-import-position

# ==================================================================================
# CUSTOMIZE below
#
#   For convenience, we set width, height of the window: change that to match
#   your target window
Width, Height = 500, 500
#
#   'Mode' refers to the type of callback you're testing. They differ slightly within
#    X-Plane with regard to how the init the OpenGL context for you.
#    ... specifically "AvionicsScreen" requires you to glClear() and glFlush()
Modes = Enum('Modes', ['AvionicsScreen',  # createAvionicsEx()
                       'AvionicsBezel',   # createAvionicsEx()
                       'Window',          # createWindowEx()
                       'AvionicsBefore',  # regsiterAvionicsCallbacksEx()
                       'AvionicsAfter',   # registerAvionicsCallbacksEx()
                       'DirectDraw',      # registerDrawCallback()
                       ])
Mode = Modes.Window

#
#   Also, we've defined a global "Data" dict. You can use that to store any
#   otherwise global data values. In your "real" program these might be
#   dataref values, XPluginInstance variables, etc.
Data = {}

#
#   Two functions for your to customize:
#   * load()
#     You should put one-time operations here -- load fonts, load images, etc.
#     These are things you might do during X-Plane initialization, perhaps
#     during XPluginEnable()
#
#   * draw()
#     Your draw routine -- this will be called over-and-over until you press 'q'
#     within the OpenGL window.
#
# To make your code more compatible with X-Plane:
# USE xp.setGraphicsState for the following, if you need to:
# xp.setGraphicsState(fog=0,             # ... ALWAYS SET TO ZERO for X-Plane
#                     numberTexUnits=0,  # 0 is none, 1 is one multitexturing unit,
#                                          2 is two multitexturing units...
#                     lighting=0,        # GL_LIGHTING, GL_LIGHT0 ... ALWAYS 0 for X-Plane
#                     alphaTesting=0,    # GL_ALPHA_TEST
#                     alphaBlending=0,   # GL_BLEND
#                     depthTesting=0,    # GL_DEPTH_TEST
#                     depthWriting=0)    # gl_DepthMask(TRUE)
# USE xp.bindtexture2d() instead of glBindTexture()
# USE xp.genrateTextureNumbers(count) instead of glGenTextures()


def load():
    # Here I store my 'globals' -- data, which I need for my test example.
    Data['flip'] = True
    Data['logo_x'] = 0.
    Data['logo_y'] = 0.
    Data['logo_x_speed'] = .5
    Data['logo_y_speed'] = .5
    Data['stencil'] = False
    Data['Textures'] = {}
    Data['Fonts'] = {}
    Data['Textures']['logo'] = xpgl.loadImage('Resources/plugins/XPPython3/xppython3.png')
    Data['Fonts']['Helvetica'] = xpgl.loadFont('Resources/fonts/Roboto-Regular.ttf', 18)


def draw():
    # Here is my draw routine... since I'm calling two different draw routines,
    # I simply redirect
    return draw_example1() if not Data['flip'] else draw_example2()


####
# Some example draw routines.... If you're coding your own, your
# code can completely be within draw(), above.

def draw_example1():
    # to axis lines
    xpgl.drawLine(Width / 2, 0, Width / 2, Height)
    xpgl.drawLine(0, Height / 2, Width, Height / 2)

    with xpgl.maskContext():
        xpgl.drawTriangle(Width / 2, Height - 60, Width - 50, 40, 50, 40, color=Colors['green'])
        xpgl.drawUnderMask(stencil=Data['stencil'])
        xpgl.drawCircle(Width / 2, Height / 2, 150, isFilled=True, color=Colors['orange'])
    xpgl.drawCircle(Width / 2, Height / 2, 50, isFilled=True)


def computeLogoPosition(logo_width, logo_height):
    Data['logo_x'] += Data['logo_x_speed']
    Data['logo_y'] += Data['logo_y_speed']
    while Data['logo_x'] >= Width - (logo_width + 1) or Data['logo_x'] <= 0:
        Data['logo_x_speed'] = (-1 if Data['logo_x_speed'] > 0 else 1) * random.gauss(.5, .2)
        Data['logo_x'] += Data['logo_x_speed']
    while Data['logo_y'] >= Height - (logo_height + 1) or Data['logo_y'] <= 0:
        Data['logo_y_speed'] = (-1 if Data['logo_y_speed'] > 0 else 1) * random.gauss(.5, .2)
        Data['logo_y'] += Data['logo_y_speed']
    return Data['logo_x'], Data['logo_y']


def draw_example2():
    # first, some aligned text
    xpgl.drawLine(125, 400, 125, Height, color=xpgl.Colors['cyan'])
    xpgl.drawText(Data['Fonts']['Helvetica'], 125, 480, "Left-Aligned", color=xpgl.Colors['green'])
    xpgl.drawText(Data['Fonts']['Helvetica'], 125, 460, "Right-Aligned", alignment='r', color=xpgl.Colors['green'])
    xpgl.drawText(Data['Fonts']['Helvetica'], 125, 440, "Center-Aligned", alignment='C', color=xpgl.Colors['green'])

    # draw a line "underneath" the logo and triangles
    xpgl.drawLine(0, 0, Width, Height, color=xpgl.Colors['pink'])

    # draw a bouncing logo
    logo_width = 140
    logo_height = 88
    x, y = computeLogoPosition(logo_width, logo_height)
    xpgl.drawTexture(Data['Textures']['logo'], x, y, logo_width, logo_height)

    # a rotating triangle which will mask a stationary Trianglevvvvvvvvv
    with xpgl.maskContext():
        # First, the mask
        with xpgl.graphicsContext():
            xpgl.setRotateTransform(xp.getCycleNumber() % 360, Width / 2, 190)
            xpgl.drawTriangle(180, 165,
                              Width / 2, Height - 220,
                              Width - 180, 165, xpgl.Colors['green'])

        xpgl.drawUnderMask(stencil=Data['stencil'])
        # Second the drawing(s) affected by the mask
        xpgl.drawTriangle(100, 100, Width / 2, Height - 100, Width - 100, 100, xpgl.Colors['green'])

    # draw a rotated arc above everything else
    with xpgl.graphicsContext():
        xpgl.setRotateTransform(90, Width / 2, Height / 2)
        xpgl.drawArc(Width / 2, Height / 2,
                     radius_inner=10, radius_outer=20,
                     start_angle=0, arc_angle=180, color=xpgl.Colors['red'])
    glFlush()


# =================================================================================================
# You should not need to modify anything below here.
# We set up the GLUT window with callbacks, and set the OpenGL
# context to match (as best we can) what X-Plane sets.
#
# You *may* find it useful to alter the keyPressed function below to
# alter values or behavior of your test.
# =================================================================================================


def keyPressed(key):
    if key == 'q':
        os._exit(0)
    elif key == 'X':
        os._exit(-1)
    elif key == 'R':
        xpgl.report()
    elif key == 'f':
        Data['flip'] = not Data['flip']
    elif key == 's':
        Data['stencil'] = not Data['stencil']
        print(f"Mask/Stencil is now {'Stencil' if Data['stencil'] else 'Mask'}")


FRAME_EVENT = pygame.USEREVENT + 1


def main():
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 16)
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 16)
    pygame.display.set_mode((Width, Height), pygame.OPENGL | pygame.RESIZABLE)
    glClearColor(0.0, 0.0, 0.0, 1.0)  # This Will Clear The Background Color To Black
    glClearDepth(1.0)  # Enables Clearing Of The Depth Buffer
    if Mode in (Modes.AvionicsScreen, ):
        glClear(GL_DEPTH_BUFFER_BIT)
    else:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # glClearColor() is previously set
    pygame.display.set_caption("OpenGL Tester")
    glLoadIdentity()  # Reset The Projection Matrix

    pygame.time.set_timer(FRAME_EVENT, 29)

    load()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                keyPressed(event.unicode)
            elif event.type == FRAME_EVENT:
                xp.Counter += 1

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glDepthMask(GL_TRUE)
        if Mode in (Modes.AvionicsScreen, ):
            glClear(GL_DEPTH_BUFFER_BIT)
        else:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # glClearColor() is previously set
        glLoadIdentity()  # Reset The View... (0, 0) is center of screen X runs left-right, Y runs Up down.
        glOrtho(0, Width, 0, Height, 0, 1)

        try:
            draw()
        except Exception as e:
            print(f"Error while drawing screen {e}")
            traceback.print_exception(e)
            os._exit(-1)

        if Mode not in (Modes.AvionicsScreen, ):
            glFlush()

        # pygame.display.flip()
        pygame.time.wait(10)


if __name__ == '__main__':
    print("Hit 'q' key in window to quit.")
    print("Hit 'f' key in window 'flip' to different drawing routine.")
    print("Hit 's' key in window alter stencil vs. mask")
    main()
