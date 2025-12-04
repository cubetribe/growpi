"""
Allow running grow_pi as a module:
    python -m grow_pi
"""

from .main import main
import sys

if __name__ == "__main__":
    sys.exit(main())
