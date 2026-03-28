"""
One-time script to export all ChromaDB documents and embeddings
into a lightweight JSON file for serverless deployment.
"""
import json
import sys
import os

sys.path.append(os.path.dirname(__file__))

from rag import _collection, rag_is_ready

def export():
    if not rag_is_ready():
        print("RAG is not ready. Cannot export.")
        return

    collection = _collection()
    all_data = collection.get(include=["documents", "metadatas", "embeddings"])

    ids = all_data.get("ids", [])
    documents = all_data.get("documents", [])
    metadatas = all_data.get("metadatas", [])
    embeddings = all_data.get("embeddings", [])

    print(f"Exporting {len(ids)} documents...")

    records = []
    for i in range(len(ids)):
        emb = embeddings[i]
        if hasattr(emb, "tolist"):
            emb = emb.tolist()
        records.append({
            "id": ids[i],
            "document": documents[i],
            "metadata": metadatas[i],
            "embedding": emb,
        })

    output_path = os.path.join(os.path.dirname(__file__), "data", "rag_vectors.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Exported {len(records)} records to {output_path} ({size_mb:.1f} MB)")

if __name__ == "__main__":
    export()
