from supabase import Client


class SupabaseChunksUpserter:
    def _get_document(
        self,
        *,
        supabase_client: Client,
        designation: str,
        year: int,
        doc_type: str,
    ) -> dict:
        """
        Ищет документ по designation, year и type и возвращает его id и workspace_id.
        Если документ не найден, выбрасывается ValueError.
        Args:
            supabase_client: клиент Supabase
            designation: код документа
            year: год документа
            doc_type: тип документа
        """
        response = (
            supabase_client.table("documents")
            .select("id, workspace_id")
            .eq("designation", designation)
            .eq("year", year)
            .eq("type", doc_type)
            .single()
            .execute()
        )
        document = response.data
        if not document:
            raise ValueError(
                f"Документ не найден: designation={designation}, year={year}, type={doc_type}"
            )
        if not document.get("id") or not document.get("workspace_id"):
            raise ValueError("В documents отсутствуют id или workspace_id.")
        return document

    def insert_chunks(
        self,
        *,
        chunks: list[dict],
        supabase_client: Client,
    ) -> list[str]:
        """
        Вставляет список чанков в таблицу chunks и возвращает список их id.
        Если чанки не вставлены, выбрасывается ValueError.

        Args:
            chunks: список словарей с данными чанков
            supabase_client: клиент Supabase
        """
        # Получаем type, designation, year из чанка и ищем документ в Supabase
        type = chunks[0]["metadata"]["type"]
        designation = chunks[0]["metadata"]["designation"]
        year = chunks[0]["metadata"]["year"]

        # Ищем документ в Supabase
        document = self._get_document(
            supabase_client=supabase_client,
            designation=designation,
            year=year,
            doc_type=type,
        )
        # Вставляем чанки в таблицу chunks
        response = supabase_client.table("chunks").insert(chunks).execute()
        rows = response.data or []