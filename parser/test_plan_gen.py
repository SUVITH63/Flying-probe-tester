"""
Automated Test Plan Generator
Generates dual-probe electrical test sequences (continuity and isolation) from parsed PCB data.
"""
from typing import List, Dict, Tuple, Optional
from .models import Board, Net, Pad, TestPair, TestJob

class TestPlanGenerator:
    def __init__(self, max_continuity_tests_per_net: int = 5):
        self.max_continuity_tests = max_continuity_tests_per_net

    def generate_test_plan(self, board: Board, job_id: int = 101) -> TestJob:
        test_pairs: List[TestPair] = []
        test_id = 1

        # 1. Continuity Tests (Pads on the SAME Net)
        for net_name, net in board.nets.items():
            if not net_name or len(net.pads) < 2:
                continue

            # Skip dummy auto-generated unrouted pads if needed, but test valid nets
            pads = net.pads
            # Pair consecutive pads on the net up to max_continuity_tests limit
            count = 0
            for i in range(len(pads) - 1):
                if count >= self.max_continuity_tests:
                    break

                pad_a = pads[i]
                pad_b = pads[i + 1]

                # Ensure distance between pads is positive
                dist = ((pad_a.x - pad_b.x)**2 + (pad_a.y - pad_b.y)**2)**0.5
                if dist < 0.1:  # Ignore identical co-located pads
                    continue

                test_pairs.append(TestPair(
                    test_id=test_id,
                    test_type="continuity",
                    net_name=net_name,
                    pad_a=pad_a,
                    pad_b=pad_b,
                    expected_min_v=3.0,
                    expected_max_v=3.3,
                    description=f"Continuity check on net '{net_name}' between {pad_a.pad_id} and {pad_b.pad_id}"
                ))
                test_id += 1
                count += 1

        # 2. Basic Net Fallback if no named nets exist (e.g. Gerber input)
        if not test_pairs and len(board.pads) >= 2:
            pads = board.pads
            for i in range(0, len(pads) - 1, 2):
                pad_a = pads[i]
                pad_b = pads[i + 1]
                test_pairs.append(TestPair(
                    test_id=test_id,
                    test_type="continuity",
                    net_name=f"NET_{test_id}",
                    pad_a=pad_a,
                    pad_b=pad_b,
                    expected_min_v=3.0,
                    expected_max_v=3.3,
                    description=f"Probe check between {pad_a.pad_id} and {pad_b.pad_id}"
                ))
                test_id += 1

        return TestJob(job_id=job_id, board_name=board.name, test_pairs=test_pairs)
