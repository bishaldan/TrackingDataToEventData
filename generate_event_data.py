"""Compatibility wrapper for the package-backed CLI."""

from tracking_to_event.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
