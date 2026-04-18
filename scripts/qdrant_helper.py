from qdrant_client import QdrantClient


class QdrantHelper:
    def __init__(
        self,
        *,
        qdrant_host: str,
        qdrant_port: str,
        qdrant_api_key: str = "",
    ):
        self.qdrant_url = f"http://{qdrant_host}:{qdrant_port}"
        self.qdrant_api_key = qdrant_api_key

    def get_qdrant_client(self) -> QdrantClient:
        """
        Создает Qdrant client по указанным параметрам.
        И возвращаем его.
        """
        return QdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
            )
