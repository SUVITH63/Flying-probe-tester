"""
FPTester USB Serial Dispatcher
Handles real COM port communication with ESP32 microcontrollers and simulated hardware execution.
"""
import json
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("FPTester_SerialDispatcher")

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.info("pyserial module not installed. Running in Simulated Serial Mode.")

class SerialDispatcher:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.conn = None
        self.is_connected = False

    @staticmethod
    def list_available_ports() -> List[Dict[str, str]]:
        """
        Lists all available USB COM ports on the system.
        """
        if not SERIAL_AVAILABLE:
            return [{"port": "SIMULATED_COM1", "description": "Virtual FPTester Hardware Port (Simulation)"}]

        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append({
                "port": p.device,
                "description": f"{p.description} ({p.hwid})"
            })
        
        if not ports:
            ports.append({"port": "SIMULATED_COM1", "description": "Virtual FPTester Hardware Port (Simulation)"})
        return ports

    def connect(self) -> bool:
        if not self.port or self.port == "SIMULATED_COM1" or not SERIAL_AVAILABLE:
            self.is_connected = True
            logger.info("Connected to SIMULATED_COM1 hardware port.")
            return True

        try:
            self.conn = serial.Serial(self.port, self.baudrate, timeout=2.0)
            self.is_connected = True
            logger.info(f"Connected to physical COM port: {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to COM port {self.port}: {e}")
            self.is_connected = False
            return False

    def send_test_command(self, cmd_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a single JSON test command to the ESP32 and waits for JSON response.
        """
        msg_str = json.dumps(cmd_dict) + "\n"

        if not self.conn or not SERIAL_AVAILABLE or self.port == "SIMULATED_COM1":
            # Simulated Hardware Execution
            time.sleep(0.15)  # Simulate 150ms arm move & measurement time
            # Compute simulated ADC reading based on expected voltage in command meta
            expected_min = cmd_dict.get("meta", {}).get("expected_min_v", 3.0)
            sim_voltage = round(expected_min + 0.05, 3)
            sim_adc = int((sim_voltage / 3.3) * 4095)

            return {
                "msg_type": "test_result",
                "job_id": cmd_dict.get("job_id", 101),
                "test_id": cmd_dict.get("meta", {}).get("test_id", 1),
                "status": "done",
                "result": {
                    "adc_raw": sim_adc,
                    "adc_voltage": sim_voltage,
                    "verdict": "PASS" if sim_voltage >= expected_min else "FAIL"
                }
            }

        # Physical Hardware Execution over USB Serial
        try:
            self.conn.write(msg_str.encode('utf-8'))
            self.conn.flush()
            line = self.conn.readline().decode('utf-8').strip()
            if line:
                return json.loads(line)
            else:
                return {"status": "error", "message": "Serial timeout waiting for response from ESP32."}
        except Exception as e:
            return {"status": "error", "message": f"Serial communication failure: {str(e)}"}

    def disconnect(self):
        if self.conn and self.conn.is_open:
            self.conn.close()
        self.is_connected = False
