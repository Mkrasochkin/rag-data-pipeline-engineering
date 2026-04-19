from qdrant_client import QdrantClient


class QdrantHelper:
    def __init__(
        self,
        *,
        qdrant_host: str,
        qdrant_port: str,
        qdrant_api_key: str = "",
    ):
        self.client = QdrantClient(
            url=f"http://{qdrant_host}:{qdrant_port}",
            api_key=qdrant_api_key,
            timeout=10,
        )

    def get_qdrant_client(self) -> QdrantClient:
        """
        Возвращает Qdrant client.
        """
        return self.client

    def check_connection(self) -> bool:
        """
        Проверяет соединение с Qdrant.
        """
        try:
            self.get_qdrant_client().get_collections()
            return True
        except Exception as e:
            print(f"Ошибка при проверке соединения с Qdrant: {e}")
            return False
