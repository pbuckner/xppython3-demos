from XPPython3 import xp
import multiprocessing

# This plugin spawns a separate process which listens for standard X-Plane
# UDP position data, and forwards this data to a remote server (maps.avnwx.com).
# That's all. On disable (X-Plane shutdown) we terminate the extra process.
#
# Real-time position is displayable at https://maps.avnwx.com.

# With few changes, this 50-line file can be used as a template
# to driver other multiprocessing type python plugins.

############################################################
# Set target python function to be executed in remote process
from avnwx.aircraft_udp_tracker import stream_to_server
TARGET = stream_to_server


class PythonInterface:
    def __init__(self):
        self.p = None
        self.fl = None

    def XPluginStart(self):
        return "AvnWx Tracker", "xppython3.avnwx.track", "Spawn external process to feed maps.avnwx.com aircraft tracking"

    def XPluginEnable(self):
        self.fl = xp.createFlightLoop(self.do_it)
        xp.scheduleFlightLoop(self.fl, -1)
        return 1

    def XPluginDisable(self):
        # On disable, we try gentle termination, followed by more drastic kill.
        if self.p and self.p.is_alive():
            self.p.terminate()
            self.p.join(timeout=5)
        if self.p and self.p.is_alive():
            self.p.kill()
            self.p.join(timeout=5)
        if xp.isFlightLoopValid(self.fl):
            xp.destroyFlightLoop(self.fl)

    def do_it(self, _since=0.0, _elapsed=0.0, _counter=0, _refCon=None) -> float:

        if self.p is not None:
            self.p.join()

        multiprocessing.set_executable(xp.pythonExecutable)  # !important, otherwise we spawn a copy of X-Plane
        self.p = multiprocessing.Process(target=TARGET, daemon=True)
        self.p.start()
        return 0
