"""python -m earnings --start 2024-04-01 --end 2024-04-15 --out earnings.csv"""

import sys

from earnings.cli import main

if __name__ == "__main__":
    sys.exit(main())
