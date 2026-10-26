import sys
from pathlib import Path

_ML = Path(__file__).resolve().parents[1] / "ml"
if str(_ML) not in sys.path:
    sys.path.insert(0, str(_ML))

from triage_ml.prepare import main

if __name__ == "__main__":
    main()
