import hashlib
import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scraper import fetch_medical_sources

BASE_DIR = Path(__file__).resolve().parent
RAG_DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = RAG_DATA_DIR / "chroma"
MANIFEST_PATH = RAG_DATA_DIR / "rag_manifest.json"
CURATED_SOURCES_PATH = RAG_DATA_DIR / "curated_sources.json"
PAGE_CACHE_DIR = RAG_DATA_DIR / "page_cache"
COLLECTION_NAME = "her_circle_medical_knowledge"
HEADERS = {"User-Agent": "HerCircle/1.0"}

DEFAULT_TOPIC_QUERIES = [
    "late period causes",
    "period cramps severe pain",
    "heavy menstrual bleeding clots",
    "signs of pcos",
    "endometriosis symptoms",
    "what is pmdd",
    "birth control side effects",
    "ovulation and fertility signs",
    "period rash irritation from pads",
    "missed period pregnancy signs",
    "how to make periods lighter safely",
    "how to shorten periods safely",
    "spotting after starting birth control",
    "irregular periods stress hormones",
    "fibroids heavy bleeding symptoms",
    "when to seek care period pain",
    "vaginal discharge normal vs infection",
    "period clots when to worry",
]

TOPIC_KEYWORDS = {
    "periods": ("period", "menstrual", "bleeding", "clots", "cycle", "menstruation", "amenorrhea"),
    "pcos": ("pcos", "polycystic ovary", "androgen", "irregular period"),
    "endometriosis": ("endometriosis", "pelvic pain", "painful periods"),
    "fibroids": ("fibroid", "uterine fibroid"),
    "pmdd": ("pmdd", "premenstrual dysphoric", "pms"),
    "contraception": ("birth control", "contraception", "iud", "implant", "pill", "shot", "ring", "patch"),
    "fertility": ("fertility", "ovulation", "conceive", "pregnant", "pregnancy", "trying to get pregnant"),
    "infection": ("infection", "discharge", "itching", "odor", "rash", "irritation"),
    "urgent": ("severe pain", "heavy bleeding", "fainting", "dizziness", "fever"),
}

ACTION_ORIENTED_TERMS = {
    "what should",
    "how can",
    "how do",
    "how to",
    "reduce",
    "shorten",
    "stop",
    "treat",
    "help",
    "manage",
}

INGEST_EXCLUDED_SOURCES = {
    "Planned Parenthood",
}


def _clean_text(value):
    return " ".join((value or "").split())


def _cache_path(url):
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return PAGE_CACHE_DIR / f"{digest}.txt"


def _structured_cache_path(url):
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return PAGE_CACHE_DIR / f"{digest}.json"


def _safe_import_chroma():
    try:
        import chromadb
        from chromadb.utils import embedding_functions

        return chromadb, embedding_functions
    except Exception:
        return None, None


def rag_dependencies_available():
    chromadb, embedding_functions = _safe_import_chroma()
    return chromadb is not None and embedding_functions is not None


def _embedding_function():
    _, embedding_functions = _safe_import_chroma()
    if embedding_functions is None:
        raise RuntimeError("RAG dependencies are not installed.")

    model_name = os.getenv("HERCIRCLE_EMBED_MODEL", "all-MiniLM-L6-v2")

    try:
        return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
    except Exception:
        return embedding_functions.DefaultEmbeddingFunction()


def _collection():
    chromadb, _ = _safe_import_chroma()
    if chromadb is None:
        raise RuntimeError("RAG dependencies are not installed.")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_function(),
        metadata={"description": "Curated women's reproductive health medical knowledge"},
    )


import math

def is_serverless():
    return not rag_dependencies_available()

