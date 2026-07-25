"""PyInstaller entry point for LendOps Studio (see LendOps.spec)."""

from lendops.app import main

if __name__ == "__main__":
    raise SystemExit(main())
