from datetime import datetime, timedelta
from .attendance import Attendance
from .exception import ZKNetworkError

class ZK(object):
    def __init__(self, ip, port=4370, password=0, **kwargs):
        self.ip = ip
        self.port = port
        self.password = password

    def connect(self):
        # 1. Simulate a Basic Connection Failure
        if self.ip == '10.0.0.1':
            print(f"--- MOCK ZK: Simulating Connection Failure for {self.ip} ---")
            return False  # Returning False triggers the "Connection Failed" logic
            
        # 2. Simulate a Network Timeout / Crash
        if self.ip == '10.0.0.2':
            print(f"--- MOCK ZK: Simulating Network Timeout for {self.ip} ---")
            raise ZKNetworkError(f"Network Timeout: Could not reach device at {self.ip}:{self.port} after 60 seconds.")

        # 3. Simulate Success for any other IP
        print(f"--- MOCK ZK: Successfully Connected to {self.ip}:{self.port} ---")
        return self

    def disconnect(self):
        print("--- MOCK ZK: Disconnected ---")
        return True

    def disable_device(self):
        return True

    def enable_device(self):
        return True

    def get_users(self):
        return []

    def get_attendance(self):
        print("--- MOCK ZK: Fetching Fake Attendance Logs ---")
        now = datetime.now()
        
        return [
            Attendance(user_id='101', timestamp=now - timedelta(hours=4), status=0, punch=0, uid=1),
            Attendance(user_id='101', timestamp=now, status=1, punch=1, uid=1),
            Attendance(user_id='102', timestamp=now - timedelta(hours=3), status=0, punch=0, uid=2),
        ]