def _get_hf_embedding(text):
    import requests
    hf_token = os.getenv("HF_API_KEY")
    if not hf_token:
        print("Warning: HF_API_KEY is missing!")
        return []
    
    api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    headers = {"Authorization": f"Bearer {hf_token}"}
    for attempt in range(3):
        try:
            response = requests.post(api_url, headers=headers, json={"inputs": [text], "options": {"wait_for_model": True}}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result
        except Exception as e:
            print(f"HF API Error: {e}")
    return []

def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if magnitude1 * magnitude2 == 0:
        return 0
    return dot_product / (magnitude1 * magnitude2)

def rag_is_ready():
    if is_serverless():
        json_path = RAG_DATA_DIR / "rag_vectors.json"
        return json_path.exists()

    try:
        return _collection().count() > 0
    except Exception:
        return False


def _extract_page_text(url):
    cache_path = _cache_path(url)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        blocks = []
        for element in soup.select("main h1, main h2, main h3, main p, article h1, article h2, article h3, article p, li"):
            text = _clean_text(element.get_text(" ", strip=True))
            if len(text) >= 40:
                blocks.append(text)

        if not blocks:
            for element in soup.select("p, li"):
                text = _clean_text(element.get_text(" ", strip=True))
                if len(text) >= 40:
                    blocks.append(text)

        text = "\n\n".join(blocks)
        if text:
            PAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")
        return text
    except Exception as exc:
        print(f"RAG page fetch error for {url}: {exc}")
        return ""


def _tokenize(text):
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) >= 3
    }


def _infer_topic_tags(text):
    lowered = (text or "").lower()
    tags = []
    for tag, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            tags.append(tag)
    return sorted(tags)


def _extract_page_blocks(url):
    cache_path = _structured_cache_path(url)
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        selector = "main h1, main h2, main h3, main p, main li, article h1, article h2, article h3, article p, article li"
        raw_elements = soup.select(selector)
        if not raw_elements:
            raw_elements = soup.select("h1, h2, h3, p, li")

        blocks = []
        for element in raw_elements:
            text = _clean_text(element.get_text(" ", strip=True))
            if len(text) < 30:
                continue
            kind = "heading" if element.name in {"h1", "h2", "h3"} else "text"
            blocks.append({"kind": kind, "level": element.name, "text": text})

        if blocks:
            PAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(blocks, ensure_ascii=False), encoding="utf-8")
            text_cache = _cache_path(url)
            text_cache.write_text("\n\n".join(block["text"] for block in blocks), encoding="utf-8")

        return blocks
    except Exception as exc:
        print(f"RAG page fetch error for {url}: {exc}")
        return []


def _extract_page_sections(url):
    blocks = _extract_page_blocks(url)
    if not blocks:
        text = _extract_page_text(url)
        if not text:
            return []
        return [{"heading": "Overview", "text": text}]

    sections = []
    current_heading = "Overview"
    current_parts = []

    def flush_section():
        if not current_parts:
            return
        section_text = "\n\n".join(current_parts).strip()
        if len(section_text) >= 80:
            sections.append({"heading": current_heading, "text": section_text})

    for block in blocks:
        if block["kind"] == "heading":
            flush_section()
            current_heading = block["text"]
            current_parts = []
            continue
        current_parts.append(block["text"])

    flush_section()
    return sections


def _chunk_section_text(section_heading, text, chunk_size=1100, overlap=180):
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return []

    chunks = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            overlap_text = current[-overlap:] if overlap else ""
            current = f"{overlap_text}\n\n{paragraph}".strip()
        else:
            chunks.append(paragraph[:chunk_size])
            current = paragraph[chunk_size - overlap :].strip() if overlap < len(paragraph) else ""

    if current:
        chunks.append(current)

    return [
        {
            "heading": section_heading,
            "text": chunk,
        }
        for chunk in chunks
        if len(chunk) >= 120
    ]


def _chunk_sections(sections):
    chunks = []
    for section in sections:
        heading = section.get("heading") or "Overview"
        text = section.get("text") or ""
        chunks.extend(_chunk_section_text(heading, text))
    return chunks


def _document_id(url, chunk_index):
    digest = hashlib.sha256(f"{url}:{chunk_index}".encode("utf-8")).hexdigest()
    return f"doc-{digest[:24]}"


def _dedupe_sources(items):
    unique = []
    seen_urls = set()
    for item in items:
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        unique.append(item)
    return unique


def _load_curated_sources():
    if not CURATED_SOURCES_PATH.exists():
        return []

    try:
        return json.loads(CURATED_SOURCES_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Failed to load curated sources: {exc}")
        return []


def _source_topics(source):
    return source.get("topics") or []


def _topic_string(source):
    return " | ".join(_source_topics(source))


def _is_action_oriented(query):
    lowered = (query or "").lower()
    return any(term in lowered for term in ACTION_ORIENTED_TERMS)


def build_rag_index(queries=None, reset=False, include_live_discovery=False):
    if not rag_dependencies_available():
        raise RuntimeError("Install chromadb and sentence-transformers before building the RAG index.")

    queries = queries or DEFAULT_TOPIC_QUERIES
    collection = _collection()

    if reset:
        existing = collection.get(include=[])
        existing_ids = existing.get("ids", [])
        if existing_ids:
            collection.delete(ids=existing_ids)

    candidate_sources = list(_load_curated_sources())
    if include_live_discovery:
        for query in queries:
            candidate_sources.extend(fetch_medical_sources(query))

    source_documents = _dedupe_sources(candidate_sources)

    ids = []
    documents = []
    metadatas = []
    indexed_sources = []

    for source in source_documents:
        if source.get("source") in INGEST_EXCLUDED_SOURCES:
            continue

        sections = _extract_page_sections(source["url"])
        base_text = "\n\n".join(section["text"] for section in sections)
        if not base_text:
            base_text = source.get("excerpt", "")
            sections = [{"heading": "Overview", "text": base_text}] if base_text else []

        chunks = _chunk_sections(sections)

        if not chunks:
            continue

        inferred_topics = _infer_topic_tags(f"{source['title']} {base_text[:2500]}")
        merged_topics = sorted(set(_source_topics(source) + inferred_topics))

        indexed_sources.append(
            {
                "source": source["source"],
                "title": source["title"],
                "url": source["url"],
                "chunks": len(chunks),
                "topics": merged_topics,
            }
        )

        for index, chunk in enumerate(chunks):
            ids.append(_document_id(source["url"], index))
            topic_text = " | ".join(merged_topics)
            section_heading = chunk.get("heading") or "Overview"
            chunk_text = chunk.get("text") or ""
            chunk_topics = sorted(set(merged_topics + _infer_topic_tags(f"{section_heading} {chunk_text[:1200]}")))
            chunk_topic_text = " | ".join(chunk_topics)
            chunk_document = (
                f"{source['title']}\n"
                f"Source: {source['source']}\n"
                f"Section: {section_heading}\n"
                f"Topics: {chunk_topic_text or topic_text}\n\n"
                f"{chunk_text}"
            ).strip()
            documents.append(chunk_document)
            metadatas.append(
                {
                    "source": source["source"],
                    "title": source["title"],
                    "url": source["url"],
                    "chunk_index": index,
                    "topics": chunk_topic_text or topic_text,
                    "section_heading": section_heading,
                }
            )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "queries": queries,
        "include_live_discovery": include_live_discovery,
        "document_count": len(ids),
        "source_count": len(indexed_sources),
        "sources": indexed_sources,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _serverless_retrieve_medical_context(query, limit=5):
    json_path = RAG_DATA_DIR / "rag_vectors.json"
    if not json_path.exists():
        return []
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        print(f"Error loading rag_vectors.json: {e}")
        return []

    query_embedding = _get_hf_embedding(query)
    if not query_embedding:
        print("Failed to get HF embedding. Cannot retrieve context.")
        return []
        
    query_tokens = _tokenize(query)
    query_topics = set(_infer_topic_tags(query))
    action_oriented = _is_action_oriented(query)

    candidates = []
    for record in records:
        metadata = record.get("metadata", {})
        document = record.get("document", "")
        doc_embedding = record.get("embedding", [])
        
        if not doc_embedding: continue

        cos_sim = cosine_similarity(query_embedding, doc_embedding)
        distance = 1.0 - cos_sim
        
        url = metadata.get("url", "")
        if not url:
            continue

        title = metadata.get("title", url)
        section_heading = metadata.get("section_heading", "")
        excerpt_body = document.split("\n\n", 1)[1] if "\n\n" in document else document
        excerpt = _clean_text(excerpt_body)[:420]
        metadata_topics = set(filter(None, (metadata.get("topics") or "").split(" | ")))
        title_tokens = _tokenize(f"{title} {section_heading}")
        excerpt_tokens = _tokenize(document)
        
        overlap_score = len(query_tokens & title_tokens) * 2.5 + len(query_tokens & excerpt_tokens) * 0.35
        topic_score = len(query_topics & metadata_topics) * 2.0
        action_score = 1.2 if action_oriented and _is_action_oriented(f"{title} {excerpt}") else 0
        
        semantic_score = max(0, 2.5 - float(distance))
        score = overlap_score + topic_score + action_score + semantic_score

        candidates.append(
            {
                "score": score,
                "source": metadata.get("source", "Unknown"),
                "title": title,
                "url": url,
                "excerpt": excerpt,
                "topics": metadata.get("topics", ""),
                "section_heading": section_heading,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)

    ranked = []
    seen_urls = set()
    for candidate in candidates:
        url = candidate["url"]
        if url in seen_urls:
            continue

        seen_urls.add(url)
        ranked.append(
            {
                "source": candidate["source"],
                "title": candidate["title"],
                "url": url,
                "excerpt": candidate["excerpt"],
                "topics": candidate["topics"],
                "section_heading": candidate["section_heading"],
            }
        )

        if len(ranked) >= limit:
            break

    return ranked

def retrieve_medical_context(query, limit=5):
    if not rag_is_ready():
        return []

    if is_serverless():
        return _serverless_retrieve_medical_context(query, limit)


    try:
        results = _collection().query(
            query_texts=[query],
            n_results=max(limit * 4, 12),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        print(f"RAG retrieval error: {exc}")
        return []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    query_tokens = _tokenize(query)
    query_topics = set(_infer_topic_tags(query))
    action_oriented = _is_action_oriented(query)

    candidates = []

    for index, (document, metadata) in enumerate(zip(documents, metadatas)):
        if not metadata:
            continue

        url = metadata.get("url", "")
        if not url:
            continue

        title = metadata.get("title", url)
        section_heading = metadata.get("section_heading", "")
        excerpt_body = document.split("\n\n", 1)[1] if "\n\n" in document else document
        excerpt = _clean_text(excerpt_body)[:420]
        metadata_topics = set(filter(None, (metadata.get("topics") or "").split(" | ")))
        title_tokens = _tokenize(f"{title} {section_heading}")
        excerpt_tokens = _tokenize(document)
        overlap_score = len(query_tokens & title_tokens) * 2.5 + len(query_tokens & excerpt_tokens) * 0.35
        topic_score = len(query_topics & metadata_topics) * 2.0
        action_score = 1.2 if action_oriented and _is_action_oriented(f"{title} {excerpt}") else 0
        distance = distances[index] if index < len(distances) else None
        semantic_score = max(0, 2.5 - float(distance)) if distance is not None else 0
        score = overlap_score + topic_score + action_score + semantic_score

        candidates.append(
            {
                "score": score,
                "source": metadata.get("source", "Unknown"),
                "title": title,
                "url": url,
                "excerpt": excerpt,
                "topics": metadata.get("topics", ""),
                "section_heading": section_heading,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)

    ranked = []
    seen_urls = set()
    for candidate in candidates:
        url = candidate["url"]
        if url in seen_urls:
            continue

        seen_urls.add(url)
        ranked.append(
            {
                "source": candidate["source"],
                "title": candidate["title"],
                "url": url,
                "excerpt": candidate["excerpt"],
                "topics": candidate["topics"],
                "section_heading": candidate["section_heading"],
            }
        )

        if len(ranked) >= limit:
            break

    return ranked


if __name__ == "__main__":
    manifest = build_rag_index(reset=True)
    print(json.dumps(manifest, indent=2))
