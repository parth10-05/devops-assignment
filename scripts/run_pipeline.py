"""TriageIQ CI/CD & Automated Retraining Pipeline Runner."""

import json, os, subprocess, sys, time, urllib.request


def format_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s" if m > 0 else f"{seconds:.1f}s"


def print_banner(text: str, char: str = "="):
    line = char * 70
    print(f"\n{line}\n  {text}\n{line}\n", flush=True)


def run_stage(stage_no: int, total_stages: int, title: str, cmd: list[str]) -> float:
    print(f">>> [Stage {stage_no}/{total_stages}] {title} ...", flush=True)
    start = time.perf_counter()
    res = subprocess.run(cmd)
    elapsed = time.perf_counter() - start
    if res.returncode != 0:
        print(f"\n❌ [Stage {stage_no}/{total_stages}] FAILED in {format_duration(elapsed)} (Exit Code: {res.returncode})", flush=True)
        sys.exit(res.returncode)
    print(f"✔ [Stage {stage_no}/{total_stages}] Completed in {format_duration(elapsed)}\n", flush=True)
    return elapsed


def main():
    total_start = time.perf_counter()
    print_banner("TRIAGEIQ AUTOMATED CI/CD & RETRAINING PIPELINE")

    # Stage 1: Pytest Test Suite
    t1 = run_stage(1, 3, "Running Quality & Integration Test Suite (pytest)", [sys.executable, "-m", "pytest", "ml/tests"])

    # Stage 2: Local Retraining
    t2 = run_stage(2, 3, "Retraining Model with Latest Feedback (retrain_local.py)", [sys.executable, "scripts/retrain_local.py", "--min-rows", "1"])

    # Stage 3: Redeployment & Verification
    print(">>> [Stage 3/3] Redeploying Containerized Model Service ...", flush=True)
    start_redeploy = time.perf_counter()
    subprocess.run(["docker", "compose", "restart", "model-service"], check=True)

    # Health check to verify new model
    ver = "unknown"
    for _ in range(10):
        try:
            with urllib.request.urlopen("http://localhost:8002/health", timeout=3) as r:
                data = json.loads(r.read())
                ver = data.get("model_version", "unknown")
                break
        except Exception:
            time.sleep(1)

    t3 = time.perf_counter() - start_redeploy
    print(f"✔ [Stage 3/3] Completed in {format_duration(t3)}")
    print(f"    Active Model Version: {ver} (Serving on http://localhost:8002)\n", flush=True)

    total_time = time.perf_counter() - total_start
    print_banner(f"PIPELINE SUCCESSFUL | Total Duration: {format_duration(total_time)}")
    print(f"  Stage 1 (Test Suite):   {format_duration(t1)}")
    print(f"  Stage 2 (Retraining):   {format_duration(t2)}")
    print(f"  Stage 3 (Redeployment): {format_duration(t3)}")
    print("=" * 70 + "\n", flush=True)


if __name__ == "__main__":
    main()
