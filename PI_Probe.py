from typing import Self
from XPPython3 import xp
from XPPython3.utils.easy_python import EasyPython
from XPPython3.utils.timers import run_timer
from XPPython3.utils.datarefs import find_dataref, DataRef
from XPPython3.xp_typing import XPLMProbeRef

M2FT = 3.28084


class PythonInterface(EasyPython):
    def __init__(self: Self) -> None:
        self.probe: XPLMProbeRef = None
        self.surface: float = None
        self.x: DataRef = None
        self.y: DataRef = None
        self.z: DataRef = None
        super().__init__()

    def onStart(self: Self) -> None:
        self.probe = xp.createProbe()
        self.x = find_dataref('sim/flightmodel/position/local_x')
        self.y = find_dataref('sim/flightmodel/position/local_y')
        self.z = find_dataref('sim/flightmodel/position/local_z')
        run_timer(self.queryProbe, delay=0, interval=5)
        xp.registerDrawCallback(self.draw)
        self.surface = None

    def queryProbe(self: Self) -> None:
        info = xp.probeTerrainXYZ(self.probe, self.x.value, self.y.value, self.z.value)
        self.surface = xp.localToWorld(info.locationX, info.locationY, info.locationZ)[2] * M2FT

    def draw(self: Self, *args) -> None:
        xp.drawString(x=10, y=10, value=f"{self.surface:.0f} ft")
