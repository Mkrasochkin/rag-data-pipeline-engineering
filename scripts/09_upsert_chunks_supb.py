from supabase import Client


class SupabaseChunksUpserter:
    def __init__(
        self,
        *,
        supabase_client: Client,
    ):
        self.supabase_client = supabase_client

    def _get_document(
        self,
        *,
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
            self.supabase_client.table("documents")
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
                f"Документ не найден: designation={designation}, year={year}, "
                f"type={doc_type}"
            )
        if not document.get("id"):
            raise ValueError("В documents отсутствуют id")
        return document

    def _get_section_maps(
        self,
        *,
        doc_id: str,
    ) -> dict[str, str]:
        """
        Возвращает маппинги секций документа.

        Args:
            doc_id: id документа
        """
        response = (
            self.supabase_client.table("document_sections")
            .select("id, section_code")
            .eq("doc_id", doc_id)
            .execute()
        )
        rows = response.data or []

        by_section_code: dict[str, str] = {}
        for row in rows:
            section_id = row.get("id")
            if not section_id:
                continue

            section_code = row.get("section_code")
            if section_code:
                by_section_code[section_code] = section_id

        return by_section_code

    def insert_chunks(
        self,
        *,
        chunks: list[dict],
        batch_size: int = 100,
    ) -> list[str]:
        """
        Вставляет список чанков в таблицу chunks батчами и возвращает
        список id вставленных записей.

        Args:
            chunks: список словарей с данными чанков
            batch_size: размер одного батча для insert
        """
        if not chunks or batch_size <= 0:
            return []

        # Получаем type, designation, year из чанка и ищем документ в Supabase
        doc_type = chunks[0]["metadata"]["type"]
        designation = chunks[0]["metadata"]["designation"]
        year = chunks[0]["metadata"]["year"]

        # Ищем документ в Supabase
        document = self._get_document(
            designation=designation,
            year=year,
            doc_type=doc_type,
        )

        doc_id = document["id"]
        workspace_id = document.get("workspace_id")
        section_ids_by_code = self._get_section_maps(doc_id=doc_id)

        records: list[dict] = []
        for chunk in chunks:
            metadata = chunk["metadata"]
            section_id = (
                metadata.get("section_id")
                or section_ids_by_code.get(metadata.get("section_code", None))
                or section_ids_by_code.get(metadata.get("clause_start", None))
            )

            records.append(
                {
                    "qdrant_point_id": metadata.get("qdrant_point_id"),
                    "doc_id": doc_id,
                    "section_id": section_id,
                    "workspace_id": workspace_id,
                    "section_path": metadata.get("section_path"),
                    "clause_start": metadata.get("clause_start"),
                    "clause_end": metadata.get("clause_end"),
                    "clause_numbers": metadata.get("clause_numbers", []),
                    "clause_display": metadata.get("clause_display"),
                    "merged_clauses_count": metadata.get("merged_clauses_count", 0),
                    "chunk_index": metadata.get("chunk_index"),
                    "content_type": metadata.get("content_type", "text"),
                    "parent_chunk_id": metadata.get("parent_chunk_id"),
                    "content_url": metadata.get("content_url"),
                    "text_content": metadata.get("text_content", chunk.get("text", "")),
                    "token_count": metadata.get("token_count"),
                }
            )

        inserted_ids: list[str] = []
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            response = self.supabase_client.table("chunks").upsert(batch).execute()
            rows = response.data or []
            inserted_ids.extend(row["id"] for row in rows if row.get("id"))

        if not inserted_ids:
            raise ValueError("Не удалось вставить чанки в таблицу chunks.")

        return inserted_ids
