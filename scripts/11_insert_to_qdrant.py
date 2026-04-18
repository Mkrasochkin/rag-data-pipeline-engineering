import importlib
from qdrant_client import QdrantClient, models

Embedder = importlib.import_module("scripts.08_embedding").Embedder


def embed_vector_rows_to_qdrant_points(
    embedder: Embedder,
    vector_rows: list[dict],
) -> list[dict]:
    """
    Точки для upsert из строк SupabaseChunksUpserter: text, point_id, payload.
    """
    if not vector_rows:
        return []

    qdrant_points: list[dict] = []
    for row in vector_rows:
        text = row.get("text") or ""
        vector = embedder.embed_text(text)
        qdrant_points.append(
            {
                "id": row["point_id"],
                "vector": vector,
                "payload": row.get("payload") or {},
            }
        )
    return qdrant_points


class QdrantInsertor:
    def __init__(
        self,
        *,
        qdrant_client: QdrantClient,
    ):
        self.qdrant_client = qdrant_client

    def insert_chunks(
        self,
        *,
        chunks: list[dict],
        collection_name: str = "test_chunks",
    ) -> None:
        """
        Вставляет чанки в Qdrant.
        """
        if not self.check_collection(collection_name=collection_name):
            print(f"Коллекция {collection_name} не существует")
            return

        self.qdrant_client.upsert(
            collection_name=collection_name,
            points=chunks,
        )
        print(f"Вставлено {len(chunks)} чанков в коллекцию {collection_name}")

    def create_collection(
        self,
        *,
        collection_name: str,
        vector_size: int = 1024,
        distance: models.Distance = models.Distance.COSINE,
    ) -> None:
        """
        Создает коллекцию в Qdrant. 
        Если коллекция уже существует, то ничего не делает.
        """
        if self.check_collection(collection_name=collection_name):
            print(f"Коллекция {collection_name} уже существует")
            return

        self.qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=distance,
            ),
        )
        print(f"Коллекция {collection_name} создана")

    def delete_collection(
        self,
        *,
        collection_name: str,
    ) -> None:
        """
        Удаляет коллекцию в Qdrant. Если коллекция не существует, то ничего не делает.
        """
        if not self.check_collection(collection_name=collection_name):
            print(f"Коллекция {collection_name} не существует")
            return

        self.qdrant_client.delete_collection(collection_name=collection_name)
        print(f"Коллекция {collection_name} удалена")

    def check_collection(
        self,
        *,
        collection_name: str,
    ) -> bool:
        """
        Проверяет наличие коллекции в Qdrant.
        True - коллекция существует, False - коллекция не существует.
        """
        return self.qdrant_client.collection_exists(collection_name=collection_name)
