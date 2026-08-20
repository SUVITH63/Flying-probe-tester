"""
Unit tests for FPTester KiCad S-Expression Parser and Test Plan Generator
"""
import unittest
import os
import sys

# Ensure host directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from parser.kicad_parser import KiCadPCBParser
from parser.gerber_parser import GerberParser
from parser.test_plan_gen import TestPlanGenerator
from parser.workspace import WorkspaceValidator

SAMPLE_KICAD_PCB = """(kicad_pcb (version 20211014) (generator pcbnew)
  (net 0 "")
  (net 1 "GND")
  (net 2 "+3V3")

  (footprint "Resistor_SMD:R_0805_2012Metric" (at 20.0 50.0 90.0)
    (property "Reference" "R1")
    (property "Value" "10k")
    (pad "1" smd rect (at -1.0 0.0 90.0) (size 1.0 1.2) (layers "F.Cu") (net 1 "GND"))
    (pad "2" smd rect (at 1.0 0.0 90.0) (size 1.0 1.2) (layers "F.Cu") (net 2 "+3V3"))
  )

  (footprint "Capacitor_SMD:C_0805_2012Metric" (at 40.0 50.0 0.0)
    (property "Reference" "C1")
    (property "Value" "100nF")
    (pad "1" smd rect (at -1.0 0.0 0.0) (size 1.0 1.2) (layers "F.Cu") (net 1 "GND"))
    (pad "2" smd rect (at 1.0 0.0 0.0) (size 1.0 1.2) (layers "F.Cu") (net 2 "+3V3"))
  )
)"""

SAMPLE_GERBER = """%MOIN*%
%FSLAX24Y24*%
%ADD10C,0.0500*%
D10*
X020000Y050000D03*
X040000Y050000D03*
M02*"""

class TestHostParser(unittest.TestCase):
    def test_kicad_parser_pads_and_rotation(self):
        parser = KiCadPCBParser()
        board = parser.parse_string(SAMPLE_KICAD_PCB, board_name="Test_Board")

        self.assertEqual(board.name, "Test_Board")
        self.assertEqual(len(board.components), 2)
        self.assertEqual(len(board.pads), 4)

        # C1 pad 1 is centered relative to board center (30.5mm)
        c1_pad1 = next(p for p in board.pads if p.pad_id == "C1-1")
        self.assertAlmostEqual(c1_pad1.x, 8.5, places=3)
        self.assertAlmostEqual(c1_pad1.y, 57.5, places=3)
        self.assertEqual(c1_pad1.net_name, "GND")

        # R1 footprint is at (20.0, 50.0)
        r1_pad1 = next(p for p in board.pads if p.pad_id == "R1-1")
        self.assertEqual(r1_pad1.net_name, "GND")

    def test_test_plan_generator(self):
        parser = KiCadPCBParser()
        board = parser.parse_string(SAMPLE_KICAD_PCB)

        generator = TestPlanGenerator()
        job = generator.generate_test_plan(board, job_id=101)

        self.assertEqual(job.job_id, 101)
        self.assertGreaterEqual(len(job.test_pairs), 2)  # GND continuity and +3V3 continuity

        hw_cmd = job.test_pairs[0].to_hardware_command(101)
        self.assertEqual(hw_cmd["msg_type"], "run_test")
        self.assertEqual(hw_cmd["job_id"], 101)
        self.assertEqual(len(hw_cmd["arms"]), 2)

    def test_gerber_parser(self):
        parser = GerberParser()
        board = parser.parse_string(SAMPLE_GERBER, board_name="Test_Gerber")

        self.assertEqual(len(board.pads), 2)
        self.assertAlmostEqual(board.pads[0].x, -25.4, places=3)  # Centered around (0, 57.5)
        self.assertAlmostEqual(board.pads[0].y, 57.5, places=3)

    def test_workspace_validator(self):
        validator = WorkspaceValidator()

        # Point near workspace center: (0, 57.5)
        self.assertTrue(validator.is_reachable(0, 0.0, 57.5))
        # Point way outside reach: (300, 300)
        self.assertFalse(validator.is_reachable(0, 300.0, 300.0))

if __name__ == "__main__":
    unittest.main()

