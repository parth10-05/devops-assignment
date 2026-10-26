import argparse, json, os, sys
from datetime import UTC, datetime
from pathlib import Path

_ML = Path(__file__).resolve().parents[1] / "ml"
if str(_ML) not in sys.path:
    sys.path.insert(0, str(_ML))

import pandas as pd, psycopg
from psycopg.types.json import Jsonb
from triage_ml.config import PROCESSED, ROOT
from triage_ml.export_feedback import snapshot
from triage_ml.train import run, sentence_embedder, split_feedback, stratified_sample


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db-url", default=f"postgresql://triageiq:postgres@localhost:{os.getenv('POSTGRES_PORT', '5433')}/triageiq")
    p.add_argument("--out", type=Path, default=ROOT / "artifacts")
    p.add_argument("--min-rows", type=int, default=1)
    p.add_argument("--sample", type=int, default=300)
    args = p.parse_args()

    with psycopg.connect(args.db_url) as conn:
        cutoff, fb_df = snapshot(conn)
        if len(fb_df) < args.min_rows:
            print(f"[-] {len(fb_df)} reviews found (min {args.min_rows}). Review tickets at http://localhost:8085")
            return 0

        train_df, val_df, golden_df = (pd.read_parquet(PROCESSED / f"{s}.parquet") for s in ("train", "val", "golden"))
        if args.sample:
            train_df, val_df, golden_df = (stratified_sample(d, args.sample) for d in (train_df, val_df, golden_df))

        fb_train, fb_holdout = split_feedback(fb_df)
        train_df = pd.concat([train_df[["text", "label"]], fb_train[["text", "label"]]])
        args.out.mkdir(parents=True, exist_ok=True)
        fb_holdout.to_parquet(args.out / "feedback_holdout.parquet", index=False)

        meta = run(train_df, val_df, golden_df, sentence_embedder(), args.out, {"dataset_revision": "local", "feedback_rows": len(fb_df), "cutoff_id": cutoff})
        ver = f"local-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        meta["model_version"] = ver
        (args.out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        with conn.transaction():
            conn.execute("UPDATE model_versions SET status = 'retired' WHERE status = 'production'")
            conn.execute("INSERT INTO model_versions (model_version, hf_repo, eval_metrics, status, promoted_at) VALUES (%s, 'local', %s, 'production', now())", (ver, Jsonb(meta["metrics"])))

    print(f"[+] Retrained {ver} | Accuracy: {meta['metrics']['golden_accuracy']:.3f} | Macro-F1: {meta['metrics']['golden_macro_f1']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
