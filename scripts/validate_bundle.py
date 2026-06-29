"""
CLI tool to validate any OKF bundle directory for spec compliance.
Usage: python scripts/validate_bundle.py <path-to-bundle>
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.okf_validator import OKFValidator


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_bundle.py <bundle-path>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isdir(path):
        print(f"Error: not a directory: {path}")
        sys.exit(1)

    validator = OKFValidator()
    result = validator.validate_bundle(path)

    print(f"\nOKF Bundle Validation Results for: {path}")
    print(f"{'='*60}")
    print(f"  Valid:     {'YES' if result.is_valid else 'NO'}")
    print(f"  Errors:    {len(result.errors)}")
    print(f"  Warnings:  {len(result.warnings)}")
    print()

    if result.errors:
        print("  ERRORS:")
        for e in result.errors:
            print(f"    ! {e}")
        print()

    if result.warnings:
        print("  WARNINGS:")
        for w in result.warnings:
            print(f"    ? {w}")
        print()

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
