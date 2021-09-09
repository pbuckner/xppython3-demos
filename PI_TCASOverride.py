from XPPython3 import xp
try:
    # earlier versions of xp.py were missing the shortcut for MSG_RELEASE_PLANES
    MSG_RELEASE_PLANES = xp.MSG_RELEASE_PLANES
except AttributeError:
    from XPLMPlugin import XPLM_MSG_RELEASE_PLANES as MSG_RELEASE_PLANES

# ORIGINAL IN C:
#   https://developer.x-plane.com/code-sample/overriding-tcas/
# See also discussion about this features in:
#   https://developer.x-plane.com/article/overriding-tcas-and-providing-traffic-information/
# This plugin creates four traffic targets that will fly circles around the users' plane. These traffic
# targets exist purely as TCAS targets, not as 3D objects, as such would usually be placed by XPLMInstance


# for convenience, I'm going to define the altitude in feet and the distance in nm and convert later
fttomtr = 0.3048
nmtomtr = 1852.0

# how many targets this plugin generates.
TARGETS = 4

# datarefs we are going to write to
modeSid = None
flt_id = None
brg = None
dis = None
alt = None
override = None

# datarefs for our own plane
psi = None
ele = None

# whether our plugin is in charge
plugin_owns_tcas = False


ids = [0xA51B64, 0xAB90C2, 0xADCB98, 0xA08DB8]  # Required: unique ID for the target. Must be 24bit number.
tailnum = [b"N428X", b"N844X", b"N98825", b"N1349Z"]  # Optional: Flight ID is item 7 of the ICAO flightplan. So it can be the tailnumber OR the flightnumber! Cannot be longer than 7 chars+nullbyte!

# the initial position of our four targets. We'll place them directly north, east, etc. of us
# at various altitudes and distances between 3 and 6 nautical miles
absbrgs = [0, 90, 180, 270]
absalts = [1000, 1500, 2000, 4000]
dists = [6 * nmtomtr, 5 * nmtomtr, 4 * nmtomtr, 3 * nmtomtr]

# this flightloop callback will be called every frame to update the targets
relbrgs = [None, ] * TARGETS
relalts = [None, ] * TARGETS


def floop_cb(elapsed1, elapsed2, ctr, refcon):
    # make some targets change altitude
    absalts[0] += 400 * elapsed1 / 60.0  # target is climbing 400fpm
    absalts[3] -= 600 * elapsed1 / 60.0  # target descending 600fpm

    for i in range(TARGETS):
        # targets are just flying perfect circles around the user.
        absbrgs[i] += (i + 1) * elapsed1  # this just makes the targets fly circles of varying speed
        relbrgs[i] = absbrgs[i] - xp.getDataf(psi)  # convert to relative position for TCAS dataref. Use true_psi, not hpath or something else
        relalts[i] = absalts[i] * fttomtr - xp.getDatad(ele)  # convert to relative position for TCAS dataref. Use elevation, not local_y!

    # if we are in charge, we can write four targets to the four TCAS datarefs, starting at index 1
    # Note this dataref write would do nothing if we hadn't acquired the planes and set override_TCAS
    if plugin_owns_tcas:
        # These relative coordinates, or the absolute x/y/z double coordinates must be updated to keep the target flying, obviously.
        # X-Plane will forget about your target if you don't update it for 10 consecutive frames.
        xp.setDatavf(brg, relbrgs, 1, TARGETS)
        xp.setDatavf(dis, dists, 1, TARGETS)
        xp.setDatavf(alt, relalts, 1, TARGETS)
        # You could also update sim/cockpit2/tcas/targets/position/double/plane1_x, plane1_y, etc..
        # In which case X-Plane would update the relative bearings for you
        # So for one target, you can write either absolute coorindates or relative bearings, but not both!
        # For mulitple targets, you can update some targets in relative mode, and others in absolute mode.

    # be sure to be called every frame. A target not updated for 10 successive frames will be dropped.
    return -1


# A simple reset we will call every minute to reset the targets to their initial position and altitude
def reset_cb(elapsed1, elapsed2, ctr, refcon):
    absbrgs[0] = 0
    absbrgs[1] = 90
    absbrgs[2] = 180
    absbrgs[3] = 270

    absalts[0] = 1000
    absalts[3] = 4000
    return 60  # call me again in a minute


