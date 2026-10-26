import json
import logging
import threading
import time
from dataclasses import dataclass

import joblib
import numpy as np

from app.settings import Settings
from app.text import build_text, feature_frame

log = logging.getLogger(__name__)
RETRY_SECONDS = 30


@dataclass
class LoadedModel:
    classifier: object
    encoder: object
    version: str
    encoder_name: str

    def predict(self, subject: str | None, body: str) -> dict:
        text = build_text(subject, body)
        x = feature_frame([text], self.encoder.encode([text], normalize_embeddings=True))
        proba = self.classifier.predict_proba(x)[0]
        top = np.argsort(proba)[::-1][:3]
        top_k = [{"label": str(self.classifier.classes_[i]), "score": float(proba[i])} for i in top]
        return {
            "label": top_k[0]["label"],
            "confidence": top_k[0]["score"],
            "top_k": top_k,
            "model_version": self.version,
        }


class ModelHolder:
    model: LoadedModel | None = None


def load(settings: Settings) -> LoadedModel:
    from pathlib import Path
    from sentence_transformers import SentenceTransformer

    local_dir = Path(settings.local_artifacts_dir)
    if not ((local_dir / "classifier.joblib").exists() and (local_dir / "metadata.json").exists()):
        raise FileNotFoundError(f"Model artifacts missing in {local_dir}")

    log.info("loading model from %s", local_dir)
    with open(local_dir / "metadata.json") as fh:
        meta = json.load(fh)
    classifier = joblib.load(local_dir / "classifier.joblib")
    kw = {"device": "cpu", "revision": meta["encoder_revision"]}
    try:
        encoder = SentenceTransformer(meta["encoder"], model_kwargs={"local_files_only": True}, tokenizer_kwargs={"local_files_only": True}, **kw)
    except Exception:
        encoder = SentenceTransformer(meta["encoder"], **kw)
    return LoadedModel(classifier, encoder, meta.get("trained_at", "local-model"), meta["encoder"])


def load_in_background(holder: ModelHolder, settings: Settings) -> threading.Thread:
    def worker() -> None:
        while holder.model is None:
            try:
                holder.model = load(settings)
                log.info("model loaded", extra={"model_version": holder.model.version})
            except Exception as e:  # keep retrying: HF may be briefly unreachable
                log.warning("model load failed, retrying", extra={"error": type(e).__name__})
                time.sleep(RETRY_SECONDS)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread
