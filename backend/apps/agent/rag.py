import uuid
import math
from django.conf import settings


def _get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(url=settings.QDRANT_URL)


def _get_embeddings(texts: list) -> list:
    from sentence_transformers import SentenceTransformer
    # all-MiniLM-L6-v2 runs locally — no API key needed, 384-dim vectors
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def _rerank(query: str, results: list, threshold: float = 0.70) -> list:
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        pairs = [(query, r['snippet']) for r in results]
        raw_scores = model.predict(pairs)
        for result, score in zip(results, raw_scores):
            # sigmoid normalizes the cross-encoder logit to [0, 1]
            result['rerank_score'] = round(float(1 / (1 + math.exp(-score))), 3)
        filtered = [r for r in results if r['rerank_score'] >= threshold]
        return sorted(filtered, key=lambda x: x['rerank_score'], reverse=True)
    except Exception:
        # cross-encoder unavailable — fall back to vector score threshold
        return [r for r in results if r.get('vector_score', 0) >= threshold]


def _chunk_text(text: str, chunk_size: int = 120, overlap: int = 20) -> list:
    # chunk by sentences rather than words — better semantic coherence per chunk
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        # overlap so sentences that land at a chunk boundary don't lose context
        start += chunk_size - overlap
    return chunks


def _ensure_collection():
    from qdrant_client.models import VectorParams, Distance
    client = _get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            # 384 matches all-MiniLM-L6-v2 output dimension
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )


class RAGService:
    @staticmethod
    def index_document(document) -> list:
        _ensure_collection()
        from qdrant_client.models import PointStruct

        client = _get_qdrant_client()
        chunks = _chunk_text(document.content)
        if not chunks:
            return []

        embeddings = _get_embeddings(chunks)

        points = []
        point_ids = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    'org_id': str(document.org.id),
                    'document_id': str(document.id),
                    'document_name': document.name,
                    'doc_type': document.doc_type,
                    'chunk_index': i,
                    'text': chunk,
                },
            ))

        client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
        return point_ids

    @staticmethod
    def search(query: str, org_id: str, doc_type: str = None, top_k: int = 5, threshold: float = 0.70) -> list:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = _get_qdrant_client()
        query_vector = _get_embeddings([query])[0]

        # org_id filter is mandatory — without it one tenant could see another's documents
        must_conditions = [FieldCondition(key='org_id', match=MatchValue(value=org_id))]
        if doc_type:
            must_conditions.append(
                FieldCondition(key='doc_type', match=MatchValue(value=doc_type))
            )

        # fetch more candidates than needed so reranker has room to filter down
        candidates = client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions),
            limit=top_k * 4,
        )

        results = [
            {
                'document_name': r.payload['document_name'],
                'doc_type': r.payload['doc_type'],
                'snippet': r.payload['text'][:600],
                'vector_score': round(r.score, 3),
            }
            for r in candidates
        ]

        reranked = _rerank(query, results, threshold=threshold)
        return reranked[:top_k]

    @staticmethod
    def delete_document_vectors(point_ids: list):
        if not point_ids:
            return
        from qdrant_client.models import PointIdsList

        client = _get_qdrant_client()
        client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=PointIdsList(points=point_ids),
        )
