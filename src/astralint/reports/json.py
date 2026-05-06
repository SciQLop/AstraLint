from pathlib import Path

from ..base import ValidationResultGroup


def generate_json(results: ValidationResultGroup) -> str:
    return results.model_dump_json(indent=2)


def report(results: ValidationResultGroup, dest: Path | None = None):
    """Generate and optionally save a JSON report."""
    payload = generate_json(results)
    if dest:
        dest.write_text(payload)
        print(f"JSON report saved to: {dest}")
    else:
        print(payload)
