#!/usr/bin/env python3
"""CLI runner for short-circuit calculations.

Usage:
    python cli/run_calc.py input.json [-o output.json] [--mode max|min]
    python cli/run_calc.py input.json --staging
    python cli/run_calc.py input.json --confirm

Examples:
    # Run max calculation
    python cli/run_calc.py network.json -o results.json

    # Run min calculation
    python cli/run_calc.py network.json --mode min -o results.json

    # Validate only (staging)
    python cli/run_calc.py network.json --staging

Input JSON format:
{
    "name": "Network name",
    "elements": [...],
    "calculation": {
        "mode": "max",
        "fault_types": ["Ik3", "Ik2", "Ik1"],
        "fault_buses": ["bus1", "bus2"]
    }
}
"""
import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine import (
    Network,
    NetworkValidator,
    CalculationValidator,
    calculate_short_circuit,
)


def load_input(input_path: str) -> dict:
    """Load input JSON file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_output(output_path: str, data: dict) -> None:
    """Save output JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def validate_network(data: dict) -> dict:
    """
    Validate network without running calculation.

    Returns validation report.
    """
    network = Network.from_dict(data)
    validator = NetworkValidator(network)
    result = validator.validate()

    return {
        "status": "valid" if result.is_valid else "invalid",
        "errors": [str(e) for e in result.errors],
        "warnings": [str(w) for w in result.warnings],
        "element_count": len(network.elements),
        "bus_count": len(network.get_elements_by_type(type(list(network._buses.values())[0]))) if network._buses else 0,
    }


def run_calculation(data: dict, mode_override: str = None) -> dict:
    """
    Run short-circuit calculation.

    Args:
        data: Input data with network and calculation parameters
        mode_override: Override calculation mode from command line

    Returns:
        Calculation results
    """
    # Build network
    network = Network.from_dict(data)

    # Get calculation parameters
    calc_params = data.get("calculation", {})
    mode = mode_override or calc_params.get("mode", "max")
    fault_types = calc_params.get("fault_types", ["Ik3"])
    fault_buses = calc_params.get("fault_buses", [])

    # If no fault buses specified, use all buses
    if not fault_buses:
        from app.engine import Busbar
        fault_buses = [b.id for b in network.get_elements_by_type(Busbar)]

    # Run calculation
    run = calculate_short_circuit(
        network=network,
        fault_types=fault_types,
        fault_buses=fault_buses,
        mode=mode
    )

    return run.to_dict()


def main():
    parser = argparse.ArgumentParser(
        description="Run IEC 60909-0 short-circuit calculation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "input",
        help="Input JSON file with network definition"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file for results (default: stdout)"
    )
    parser.add_argument(
        "--mode",
        choices=["max", "min"],
        help="Calculation mode (overrides input file)"
    )
    parser.add_argument(
        "--staging",
        action="store_true",
        help="Validate input without running calculation"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Run calculation (same as default, for staging workflow)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Load input
    try:
        data = load_input(args.input)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        return 1

    # Run validation or calculation
    if args.staging:
        if args.verbose:
            print("Running validation (staging mode)...", file=sys.stderr)

        result = validate_network(data)

        if result["status"] == "valid":
            print("Validation passed.", file=sys.stderr)
        else:
            print("Validation failed.", file=sys.stderr)
            for err in result["errors"]:
                print(f"  ERROR: {err}", file=sys.stderr)

        for warn in result["warnings"]:
            print(f"  WARNING: {warn}", file=sys.stderr)

        # Output validation report
        if args.output:
            save_output(args.output, result)
        else:
            print(json.dumps(result, indent=2))

        return 0 if result["status"] == "valid" else 1

    else:
        # Run calculation
        if args.verbose:
            mode = args.mode or data.get("calculation", {}).get("mode", "max")
            print(f"Running {mode} calculation...", file=sys.stderr)

        try:
            result = run_calculation(data, args.mode)
        except Exception as e:
            print(f"Error: Calculation failed: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

        if not result["is_success"]:
            print("Calculation completed with errors:", file=sys.stderr)
            for err in result["errors"]:
                print(f"  ERROR: {err}", file=sys.stderr)

        # Output results
        if args.output:
            save_output(args.output, result)
            if args.verbose:
                print(f"Results saved to {args.output}", file=sys.stderr)
        else:
            print(json.dumps(result, indent=2))

        # Print summary
        if args.verbose and result["is_success"]:
            print(f"\nCalculation summary:", file=sys.stderr)
            print(f"  Mode: {result['mode']}", file=sys.stderr)
            print(f"  Fault types: {result['fault_types']}", file=sys.stderr)
            print(f"  Results: {len(result['results'])} calculations", file=sys.stderr)

            for r in result["results"]:
                print(
                    f"    {r['fault_type']} @ {r['bus_id']}: "
                    f"Ik = {r['Ik_kA']:.3f} kA, ip = {r['ip_kA']:.3f} kA",
                    file=sys.stderr
                )

        return 0 if result["is_success"] else 1


if __name__ == "__main__":
    sys.exit(main())
