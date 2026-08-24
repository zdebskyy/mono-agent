import numpy as np

import config

_model = None


def model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBED_MODEL)
    return _model


def _encode(texts, prefix):
    vectors = model().encode([f"{prefix}{t}" for t in texts],
                             batch_size=config.EMBED_BATCH,
                             normalize_embeddings=True,
                             show_progress_bar=False)
    return np.asarray(vectors, dtype=np.float32)


def passages(texts):
    return _encode(texts, "passage: ")


def query(text):
    return _encode([text], "query: ")[0]