# we call this function when we succesfully acquired the AI planes.
# Arthur says: BRILLIANT! My Jets Now!
def my_planes_now():
    xp.debugString("TCAS test plugin now has the AI planes!\n")
    xp.setDatai(override, 1)  # If you try to set this dataref when not owning the planes, it will fail!

    # query the array size. This might change with X-Plane updates.
    max_targets = xp.getDatavi(modeS_id, None, 0, 0)
    assert TARGETS < max_targets

    xp.setActiveAircraftCount(TARGETS)  # This will give you four targets, even if the user's AI plane count is set to 0. This can be as high as 63!
    global plugin_owns_tcas
    plugin_owns_tcas = True

    # As long as you keep updating the positions, X-Plane will remember the ID.
    # These IDs can be used by other plugins to keep track of your aircraft if you shuffle slots.
    # Note that the ID cannot be left 0! X-Plane will not update your target's dependent datarefs if it has no ID!!
    # If you haven't updated a target for 10 frames, X-Plane will forget it and reset the ID of the slot to 0.
    xp.setDatavi(modeS_id, ids, 1, TARGETS)

    # Each target can have a 7 ASCII character flight ID, usually the tailnumber or flightnumber
    # it consists of an 8 byte character array, which is null terminated.
    # The array is 64*8 bytes long, and the first 8 bytes are the user's tailnumber obviously.
    # Note that this is, unlike the Mode-S ID, totally optional.
    # But it is nice to see the tainumber on the map obviously!
    for i in range(1, TARGETS + 1):
        xp.setDatab(flt_id, tailnum[i - 1], i * 8, len(tailnum[i - 1]))  # copy at most 8 characters, but not more than we actually have.

    # start updating
    xp.registerFlightLoopCallback(floop_cb, 1, None)
    xp.registerFlightLoopCallback(reset_cb, 60, None)


# we call this function when we want to give up on controlling the AI planes
# For example, a network plugin would do this as soon as you disconnect from your multiplayer session!
def someone_elses_planes_now():
    # stop updating
    xp.unregisterFlightLoopCallback(floop_cb, None)
    xp.unregisterFlightLoopCallback(reset_cb, None)
    # relinquish control
    global plugin_owns_tcas
    plugin_owns_tcas = False
    xp.setDatai(override, 0)  # order is important! Relinquish the override first
    xp.releasePlanes()  # Then release the AI planes to another plugin! Note that another plugins AcquirePlanes callback function might be called here synchronously


# this is a callback that will be called by X-Plane, if we asked for planes, but another plugin had the planes at the time
# but now this other plugin has given up the planes. They essentially yielded control to us. So the planes are up for grabs again!!
def retry_acquiring_planes():

    if not xp.acquirePlanes(None, retry_acquiring_planes, None):
        # Damn, someone else cut imn the queue before us!
        # this can happen if more than two plugins are all competing for AI.
        xp.debugString("TCAS test plugin could not get the AI planes, even after the previous plugin gave them up. We are waiting for the next chance\n")
    else:
        # Acquisition succeded.
        my_planes_now()


class PythonInterface:
    def XPluginStart(self):
        name = "TCAS override test"
        sig = "com.laminarresearch.test.tcas"
        desc = "Test plugin for TCAS override datarefs"
        return name, sig, desc

    def XPluginStop(self):
        pass

    def XPluginEnable(self):
        global psi, ele
        psi = xp.findDataRef("sim/flightmodel/position/true_psi")
        ele = xp.findDataRef("sim/flightmodel/position/elevation")

        # these datarefs were read-only until 11.50
        global brg, dis, alt, modeS_id, flt_id
        brg = xp.findDataRef("sim/cockpit2/tcas/indicators/relative_bearing_degs")
        dis = xp.findDataRef("sim/cockpit2/tcas/indicators/relative_distance_mtrs")
        alt = xp.findDataRef("sim/cockpit2/tcas/indicators/relative_altitude_mtrs")
        # these datarefs are new to 11.50
        modeS_id = xp.findDataRef("sim/cockpit2/tcas/targets/modeS_id")  # array of 64 int
        flt_id = xp.findDataRef("sim/cockpit2/tcas/targets/flight_id")  # array of 64*8 bytes

        # this dataref can only be set if we own the AI planes!
        global override
        override = xp.findDataRef("sim/operation/override/override_TCAS")

        ## STOP
        ## DROP AND LISTEN
        # In a real application, you would only do the next step if you are immediately ready to supply traffic.
        # I.e. if you are connected to a session if you are a multiplayer plugin. Don't preemptively acquire the traffic
        # just because you might connect to a session some time later!
        # So this piecce of code is probably not going to be in XPluginEnable for you.
        # It is going to be wherever you are actually done establishing your traffic source!

        # try to acquire planes. If a different plugin has them, this will fail.
        # If the other plugin releases them, our callback will be called.
        if not xp.acquirePlanes(None, retry_acquiring_planes, None):
            # If acquisition has failed, gather some intelligence on who currently owns the planes
            (total, active, controller) = xp.countAircraft()
            who = xp.getPluginInfo(controller)
            xp.debugString("TCAS test plugin could not get the AI planes, because ")
            xp.debugString(who.name)
            xp.debugString(" owns the AI planes now. We'll get them when he relinquishes control.\n")
            # Note that the retry callback will be called when this other guy gives up the planes.
        else:
            # Acquisition succeded.
            my_planes_now()
        return 1

    def XPluginDisable(self):
        someone_elses_planes_now()

    def XPluginReceiveMessage(self, msg_from, msg, param):
        if msg == MSG_RELEASE_PLANES:
            # Some other plugin wants the AI planes. Since this is just a dummy traffic provider, we yield
            # to a real traffic provider. Deactivate myself now!
            # If this was send to a VATSIM plugin while the user is connected, of course it would just ignore this message.
            someone_elses_planes_now()

            who = xp.getPluginInfo(msg_from)
            xp.debugString("TCAS test plugin has given up control of the AI planes to ")
            xp.debugString(who.name)
            xp.debugString("\n")
