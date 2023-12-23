from XPPython3 import xp
# Modeled after
# Bill Good's demo: https://github.com/sparker256/xp12-fmod-sdk-demo/blob/main/src/xp12_fmod_sdk_demo.cpp */

# use ctypes to load fmod libraries, and define PyCapsule_GetPointer to extra C-language pointer
# from a capsule
import ctypes   # type:ignore
import platform
if platform.system() == 'Darwin':
    studio_dll = ctypes.cdll.LoadLibrary('libfmodstudio.dylib')    # type:ignore
    fmod_dll = ctypes.cdll.LoadLibrary('libfmod.dylib')   # type:ignore
elif platform.system() == 'Windows':
    studio_dll = ctypes.windll.LoadLibrary('fmodstudio')  # type:ignore
    fmod_dll = ctypes.windll.LoadLibrary('fmod')   # type:ignore
elif platform.system() == 'Linux':
    studio_dll = ctypes.cdll.LoadLibrary('libfmodstudio.so.13')   # type:ignore
    fmod_dll = ctypes.cdll.LoadLibrary('libfmod.so.13')   # type:ignore

def PyCapsule_GetPointer(capsule, name):
    # convenience function to get a void * out of a python capsule
    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
    # cast it to c_void_p as otherwise, it's an 'int'
    return ctypes.c_void_p(ctypes.pythonapi.PyCapsule_GetPointer(capsule, name.encode('utf-8')))

# convenient FMOD enumerations... there are hundreds more in FMOD headers, but these are the only ones I'm using:
FMOD_DEFAULT = 0
FMOD_TIMEUNIT_PCM = 2

def getDelayToCurrentSoundEnd(outputSampleRate, playingChannel):
    if playingChannel is None:
        return 0
    startdelay = ctypes.c_int(0)
    soundlength = ctypes.c_int(0)
    soundfrequency = ctypes.c_float()
    playingsound = ctypes.c_void_p()

    # get the channel DSP clock, which serves as a reference
    fmod_dll.FMOD_Channel_GetDSPClock(playingChannel, 0, ctypes.byref(startdelay))

    # Grab the length of the playing sound, and its frequency, so we can calculate where to plae the new sound
    fmod_dll.FMOD_Channel_GetCurrentSound(playingChannel, ctypes.byref(playingsound))
    fmod_dll.FMOD_Sound_GetLength(playingsound, ctypes.byref(soundlength), FMOD_TIMEUNIT_PCM)
    fmod_dll.FMOD_Channel_GetFrequency(playingChannel, ctypes.byref(soundfrequency))

    # Now calculate the legnth of the sound in 'output samples'
    # Ie if a 44khz sound is 22050 samples long, that's 22050 / 44000 or ~0.5 seconds.
    # if the output rate is output rate is 48khz, then we want
    # to delay by 48 * 0.5 = 24000 output samples
    soundlength.value *= outputSampleRate.value
    soundlength.value = int(soundlength.value / soundfrequency.value)
    startdelay.value += soundlength.value
    return startdelay

class PythonInterface:
    def __init__(self):
        self.flightLoopID = None
        self.fmodSystem = ctypes.c_void_p()
        self.soundFiles = ['10ft.wav', '20ft.wav', '30ft.wav', '40ft.wav',]  # all found in Resources/sounds/alert/
        self.sounds = {}
        self.com1_channel_group = ctypes.c_void_p()

    def XPluginStart(self):
        self.flightLoopID = xp.createFlightLoop(self.flightLoop, phase=xp.FlightLoop_Phase_AfterFlightModel)
        return "FMOD-advanced XPPython3 v.1", "fmod_advanced_demo.xppython3", "Use ctypes to access FMOD"

    def XPluginStop(self):
        if self.flightLoopID:
            xp.destroyFlightLoop(self.flightLoopID)

    def XPluginEnable(self):
        return 1

    def XPluginReceiveMessage(self, inFrom, inMessage, inParam):
        if xp.PLUGIN_XPLANE == inFrom:
            if xp.MSG_FMOD_BANK_LOADED == inMessage and xp.RadioBank == inParam:
                # Get FMODSystem from FMODStudio
                fmodStudio = PyCapsule_GetPointer(xp.getFMODStudio(), 'FMOD_STUDIO_SYSTEM')
                studio_dll.FMOD_Studio_System_GetCoreSystem(fmodStudio, ctypes.byref(self.fmodSystem))

                # create custom channel group
                fmod_dll.FMOD_System_CreateChannelGroup(self.fmodSystem, b'Demo_Channel',
                                                          ctypes.byref(self.com1_channel_group))

                # get existing channel group, and add ours to it
                com1_ptr = PyCapsule_GetPointer(xp.getFMODChannelGroup(xp.AudioRadioCom1), 'FMOD_CHANNELGROUP')
                fmod_dll.FMOD_ChannelGroup_AddGroup(com1_ptr, self.com1_channel_group, True, None)

                # Load sounds
                for idx, filename in enumerate(self.soundFiles):
                    path = xp.getSystemPath() + f'/Resources/sounds/alert/{filename}'
                    self.sounds[idx] = ctypes.c_void_p()
                    fmod_dll.FMOD_System_CreateSound(
                        self.fmodSystem,
                        ctypes.c_char_p(path.encode('utf-8')),
                        FMOD_DEFAULT,
                        None,
                        ctypes.byref(self.sounds[idx]))

                xp.scheduleFlightLoop(self.flightLoopID, 1.)

    def flightLoop(self, *_args):
        try:
            sampleRate = ctypes.c_int()
            fmod_dll.FMOD_System_GetSoftwareFormat(self.fmodSystem, ctypes.byref(sampleRate), 0, 0)

            # define four channels, which will hold c-pointers
            # each will be initialized to play a different sound
            channels = {}
            delay_sum = 0
            for i in range(len(self.soundFiles)):
                channels[i] = ctypes.c_void_p()
                fmod_dll.FMOD_System_PlaySound(self.fmodSystem, self.sounds[i],
                                                 self.com1_channel_group, False,
                                                 ctypes.byref(channels[i]))
            for i in range(len(self.soundFiles)):
                if i > 0:
                    delay = getDelayToCurrentSoundEnd(sampleRate, channels[i-1])
                    delay_sum = delay.value + (i-1) * 20000
                    fmod_dll.FMOD_Channel_SetDelay(channels[i], ctypes.c_int(delay_sum), 0, True)
                    fmod_dll.FMOD_Channel_SetPaused(channels[i], False)

        except Exception as e:
            xp.log(f"PlaySound failed {e}")
            return 0.0
        return 10.0
