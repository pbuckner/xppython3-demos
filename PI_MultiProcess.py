import os
try:
    from XPPython3 import xp
except ImportError:
    # 'xp' won't be available to the python child process, so guard against import failure
    pass

import multiprocessing

"""
Demonstrate the use of multiprocessing (and xp.pythonExecutable).

Result should be in your XPPython3.log similar to:

  [PythonPlugins.PI_MultiProcess] Calling from PID 38087                                                                                             [PythonPlugins.PI_MultiProcess] [42, None, 'hello from PID: 38167']           

"""

class PythonInterface:

    def XPluginStart(self):
        return 'PI_MultiProcess v1.0', 'xppython.demos.multiprocess', 'Example plugin using multiprocessing'

    def XPluginEnable(self):
        xp.log("Calling from PID {}".format(os.getpid()))
        parent_conn, child_conn = multiprocessing.Pipe()
        # IMPORTANT! Otherwise, sys.executable is used. When running X-Plane, it will be X-Plane app which will fail!
        multiprocessing.set_executable(xp.pythonExecutable)
        p = multiprocessing.Process(target=f, args=(child_conn, ))
        p.start()
        xp.log('{}'.format(parent_conn.recv()))
        # !!!! Note that 'join' will wait untill the called process has finished. This means
        # X-Plane will wait for this XPluginEnable() to complete prior to continuing.
        #
        # Alternatively, don't "join" here... Join in XPluginDisable(), for example
        p.join()
        return 1

    def XPluginDisable(self):
        pass

    def XPluginStop(self):
        pass

    def XPluginReceiveMessage(self, *args, **kwargs):
        pass


def f(conn):
    conn.send([42, None, 'hello from PID: {}'.format(os.getpid())])
    conn.close()
