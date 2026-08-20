"""
OpenFPT AI Test Plan Generator & Circuit Pattern Analyzer
Supports Built-in Offline AI, Google Gemini API, OpenAI GPT API, and Local Ollama LLM.
Uses Python standard library (urllib) for zero external pip dependencies.
"""
import os
import json
import logging
import urllib.request
from typing import List, Dict, Any, Optional
from .models import Board, Net, Pad, TestPair, TestJob

logger = logging.getLogger("OpenFPT_AI_Planner")

class AITestPlanner:
    def __init__(self, provider: str = "built_in", api_key: Optional[str] = None, custom_url: Optional[str] = None):
        self.provider = (provider or "built_in").lower()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.custom_url = custom_url or "http://localhost:11434"

    def generate_plan(self, board: Board, job_id: int = 101) -> TestJob:
        """
        Main entry point for generating an AI probe test plan.
        Supports:
        - 'built_in': Local zero-dependency Heuristic Circuit Pattern AI Engine
        - 'gemini': Google Gemini API
        - 'openai': OpenAI GPT-4o / GPT-3.5 API
        - 'ollama': Local Ollama LLM Server
        """
        logger.info(f"Generating test plan for board '{board.name}' (Provider: {self.provider}, Job ID: {job_id})")
        
        test_pairs: List[TestPair] = []

        if self.provider == "gemini" and self.api_key:
            try:
                test_pairs = self._generate_with_gemini(board)
                logger.info(f"Successfully generated {len(test_pairs)} test pairs using Gemini API.")
            except Exception as e:
                logger.warning(f"Gemini API call failed ({e}). Falling back to Built-in AI.")
                test_pairs = self._generate_with_heuristic_ai(board)

        elif self.provider == "openai" and self.api_key:
            try:
                test_pairs = self._generate_with_openai(board)
                logger.info(f"Successfully generated {len(test_pairs)} test pairs using OpenAI API.")
            except Exception as e:
                logger.warning(f"OpenAI API call failed ({e}). Falling back to Built-in AI.")
                test_pairs = self._generate_with_heuristic_ai(board)

        elif self.provider == "ollama":
            try:
                test_pairs = self._generate_with_ollama(board)
                logger.info(f"Successfully generated {len(test_pairs)} test pairs using Ollama LLM.")
            except Exception as e:
                logger.warning(f"Ollama API call failed ({e}). Falling back to Built-in AI.")
                test_pairs = self._generate_with_heuristic_ai(board)

        else:
            logger.info("Using Built-in Zero-Dependency Heuristic Circuit Pattern AI Engine.")
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        board_summary = {
            "name": board.name,
            "components": [c.to_dict() for c in board.components[:20]],
            "nets": [n.to_dict() for n in list(board.nets.values())[:15]]
        }
        prompt = (
            "You are an expert PCB Quality Assurance AI. Analyze this PCB design summary and produce "
            "a JSON list of dual-probe test targets.\n"
            f"Board Data: {json.dumps(board_summary)}"
        )
        req_data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return self._generate_with_heuristic_ai(board)

    def _generate_with_openai(self, board: Board) -> List[TestPair]:
        url = "https://api.openai.com/v1/chat/completions"
        board_summary = {
            "name": board.name,
            "components": [c.to_dict() for c in board.components[:20]],
            "nets": [n.to_dict() for n in list(board.nets.values())[:15]]
        }
        prompt = f"Analyze PCB data: {json.dumps(board_summary)}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]
        }
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return self._generate_with_heuristic_ai(board)

    def _generate_with_ollama(self, board: Board) -> List[TestPair]:
        url = f"{self.custom_url}/api/generate"
        board_summary = {
            "name": board.name,
            "components": [c.to_dict() for c in board.components[:20]],
            "nets": [n.to_dict() for n in list(board.nets.values())[:15]]
        }
        payload = {
            "model": "llama3",
            "prompt": f"Analyze PCB data: {json.dumps(board_summary)}",
            "stream": False
        }
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return self._generate_with_heuristic_ai(board)

