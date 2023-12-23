from XPPython3 import xp
from XPPython3.xp_typing import *
import math

# Draw a couple of objects (red/white street traffic poles, in this case) using
# XPLMCreateInstance, but place them relative a moving aircraft.
# This plugin is inspired by @RandomUser on forums.x-plane.org,
# who was looking to do something similar.
# https://forums.x-plane.org/index.php?/forums/topic/276602-solution-aircraft-coordinates-to-world-coordinates/
#
# poleInstance1: red/white pole, centered in aircraft, moves and rotates as the aircraft rotates, giving
#                the appearance that the pole is welded to the airframe.
#
# poleInstance2: red/white pole, offset along the right wing



class PythonInterface:

    def __init__(self):
        self.objectRefs = []
        self.poleInstance1 = None
        self.poleInstance2 = None
        self.flightLoopID = None

    def XPluginStart(self):
        return "RightWingTip v1.0", "rightwingtip1.demos.xppython3", "Place Instance on Right Wing of Aircraft"

    def XPluginEnable(self):
        # get datarefs and schedule flightloop
        self.dataRefs = {'local_x': xp.findDataRef('sim/flightmodel/position/local_x'),  # OpenGL coordinates
                         'local_y': xp.findDataRef('sim/flightmodel/position/local_y'),  # OpenGL
                         'local_z': xp.findDataRef('sim/flightmodel/position/local_z'),  # OpenGL
                         'phi': xp.findDataRef('sim/flightmodel/position/phi'),    # degrees OpenGL
                         'theta': xp.findDataRef('sim/flightmodel/position/theta'),  # degrees OpenGL
                         'psi': xp.findDataRef('sim/flightmodel/position/psi'),  # degrees true, OpenGL
                         }
        self.flightLoopID = xp.createFlightLoop(self.flightLoopCallback, xp.FlightLoop_Phase_AfterFlightModel)
        xp.scheduleFlightLoop(self.flightLoopID, -1)
        return 1

    def XPluginDisable(self):
        if self.flightLoopID:
            xp.destroyFlightLoop(self.flightLoopID)
            self.flightLoopID = None

        if self.poleInstance1:
            xp.destroyInstance(self.poleInstance1)
            xp.destroyInstance(self.poleInstance2)
            self.poleInstance1 = None
            self.poleInstance2 = None

    def flightLoopCallback(self, lastCall, elapsedTime, counter, refCon):
        # instance loading is dependent upon the location of the user aircraft,
        # so best to load it after user aircraft has been placed -- that's easy
        # to do within a flight loop callback (but be sure to do it only once!)

        if self.objectRefs == []:
            # use a callback: once the object has been loaded, create object instances
            def loaded(objectRef, _):
                self.poleInstance1 = xp.createInstance(objectRef)
                self.poleInstance2 = xp.createInstance(objectRef)

            # because lookupObjects() is synchronous, we know we'll only do this once.
            num_found = xp.lookupObjects('lib/airport/Common_Elements/Markers/Poles/Thin_Red_White.obj',
                                         enumerator=lambda path, _: self.objectRefs.append(path))
            xp.loadObjectAsync(self.objectRefs[0], loaded)

        # Then, once the instances have been loaded, you can position them
        if self.poleInstance1 is not None:
            self.position_instances()
        return -1

    def position_instances(self):
        # pole 1 is "centered" on aircraft, with pitch, heading and roll matching the aircraft
        aircraft_position = (xp.getDatad(self.dataRefs['local_x']),
                             xp.getDatad(self.dataRefs['local_y']),
                             xp.getDatad(self.dataRefs['local_z']),
                             xp.getDataf(self.dataRefs['theta']),
                             xp.getDataf(self.dataRefs['psi']),
                             xp.getDataf(self.dataRefs['phi']),)
        xp.instanceSetPosition(self.poleInstance1, aircraft_position)


        # To compute an offset from the aircraft, we need to convert the offset
        # to (relative) 'world' coordinates and then add those offsets to the
        # current aircraft position

        offset = {'x': 5,  # lateral offset from aircraft origin in meters
                  'y': 0,
                  'z': 0}

        world_x, world_y, world_z = AcftToWorld(offset['x'],
                                                offset['y'],
                                                offset['z'],
                                                aircraft_position[5],  # phi
                                                aircraft_position[4],  # psi
                                                aircraft_position[3])  # theta

        position = XPLMDrawInfo_t(aircraft_position[0] + world_x,
                                  aircraft_position[1] + world_y,
                                  aircraft_position[2] + world_z,
                                  aircraft_position[3],
                                  aircraft_position[4],
                                  aircraft_position[5])

        xp.instanceSetPosition(self.poleInstance2, position)
        
def AcftToWorld(x_acft, y_acft, z_acft, phi, psi, theta):
    phi_rad = math.radians(phi)
    psi_rad = math.radians(psi)
    theta_rad = math.radians(theta)

    x_phi = (x_acft * math.cos(phi_rad)) + (y_acft * math.sin(phi_rad))
    y_phi = (y_acft * math.cos(phi_rad)) - (x_acft * math.sin(phi_rad))
    z_theta = (z_acft * math.cos(theta_rad)) + (y_phi * math.sin(theta_rad))
    out_x = (x_phi * math.cos(psi_rad)) - (z_theta * math.sin(psi_rad))
    out_y = (y_phi * math.cos(theta_rad)) - (z_acft * math.sin(theta_rad))
    out_z = (z_theta * math.cos(psi_rad)) + (x_phi * math.sin(psi_rad))
    return out_x, out_y, out_z
