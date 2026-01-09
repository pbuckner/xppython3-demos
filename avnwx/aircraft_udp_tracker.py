#!/usr/bin/env python3
"""
X-Plane Aircraft Position Tracker (UDP Broadcast Version)
Listens to X-Plane "Broadcast To All Mapping Apps" and streams position data to maps.avnwx.com

NO X-PLANE CONFIGURATION NEEDED (except enable "Broadcast To All Mapping Apps")!
This script automatically:
1. Listens for X-Plane UDP broadcasts on port 49002
2. Parses XGPS (position) and XATT (attitude) data
3. Streams to your browser

Just enable "Broadcast To All Mapping Apps" in X-Plane Network settings and run this script!
"""

import os
import socket
import requests
import time
import sys
import signal
from datetime import datetime

# Configuration
UDP_PORT = 49002  # Port to listen on for X-Plane UDP
SERVER_URL = "https://maps.avnwx.com/api/aircraft/push"
BAD_API_KEY = 'your-api-key'

logFile = None


def log(*args):
    """Log message with timestamp"""
    global logFile  # pylint: disable=global-statement
    if not logFile:
        try:
            logFile = open("Resources/plugins/PythonPlugins/avnwx/trackerLog.txt", "w", encoding='utf-8')
        except FileNotFoundError:
            logFile = sys.stdout

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}]", *args, file=logFile, flush=True)


