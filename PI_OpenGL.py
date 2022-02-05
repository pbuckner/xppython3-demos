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
#    However:
#    Newer (2021) Macs running Big Sur (MacOS 11.2) (and perhaps newer...)
#    changed the way shared libaries are stored physically on disk. Specifically,
#    the 'OpenGL' python module requires to OS-provided OpenGL shared libraries.
#    On startup, the python module attempts to find and load these shared libraries
#    but will fail on Big Sur (and only Big Sur, as far as I know). The bug
#    exists in python's integrated ctypes module and remains unfixed (as of 4/16/2021)
#    in all versions of python.
#
#    We attempt to detect this case: 'import OpenGL' does not actually load
#    the libraries, so if this is successful, but 'import OpenGL.GL' is not,
#    we look to see if the current system is a Mac running Big Sur. If not, we bail.
#    If it is, we attempt to MODIFY IN PLACE the library loader used by python OpenGL.
#      * The loader is in the file 'opengl/platform/ctypesloader.py' which *should*
#        be under python's site-packages. That's where we look for it.
#      * Assuming we find the file, we edit the existing line:
#            fullName = util.find_library( name )
#        Changing it to:
#            fullName = '/System/Library/Frameworks/{}.framework/{}'.format(name, name)
#        We *know* where the OpenGL shared objects are supposed to be located,
#        even though they're not there physically on the disk -- that's the Big Sur
#        issue -- Big Sur caches the libraries.
#        ... You can make this edit directly with a text editor, if this script fails.
#      * Assuming we're able to make the edit, we do some python magic to remove old
#        module definitions and re-import 'OpenGL.GL'.
#
# If all works, we display an OpenGL graphic.
# NOTE:
#   Once OpenGL is installed, you don't need to do all this magic to use it. Simply
#   do 'import OpenGL.GL as GL' and/or 'import OpenGL.GLUT as GLUT' and it will work!


class PythonInterface:
    def XPluginStart(self):
        self.openGL = False
        return 'PI_OpenGL v1.0', 'xppython3.opengl_test', 'Tests OpenGL installation'

    def XPluginEnable(self):
        try:
            import OpenGL
        except ModuleNotFoundError:
            cmd = [xp.pythonExecutable, '-m', 'pip', 'install', '--user', 'pyopengl']
            print("Calling pip as: {}".format(' '.join(cmd)))
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                output = output.decode('utf-8').split('\n')
                xp.log(output)
            except subprocess.CalledProcessError as e:
                xp.log("Fail: Calling pip failed: [{}]: {}".format(e.returncode, e.output.decode('utf-8')))
                return 0
        try:
            import OpenGL
        except ModuleNotFoundError as e:
            xp.log("Fail: Cannot load package for OpenGL: {}".format(e))
            return 0

        # [x for x in sys.modules if 'OpenGL' in x]
        # ['OpenGL.version', 'OpenGL.plugins', 'OpenGL']

        xp.log("Python OpenGL (pyopengl) installed")
        try:
            import OpenGL.GL as GL
        except ImportError as e:
            # Here, python OpenGL has been successfully imported, so if GL doesn't work,
            # it is most likely due to Apple's Big Sur implementation which moved the OpenGL shared
            # object library.
            #    (MacOS 11.2 "Big Sur" is known internally as version '10.16')
            if platform.system() == 'Darwin' and platform.mac_ver()[0] == '10.16':
                ctypes_file = os.path.join(os.path.dirname(OpenGL.__file__), 'platform/ctypesloader.py')
                xp.log("For Mac 10.16 \"Big Sur\" you need to also edit {}.".format(ctypes_file))
                try:
                    with FileInput(files=(ctypes_file,), inplace=True, backup='.bak') as file_input:
                        for line in file_input:
                            print(line, end="")
                            if 'fullName = util.find_library(' in line:
                                print(line.replace('util.', "'/System/Library/Frameworks/{}.framework/{}'.format(name, name)  # util."), end="")
                    xp.log('file modified')
                    # Now, invalidate previous
                    xp.log(str([x for x in sys.modules if 'OpenGL' in x]))
                    for i in [x for x in sys.modules if x.startswith('OpenGL')]:
                        del sys.modules[i]
                        xp.log("removing {}".format(i))
                    xp.log('finished removing')
                except Exception as e:
                    xp.log("Fail: Failed to update ctypesloader: {}".format(e))
                    return 0
            else:
                xp.log("Failed to import OpenGL.GL: {}".format(e))
                return 0
        xp.log("trying to load OpenGL.GL")
        try:
            import OpenGL.GL as GL
            globals()['GL'] = GL
        except Exception as e:
            xp.log("Failed final attemd with GL: {}".format(e))
            return 0
        self.openGL = True
        self.createWindow()
        xp.log("OpenGL successfully loaded")
        return 1

    def XPluginDisable(self):
        pass

    def XPluginStop(self):
        pass

    def XPluginReceiveMessage(self, message, *args, **kwargs):
        pass

    def createWindow(self):
        windowInfo = (50, 600, 300, 400, 1,
                      self.drawWindowCallback,
                      self.MouseClickCallback,
                      self.KeyCallback,
                      self.CursorCallback,
                      self.MouseWheelCallback,
                      0,
                      xp.WindowDecorationRoundRectangle,
                      xp.WindowLayerFloatingWindows,
                      None)
        self.WindowId = xp.createWindowEx(windowInfo)

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

    def MouseClickCallback(self, *args):
        return 1

    def KeyCallback(self, *args):
        pass

    def CursorCallback(self, *args):
        return xp.CursorDefault

    def MouseWheelCallback(self, *args):
        return 1
