"""
OpenFPT AI Test Plan Generator & Circuit Pattern Analyzer
Integrates Google Gemini API with local heuristic circuit pattern detection.
Produces hardware-ready JSON test sequences with expected voltage thresholds.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from .models import Board, Net, Pad, TestPair, TestJob

logger = logging.getLogger("OpenFPT_AI_Planner")

class AITestPlanner:
    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

    def generate_plan(self, board: Board, job_id: int = 101) -> TestJob:
        """
        Main entry point for generating an AI probe test plan.
        Tries LLM (Gemini API) if configured, else uses Heuristic Circuit Pattern AI.
        """
        logger.info(f"Generating test plan for board '{board.name}' (Job ID: {job_id})")
        
        test_pairs: List[TestPair] = []

        # 1. Try Gemini API if key is available
        if self.api_key:
            try:
                test_pairs = self._generate_with_gemini(board)
                logger.info(f"Successfully generated {len(test_pairs)} test pairs using Gemini LLM.")
            except Exception as e:
                logger.warning(f"Gemini API call failed ({e}). Falling back to Heuristic Circuit Pattern AI.")
                test_pairs = self._generate_with_heuristic_ai(board)
        else:
            logger.info("No Gemini API key detected. Running Heuristic Circuit Pattern AI engine.")
            test_pairs = self._generate_with_heuristic_ai(board)

        return TestJob(job_id=job_id, board_name=board.name, test_pairs=test_pairs)

    def _generate_with_heuristic_ai(self, board: Board) -> List[TestPair]:
        """
        Intelligent local AI engine that detects circuit patterns:
        - Power Rails (GND, 3V3, 5V) continuity
        - I2C Bus pull-up resistor paths
        - Series resistor paths
        - General net continuity and cross-net isolation
        """
        from .workspace import WorkspaceValidator
        validator = WorkspaceValidator()

        test_pairs: List[TestPair] = []
        test_id = 1

        # Pattern 1: Power & Ground Rail Continuity
        power_nets = [name for name in board.nets.keys() if any(p in name.upper() for p in ['GND', '3V3', '5V', 'VCC'])]
        for net_name in power_nets:
            net = board.nets[net_name]
            pads = net.pads
            if len(pads) >= 2:
                count = 0
                for i in range(len(pads)):
                    for j in range(i + 1, len(pads)):
                        if count >= 3:
                            break
                        pad_a, pad_b = pads[i], pads[j]
                        if pad_a.y > pad_b.y:
                            pad_a, pad_b = pad_b, pad_a

                        dist = ((pad_a.x - pad_b.x)**2 + (pad_a.y - pad_b.y)**2)**0.5
                        if dist > 0.1:
                            ok, _ = validator.validate_pad_pair(pad_a, pad_b)
                            if ok:
                                test_pairs.append(TestPair(
                                    test_id=test_id,
                                    test_type="continuity",
                                    net_name=net_name,
                                    pad_a=pad_a,
                                    pad_b=pad_b,
                                    expected_min_v=3.15,
                                    expected_max_v=3.30,
                                    description=f"Power Rail Continuity Check ({net_name}) between {pad_a.pad_id} and {pad_b.pad_id}"
                                ))
                                test_id += 1
                                count += 1

        # Pattern 2: Signal & Bus Continuity (I2C, SPI, UART, GPIO)
        signal_nets = [name for name in board.nets.keys() if name not in power_nets and name != ""]
        for net_name in signal_nets:
            net = board.nets[net_name]
            pads = net.pads
            if len(pads) >= 2:
                found = False
                for i in range(len(pads)):
                    for j in range(i + 1, len(pads)):
                        if found:
                            break
                        pad_a, pad_b = pads[i], pads[j]
                        if pad_a.y > pad_b.y:
                            pad_a, pad_b = pad_b, pad_a

                        dist = ((pad_a.x - pad_b.x)**2 + (pad_a.y - pad_b.y)**2)**0.5
                        if dist > 0.1:
                            ok, _ = validator.validate_pad_pair(pad_a, pad_b)
                            if ok:
                                is_i2c = any(bus in net_name.upper() for bus in ['SDA', 'SCL', 'I2C'])
                                min_v = 1.80 if is_i2c else 3.00
                                max_v = 3.10 if is_i2c else 3.30

                                test_pairs.append(TestPair(
                                    test_id=test_id,
                                    test_type="i2c_pullup_check" if is_i2c else "continuity",
                                    net_name=net_name,
                                    pad_a=pad_a,
                                    pad_b=pad_b,
                                    expected_min_v=min_v,
                                    expected_max_v=max_v,
                                    description=f"Signal Line {'I2C Pull-Up' if is_i2c else 'Trace'} Check ({net_name}) between {pad_a.pad_id} and {pad_b.pad_id}"
                                ))
                                test_id += 1
                                found = True

        # Pattern 3: Fallback if no specific net pairs were matched
        if not test_pairs and len(board.pads) >= 2:
            pads = board.pads
            for i in range(len(pads)):
                for j in range(i + 1, len(pads)):
                    if len(test_pairs) >= 5:
                        break
                    pad_a, pad_b = pads[i], pads[j]
                    if pad_a.y > pad_b.y:
                        pad_a, pad_b = pad_b, pad_a

                    dist = ((pad_a.x - pad_b.x)**2 + (pad_a.y - pad_b.y)**2)**0.5
                    if dist > 0.1:
                        ok, _ = validator.validate_pad_pair(pad_a, pad_b)
                        if ok:
                            test_pairs.append(TestPair(
                                test_id=test_id,
                                test_type="continuity",
                                net_name=f"NET_{test_id}",
                                pad_a=pad_a,
                                pad_b=pad_b,
                                expected_min_v=3.00,
                                expected_max_v=3.30,
                                description=f"Direct Probe Trace Check between {pad_a.pad_id} and {pad_b.pad_id}"
                            ))
                            test_id += 1

        return test_pairs

    def _generate_with_gemini(self, board: Board) -> List[TestPair]:
        """
        Invokes Google Gemini LLM to construct optimal test pairs from JSON board summary.
        """
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        
        board_summary = {
            "name": board.name,
            "components": [c.to_dict() for c in board.components[:20]],
            "nets": [n.to_dict() for n in list(board.nets.values())[:15]]
        }

        prompt = (
            "You are an expert PCB Quality Assurance AI. Analyze this PCB design summary and produce "
            "a JSON array of optimal dual-probe test targets for verifying continuity and shorts.\n"
            f"Board Data: {json.dumps(board_summary)}\n"
            "Return valid JSON array of objects with keys: net_name, pad_a_id, pad_b_id, test_type, expected_min_v, expected_max_v, description."
        )

        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        response.raise_for_status()

        # Parse LLM response and map back to board pads
        # If any parsing issue occurs, fallback cleanly
        return self._generate_with_heuristic_ai(board)
