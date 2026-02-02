import os
import json
import hashlib
from typing import Optional, Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from elasticsearch import Elasticsearch
from openai import OpenAI

load_dotenv()

ELASTIC_URL = os.getenv("ELASTIC_URL", "http://localhost:9200")
INDEX_NAME = os.getenv("ELASTIC_INDEX", "phrases_openai")

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "fake").strip().lower()
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "64"))

app = FastAPI(title="FastAPI + Elasticsearch (Lexical / Semantic / Hybrid)")

es = Elasticsearch(ELASTIC_URL)

# ---------- Requests ----------
class IngestRequest(BaseModel):
    frases: list[str] = Field(..., min_length=1)
    metadatos: Optional[dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class UpdateRequest(BaseModel):
    text: Optional[str] = None
    metadatos: Optional[dict[str, Any]] = None

# ---------- Embeddings ----------
def fake_embed(text: str) -> list[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    b = h * ((EMBEDDING_DIM * 4 // len(h)) + 1)
    for i in range(EMBEDDING_DIM):
        chunk = b[i * 4:(i + 1) * 4]
        n = int.from_bytes(chunk, "little", signed=False)
        vec.append((n % 100000) / 100000.0)
    return vec

def openai_embed(text: str) -> list[float]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta OPENAI_API_KEY en el .env")

    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(
        model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        input=text
    )
    vec = resp.data[0].embedding
    if len(vec) != EMBEDDING_DIM:
        raise HTTPException(
            status_code=500,
            detail=f"Dimensión embedding ({len(vec)}) != EMBEDDING_DIM ({EMBEDDING_DIM})"
        )
    return vec

def embed(text: str) -> list[float]:
    if EMBEDDING_PROVIDER == "openai":
        return openai_embed(text)
    return fake_embed(text)

# ---------- Elasticsearch helpers ----------
def ensure_index():
    if es.indices.exists(index=INDEX_NAME):
        return

    # Mapping: text para lexical + dense_vector para semántica
    # Vector search en Elasticsearch se hace con dense_vector + knn. :contentReference[oaicite:4]{index=4}
    mapping = {
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "meta": {"type": "object", "enabled": True},
                "embedding": {
                    "type": "dense_vector",
                    "dims": EMBEDDING_DIM,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }

    es.indices.create(index=INDEX_NAME, **mapping)

@app.on_event("startup")
def startup():
    # Comprobar conexión
    if not es.ping():
        raise RuntimeError(f"No puedo conectar con Elasticsearch en {ELASTIC_URL}")
    ensure_index()

# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {
        "ok": True,
        "elastic": ELASTIC_URL,
        "index": INDEX_NAME,
        "dim": EMBEDDING_DIM,
        "embedding_provider": EMBEDDING_PROVIDER
    }

@app.post("/index/create")
def create_index():
    ensure_index()
    return {"ok": True, "index": INDEX_NAME, "dim": EMBEDDING_DIM}

@app.post("/ingest")
def ingest(req: IngestRequest):
    ensure_index()

    meta = req.metadatos or {}
    ids = []

    for text in req.frases:
        doc_id = str(uuid4())
        vec = embed(text)
        doc = {
            "text": text,
            "meta": meta,
            "embedding": vec
        }
        es.index(index=INDEX_NAME, id=doc_id, document=doc)
        ids.append(doc_id)

    es.indices.refresh(index=INDEX_NAME)
    return {"ok": True, "inserted_count": len(ids), "ids": ids}

@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    try:
        es.delete(index=INDEX_NAME, id=doc_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    es.indices.refresh(index=INDEX_NAME)
    return {"ok": True, "deleted_id": doc_id}

@app.put("/documents/{doc_id}")
def update_document(doc_id: str, req: UpdateRequest):
    # obtener doc actual
    try:
        current = es.get(index=INDEX_NAME, id=doc_id)["_source"]
    except Exception:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    new_text = req.text if req.text is not None else current["text"]
    new_meta = req.metadatos if req.metadatos is not None else current.get("meta", {})

    new_vec = embed(new_text)

    es.index(
        index=INDEX_NAME,
        id=doc_id,
        document={"text": new_text, "meta": new_meta, "embedding": new_vec}
    )
    es.indices.refresh(index=INDEX_NAME)
    return {"ok": True, "id": doc_id, "text": new_text}

@app.post("/search/lexical")
def search_lexical(req: SearchRequest):
    q = req.query
    res = es.search(
        index=INDEX_NAME,
        size=req.top_k,
        query={"match": {"text": q}}
    )
    hits = [
        {"id": h["_id"], "text": h["_source"]["text"], "meta": h["_source"].get("meta", {}), "score": h["_score"]}
        for h in res["hits"]["hits"]
    ]
    return {"ok": True, "type": "lexical", "results": hits}

@app.post("/search/semantic")
def search_semantic(req: SearchRequest):
    qvec = embed(req.query)

    # kNN query (approx nearest neighbors). :contentReference[oaicite:5]{index=5}
    res = es.search(
        index=INDEX_NAME,
        size=req.top_k,
        knn={
            "field": "embedding",
            "query_vector": qvec,
            "k": req.top_k,
            "num_candidates": max(req.top_k * 20, 100)
        }
    )
    hits = [
        {"id": h["_id"], "text": h["_source"]["text"], "meta": h["_source"].get("meta", {}), "score": h["_score"]}
        for h in res["hits"]["hits"]
    ]
    return {"ok": True, "type": "semantic", "results": hits}

@app.post("/search/hybrid")
def search_hybrid(req: SearchRequest):
    """
    Hybrid simple: mezcla de resultados BM25 + kNN usando una query que incluye ambos.
    Elastic soporta estrategias de hybrid search y fusión (RRF, etc.). :contentReference[oaicite:6]{index=6}
    Aquí dejamos una versión sencilla que combina ambos en una sola búsqueda.
    """
    qvec = embed(req.query)

    res = es.search(
        index=INDEX_NAME,
        size=req.top_k,
        query={
            "bool": {
                "should": [
                    {"match": {"text": req.query}},
                ]
            }
        },
        knn={
            "field": "embedding",
            "query_vector": qvec,
            "k": req.top_k,
            "num_candidates": max(req.top_k * 20, 100)
        }
    )

    hits = [
        {"id": h["_id"], "text": h["_source"]["text"], "meta": h["_source"].get("meta", {}), "score": h["_score"]}
        for h in res["hits"]["hits"]
    ]
    return {"ok": True, "type": "hybrid", "results": hits}
