import threading
import serial
import serial.tools.list_ports
import xp


def find_arduino():
    # find first device with 'arduino' in it's manufacturer name.
    # This probably doesn't work for some clones, so you may
    # need to either list all ports and have user select, or
    # alter your search.
    #
    # Also, we return the first one found... if you have more
    # than one, you'd need to do something different!
    ports = serial.tools.list_ports.comports()
    return [x.device for x in ports if x.manufacturer and 'arduino' in x.manufacturer.lower()][0]
    

def poll_arduino(arduino, data):
    #
    # This runs _only_ within a separate thread.
    # It's an infinite loop which reads data from
    # the arduino as quickly as possible. readline() waits
    # for data to be available, but, because this is in
    # a separate thread, it does not cause X-Plane to wait.
    # On receipt of data, it updates shared data, making
    # the results available to the main thread.
    #
    # Do NOT call any XPLM code from within this thread!
    while True:
        if data['kill']:  # be setting data value, we can signal exit
            return
        a = arduino.readline()
        if a:
            data['var'] = a.decode('utf-8')


def flightloop_callback(_since, _elapsed, _counter, refCon):
    # Simple flight loop 
    xp.log(f"Value of var is {refCon['var']}")
    xp.log()  # (this immediately flushes to log buffer)
    return 1.0


def draw_callback(_phase, _after, refCon):
    # Simple draw callback, in green, in the lower left of the screen
    xp.drawString((0, 1, 0), 10, 10, f"Arduino says: {refCon['var']}")
    return 1


class PythonInterface:
    def __init__(self):
        self.thread = None
        self.shared_data = {}
        self.floop = None
        
    def XPluginStart(self):
        # Find the device and connect with it
        device = find_arduino()
        arduino = serial.Serial(port=device, baudrate=115200, timeout=.1)

        # start a thread which will poll the device and update shared data
        # so "we", the main thread, can access the data.
        self.shared_data = {'var': None, 'kill': False}
        self.thread = threading.Thread(target=poll_arduino, args=(arduino, self.shared_data))
        self.thread.start()
        return "Arduino1 Example v1.0", "xppython3.example.arduino1", "XPPython3 Arduino Example"

    def XPluginEnable(self):
        # We use a simple flight loop in order to periodically see and display
        self.floop = xp.createFlightLoop(flightloop_callback, refCon=self.shared_data)
        xp.scheduleFlightLoop(self.floop, -1)
        
        # And..., just to show that we can, we also display the results on screen using a draw callback.
        xp.registerDrawCallback(draw_callback, refCon=self.shared_data)

        # Compare and contrast:
        # * 'draw_callback' is called, of course, every time X-Plane wants to draw
        #   That means it always shows the current value from Arduino. Because the
        #   arduino is updating itself every 150 mseconds, the display rapidly changes.
        #
        # * 'flighloop_callback' is called only once per second, so the values
        #   that get logged are non-contiguous.
        #   

        return 1

    def XPluginDisable(self):
        if self.floop:
            xp.destroyFlightLoop(self.floop)
            self.floop = None
        xp.unregisterDrawCallback(draw_callback, refCon=self.shared_data)
        
    def XPluginStop(self):
        # Set flag so thread will exit, and then wait to join
        # Remember:
        #   if you enable it, you should disable it;
        #   if you start it, you should stop it.
        self.shared_data['kill'] = True
        self.thread.join()
        

# The arduino program I'm using is:
#   int x = 0;
#   void setup() {
#     Serial.begin(115200);
#     Serial.setTimeout(1);
#   }
#   
#   void loop() {
#     x += 1;
#     delay(150);
#     Serial.print(x);
#   }
