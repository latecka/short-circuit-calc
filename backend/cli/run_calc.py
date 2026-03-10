#!/usr/bin/env python3
"""CLI runner for short-circuit calculations.

Usage:
    python cli/run_calc.py input.json [-o output.json] [--staging] [--confirm]
"""
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Run IEC 60909-0 short-circuit calculation"
    )
    parser.add_argument("input", help="Input JSON file with network definition")
    parser.add_argument("-o", "--output", help="Output JSON file for results")
    parser.add_argument(
        "--staging", action="store_true", help="Validate input without running calculation"
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Confirm staged calculation"
    )
    
    args = parser.parse_args()
    
    # TODO: Implement calculation logic
    print(f"CLI runner placeholder - input: {args.input}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
