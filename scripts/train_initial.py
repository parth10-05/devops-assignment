import os, sys
from pathlib import Path

_ML = Path(__file__).resolve().parents[1] / "ml"
if str(_ML) not in sys.path:
    sys.path.insert(0, str(_ML))

from triage_ml.train import main

if __name__ == "__main__":
    out = _ML.parent / "artifacts"
    out.mkdir(parents=True, exist_ok=True)
    main(["--out", str(out), "--no-mlflow"])
    print(f"[+] Baseline model artifacts saved to {out}")
