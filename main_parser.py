"""
FPTester Main Parser CLI
Parses KiCad PCB or Gerber files and outputs JSON hardware test plans.
Usage:
    python main_parser.py --input board.kicad_pcb --output test_plan.json
"""
import argparse
import json
import os
import sys
from parser.kicad_parser import KiCadPCBParser
from parser.gerber_parser import GerberParser
from parser.test_plan_gen import TestPlanGenerator
from parser.workspace import WorkspaceValidator

def main():
    parser = argparse.ArgumentParser(description="FPTester PCB Pad Coordinate Parser & Test Plan Generator")
    parser.add_argument("--input", "-i", required=True, help="Path to .kicad_pcb or .gbr file")
    parser.add_argument("--output", "-o", default="test_plan.json", help="Path to output JSON test plan")
    parser.add_argument("--job-id", type=int, default=101, help="Job ID for test execution")

    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    print(f"[*] Parsing input design file: {input_path}")
    
    if input_path.endswith('.kicad_pcb'):
        pcb_parser = KiCadPCBParser()
        board = pcb_parser.parse_file(input_path)
    elif input_path.endswith('.gbr') or input_path.endswith('.pho'):
        pcb_parser = GerberParser()
        board = pcb_parser.parse_file(input_path)
    else:
        # Fallback to KiCad attempt
        try:
            pcb_parser = KiCadPCBParser()
            board = pcb_parser.parse_file(input_path)
        except Exception:
            pcb_parser = GerberParser()
            board = pcb_parser.parse_file(input_path)

    print(f"[+] Board Name: {board.name}")
    print(f"[+] Total Pads Extracted: {len(board.pads)}")
    print(f"[+] Total Components Extracted: {len(board.components)}")
    print(f"[+] Total Nets Identified: {len(board.nets)}")

    # Generate Test Plan
    print("[*] Generating dual-arm probe test plan...")
    generator = TestPlanGenerator()
    job = generator.generate_test_plan(board, job_id=args.job_id)

    # Validate Workspace Reachability
    validator = WorkspaceValidator()
    valid_test_pairs = []
    skipped_count = 0

    for tp in job.test_pairs:
        ok, msg = validator.validate_pad_pair(tp.pad_a, tp.pad_b)
        if ok:
            valid_test_pairs.append(tp)
        else:
            skipped_count += 1
            print(f"[!] Warning: Skipping test pair {tp.test_id} ({tp.net_name}): {msg}")

    job.test_pairs = valid_test_pairs
    print(f"[+] Total Valid Reachable Tests: {len(job.test_pairs)} (Skipped out-of-reach: {skipped_count})")

    # Output JSON
    output_dict = job.to_dict()
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_dict, f, indent=2)

    print(f"[SUCCESS] Hardware JSON test plan exported to: {args.output}")

if __name__ == "__main__":
    main()
