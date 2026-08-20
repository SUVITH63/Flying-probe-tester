"""
Integration tests for OpenFPT FastAPI Server, AI Planner, and Serial Dispatcher
"""
import unittest
import os
import sys

# Ensure host directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from parser.kicad_parser import KiCadPCBParser
from parser.ai_planner import AITestPlanner
from parser.serial_dispatcher import SerialDispatcher
from parser.workspace import WorkspaceValidator

SAMPLE_KICAD_PCB = """(kicad_pcb (version 20211014) (generator pcbnew)
  (net 0 "")
  (net 1 "GND")
  (net 2 "+3V3")
  (net 3 "SDA")

  (footprint "Resistor_SMD:R_0805_2012Metric" (at -2.0 57.5 0.0)
    (property "Reference" "R1")
    (property "Value" "10k")
    (pad "1" smd rect (at -0.5 0.0 0.0) (size 1.0 1.2) (layers "F.Cu") (net 3 "SDA"))
    (pad "2" smd rect (at 0.5 0.0 0.0) (size 1.0 1.2) (layers "F.Cu") (net 2 "+3V3"))
  )

  (footprint "Resistor_SMD:R_0805_2012Metric" (at 2.0 57.5 0.0)
    (property "Reference" "R2")
    (property "Value" "10k")
    (pad "1" smd rect (at -0.5 0.0 0.0) (size 1.0 1.2) (layers "F.Cu") (net 3 "SDA"))
    (pad "2" smd rect (at 0.5 0.0 0.0) (size 1.0 1.2) (layers "F.Cu") (net 2 "+3V3"))
  )
)"""

class TestAPIServerAndAI(unittest.TestCase):
    def test_ai_planner(self):
        parser = KiCadPCBParser()
        board = parser.parse_string(SAMPLE_KICAD_PCB)

        planner = AITestPlanner()
        job = planner.generate_plan(board, job_id=202)

        self.assertEqual(job.job_id, 202)
        self.assertGreater(len(job.test_pairs), 0)

        first_test = job.test_pairs[0]
        self.assertIn(first_test.net_name, ["+3V3", "SDA"])
        self.assertGreaterEqual(first_test.expected_min_v, 1.8)

    def test_serial_dispatcher_simulation(self):
        dispatcher = SerialDispatcher(port="SIMULATED_COM1")
        self.assertTrue(dispatcher.connect())

        cmd = {
            "msg_type": "run_test",
            "job_id": 202,
            "test_params": {"tx_high_time_ms": 100},
            "meta": {"test_id": 1, "expected_min_v": 3.0}
        }

        res = dispatcher.send_test_command(cmd)
        self.assertEqual(res["status"], "done")
        self.assertEqual(res["result"]["verdict"], "PASS")
        self.assertGreaterEqual(res["result"]["adc_voltage"], 3.0)

        dispatcher.disconnect()

    def test_serial_ports_listing(self):
        ports = SerialDispatcher.list_available_ports()
        self.assertGreater(len(ports), 0)

if __name__ == "__main__":
    unittest.main()
