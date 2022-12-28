import platform
import sys
import os
import subprocess
from fileinput import FileInput
import XPPython3.xp as xp

#
# This plugin tests for the existence of OpenGL and attempts
# to install the 'pyopengl' python module.
# If successful, a message is displayed in a X-Plane window.
# If unsuccessful, hopefully sufficient information is provided
# in XPPython3.log in order to diagnose and fix the problem.
#
# Potential issues:
# a) if we cannot load python module 'OpenGL', we will attempt
#    to install it using '<python> -m pip install --user pyopengl'.
#    This will fail if:
#      * There are network issues (which we don't explicitly
#        check for). If this happens fix your network and retry.
#      * We don't have permission to install in --user space.
#        As "you" are installing the module, "you" should have
#        permission to install in that location, so this should
#        not fail. If this happens, you should attempt to
#        manually install 'pyopengl' module, doing something from
#        the command line like:
#           python3 -m pip install pyopengl
# b) Assuming we can (either find, or) load OpenGL, the pyopengl module,
#    we next try to import OpenGL.GL, which will pull in the OS shared libraries
#    (which are always installed with the OS -- you don't need to manually install these).
# NOTE:
#   Once OpenGL is installed, you don't need to do all this magic to use it. Simply
#   do 'import OpenGL.GL as GL' and/or 'import OpenGL.GLUT as GLUT' and it will work!


class PythonInterface:
    def XPluginStart(self):
        return 'PI_OpenGL v1.1', 'xppython3.opengl_test', 'Tests OpenGL installation'

    def XPluginEnable(self):
        if not tryLoadOpenGL():
            xp.log("OpenGL loading failed")
            return 0
        self.createWindow()
        xp.log("OpenGL successfully loaded")
        return 1

    def createWindow(self):
        windowInfo = (50, 600, 300, 400, 1,
                      self.drawWindowCallback,
                      0,
                      xp.WindowDecorationRoundRectangle,
                      xp.WindowLayerFloatingWindows,
                      None)
        self.WindowId = xp.createWindowEx(left=50, top=600, right=300, bottom=400, visible=1, draw=self.drawWindowCallback)

    def drawWindowCallback(self, windowID, refCon):
        (left, top, right, bottom) = xp.getWindowGeometry(windowID)
        xp.drawString((1.0, 1.0, 1.0), left + 5, bottom + 5, "OpenGL successfully installed!", 0, xp.Font_Basic)
        xp.setGraphicsState(0, 0, 0, 0, 1, 1, 0)
        bottom += 20
        # Draw a rectangle with a color gradiant
        numLines = int(min(top - bottom, right - left) / 2)
        time = int(numLines * xp.getElapsedTime()) % numLines
        for i in range(numLines):
            GL.glBegin(GL.GL_LINE_LOOP)
            left += 1
            right -= 1
            bottom += 1
            top -= 1
            x = (i + time) % numLines
            GL.glColor3f(x / numLines, (numLines - x) / numLines, x / numLines)  # change colors, for fun
            GL.glVertex2f(left, bottom)
            GL.glVertex2f(left, top)
            GL.glVertex2f(right, top)
            GL.glVertex2f(right, bottom)
            GL.glEnd()

def tryLoadOpenGL():
    try:
        import OpenGL
    except ModuleNotFoundError:
        cmd = [xp.pythonExecutable, '-m', 'pip', 'install', '--user', 'pyopengl']
        xp.log(f"Calling pip as: {' '.join(cmd)}")
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            output = output.decode('utf-8').split('\n')
            xp.log(output)
        except subprocess.CalledProcessError as e:
            xp.log("Fail: Calling pip failed: [{}]: {}".format(e.returncode, e.output.decode('utf-8')))
            return False
    try:
        import OpenGL
    except ModuleNotFoundError as e:
        xp.log("Fail: Cannot load package for OpenGL: {}".format(e))
        return False

    xp.log("Python OpenGL (pyopengl) installed")
    try:
        import OpenGL.GL as GL
    except ImportError as e:
        # Here, python OpenGL has been successfully imported, so if GL doesn't work,
        # it is most likely due to Apple's Big Sur implementation which moved the OpenGL shared
        # object library. Newer versions of python have fixed this, so we no longer try
        # to hack a solution. Upgrade to at least python 3.11.0).
        #    (MacOS 11.2 "Big Sur" is known internally as version '10.16')
        xp.log("Failed to import OpenGL.GL: {}".format(e))
        return False
    xp.log("trying to load OpenGL.GL")
    try:
        import OpenGL.GL as GL
        globals()['GL'] = GL
    except Exception as e:
        xp.log(f"Failed final attempt with GL: {e}")
        return False
    return True