class XPlaneUDPReceiver:
    """Receives position data from X-Plane UDP broadcast on port 49002"""

    def __init__(self):
        self.sock = None
        self.position_data = {}
        self.xgps_data = {}
        self.xatt_data = {}
        self.last_receive_time = 0.0

    def start(self):
        """Start UDP receiver on port 49002"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # On MacOS, also need SO_REUSEPORT for UDP broadcast receiving
        if hasattr(socket, 'SO_REUSEPORT'):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)  # 500ms timeout
        self.sock.bind(('0.0.0.0', UDP_PORT))
        log(f"Listening for X-Plane UDP broadcasts on 0.0.0.0:{UDP_PORT}")
        log("Make sure 'Broadcast To All Mapping Apps' is enabled in X-Plane Network settings")
        log()

    def parse_xgps(self, data):
        """Parse XGPS message: Longitude, latitude, elevation (m), horizontal path (deg), true speed (m/s)"""
        try:
            values = data.decode('utf-8', errors='ignore').strip('\x00').split(',')
            if len(values) >= 5:
                self.xgps_data = {
                    'lon': float(values[0]),
                    'lat': float(values[1]),
                    'elevation_m': float(values[2]),
                    'horizontal_path': float(values[3]),
                    'true_speed_ms': float(values[4])
                }
                self.last_receive_time = time.time()
                self._update_position_data()
                return True
        except (ValueError, IndexError) as e:
            log(f"⚠ Failed to parse XGPS: {e}")
        return False

    def parse_xatt(self, data):
        """Parse XATT message: Heading, pitch, roll, P/Q/R, speeds, g-loads"""
        try:
            values = data.decode('utf-8', errors='ignore').strip('\x00').split(',')
            if len(values) >= 12:
                self.xatt_data = {
                    'heading': float(values[0]),
                    'pitch': float(values[1]),
                    'roll': float(values[2]),
                    'p_rad': float(values[3]),
                    'q_rad': float(values[4]),
                    'r_rad': float(values[5]),
                    'speed_e_ms': float(values[6]),  # East
                    'speed_u_ms': float(values[7]),  # Up
                    'speed_s_ms': float(values[8]),  # South
                    'g_side': float(values[9]),
                    'g_normal': float(values[10]),
                    'g_axial': float(values[11])
                }
                self.last_receive_time = time.time()
                self._update_position_data()
                return True
        except (ValueError, IndexError) as e:
            log(f"⚠ Failed to parse XATT: {e}")
        return False

    def _update_position_data(self):
        """Combine XGPS and XATT data into position_data format matching original tracker"""
        if not self.xgps_data:
            return

        # Calculate ground speed from XGPS true speed (m/s to knots)
        ground_speed_kts = self.xgps_data['true_speed_ms'] * 1.94384

        # Build position data
        self.position_data = {
            'lat': round(self.xgps_data['lat'], 6),
            'lon': round(self.xgps_data['lon'], 6),
            'altitude': round(self.xgps_data['elevation_m'] * 3.28084, 0),  # meters to feet
            'heading': round(self.xgps_data['horizontal_path'], 1),
            'speed': round(ground_speed_kts, 1),
        }

        # Add XATT data if available
        if self.xatt_data:
            self.position_data['pitch'] = round(self.xatt_data['pitch'], 1)
            self.position_data['roll'] = round(self.xatt_data['roll'], 1)

            # Calculate vertical speed from up component (m/s to ft/min)
            vertical_speed_fpm = self.xatt_data['speed_u_ms'] * 196.85
            self.position_data['vertical_speed'] = round(vertical_speed_fpm, 0)

    def get_position(self, max_age=5.0):
        """Get current position data (returns None if data is older than max_age seconds)"""
        if self.position_data and self.last_receive_time > 0:
            age = time.time() - self.last_receive_time
            if age <= max_age:
                return {
                    **self.position_data,
                    'timestamp': time.time()
                }
        return None

    def receive(self):
        """Receive one UDP packet"""
        try:
            data, _addr = self.sock.recvfrom(4096)

            # Check for message type (first 4 chars, followed by null)
            if len(data) < 6:
                return False

            msg_type = data[:4].decode('utf-8', errors='ignore')
            payload = data[6:]  # Skip "XXXX\0\0"

            if msg_type == 'XGPS':
                return self.parse_xgps(payload)
            elif msg_type == 'XATT':
                return self.parse_xatt(payload)
            elif msg_type == 'XTRA':
                # Ignore XTRA (other aircraft) for now
                return False

            return False

        except socket.timeout:
            return False
        except Exception as e:  # pylint: disable=broad-exception-caught
            log(f"⚠ Error receiving data: {e}")
            return False

    def stop(self):
        """Stop receiving position updates"""
        if self.sock:
            self.sock.close()


def get_api_key(config_file):
    def clean_key(raw_key):
        # Convert to uppercase, strip whitespace (including newlines), remove hyphens
        return raw_key.upper().strip().replace('-', '').replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')

    api_key = clean_key(BAD_API_KEY)
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            api_key = clean_key(f.read())
    except Exception:  # pylint: disable=broad-exception-caught
        # On any error, leave api_key as 'your-api-key'
        pass

    if api_key == clean_key(BAD_API_KEY):
        log("ERROR: Please configure your API_KEY")
        log(f"Edit the file {config_file}, so it contains only the key value.")
        log()
        log("To get an API key:")
        log("1. Visit https://maps.avnwx.com")
        log("2. Click 'Track My Aircraft'")
        log("3. Copy value of displayed API-key from side panel.")
        sys.exit(1)

    return api_key


def stream_to_server():
    """Main loop: receive X-Plane UDP broadcast data and stream to server"""
    log("INFO: stream_to_server started")

    if sys.stdin and sys.stdin.isatty():
        # ... if run from command line
        config_file = 'api-key.txt'
    else:
        config_file = os.path.join(os.path.dirname(__file__), 'api-key.txt')
    api_key = get_api_key(config_file)
    server_url = SERVER_URL

    # Set up signal handler for graceful termination
    def signal_handler(signum, _frame):
        sig_name = signal.Signals(signum).name
        log(f"INFO: Received {sig_name} signal - initiating graceful shutdown")
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start UDP receiver
    receiver = XPlaneUDPReceiver()
    receiver.start()
    log("INFO: receiver started")

    last_upload = 0.0
    last_no_data_log = time.time()
    upload_interval = 1.0  # Upload every second
    no_data_log_interval = 60.0  # Log "still listening" every 60 seconds if no data
    log_counter = 0  # Counter for logging every 10th position

    log("Waiting for X-Plane UDP broadcast data...")
    log(f"Will post to {server_url} with key {api_key}")
    log("-" * 60)

    try:
        while True:
            # Receive UDP packets
            received = receiver.receive()

            current_time = time.time()

            # Log if no data received for a while
            if current_time - receiver.last_receive_time > no_data_log_interval:
                if current_time - last_no_data_log >= no_data_log_interval:
                    log("⏱ Still listening for X-Plane UDP broadcasts (no data received yet)...")
                    last_no_data_log = current_time

            # Upload to server at regular intervals
            if current_time - last_upload >= upload_interval:
                position = receiver.get_position()

                if position:
                    try:
                        response = requests.post(
                            server_url,
                            json={'api_key': api_key, 'position': position},
                            timeout=5
                        )

                        if response.status_code == 200:
                            # Log only every 10th position to reduce log file size (1st, 11th, 21st, etc.)
                            log_counter = (log_counter % 10) + 1
                            if log_counter == 1:
                                # Build status line
                                status = (f"✓ {position['lat']:.4f}, {position['lon']:.4f} | "
                                          f"{position['altitude']:.0f}ft")

                                if 'altitude_agl' in position:
                                    status += f" ({position['altitude_agl']:.0f}ft AGL)"

                                status += f" | {position['heading']:.0f}° | {position['speed']:.0f}kts"

                                if 'vertical_speed' in position and abs(position['vertical_speed']) > 50:
                                    vs_sign = "↑" if position['vertical_speed'] > 0 else "↓"
                                    status += f" | {vs_sign}{abs(position['vertical_speed']):.0f}fpm"

                                log(status)
                        else:
                            log(f"✗ Upload failed: {response.status_code}")

                    except requests.exceptions.RequestException as e:
                        log(f"✗ Network error: {e}")

                    last_upload = current_time
                else:
                    if received:
                        log("⚠ Waiting for valid position data from X-Plane...")

    except KeyboardInterrupt:
        log("\nStopping...")
    finally:
        # Stop receiving on exit
        receiver.stop()
        log("Stopped listening for X-Plane UDP broadcasts")


if __name__ == '__main__':
    # It's possible to run this manually, rather than using PI_AvnWx.py.
    # The benefit of PI_AvnWx.py will automatically start/stop the process.
    print("X-Plane Aircraft Tracker (UDP Broadcast Version)")
    print("=" * 60)
    print(f"Server: {SERVER_URL}")
    print()

    try:
        stream_to_server()
    except KeyboardInterrupt:
        print("\nStopping aircraft tracker...")
        sys.exit(0)
