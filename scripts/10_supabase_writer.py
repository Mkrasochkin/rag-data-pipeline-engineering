# ============================================================================
# scripts/10_supabase_writer.py
# SupabaseMetadataWriter - запись документов и секций в Supabase
# ============================================================================

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import date

from dotenv import load_dotenv
from supabase import Client, create_client

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


def get_supabase_client() -> Client:
    """Создает Supabase client из переменных окружения."""
    load_dotenv(override=True)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_PRIVATE_KEY_LONG")

    if not supabase_url or not supabase_key:
        raise ValueError(
            "Не заданы SUPABASE_URL и ключ Supabase (SUPABASE_PRIVATE_KEY/SUPABASE_PUBLIC_KEY)"
        )

    return create_client(supabase_url, supabase_key)


class SupabaseMetadataWriter:
    """
    Записывает метаданные документов и секции в Supabase.
    Использует UPSERT логику: если документ существует - обновляет.
    """

    def __init__(self):
        self.supabase = get_supabase_client()
        self.json_dir = OUTPUT_DIR / "json"

    def upsert_document(self, doc_data: Dict) -> Dict:
        """
        UPSERT документа по designation + year + type.

        Args:
            doc_data: словарь с метаданными документа

        Returns:
            Dict с id документа и флагом created
        """

        # Проверяем существование документа
        existing = self.supabase.table("documents") \
            .select("id") \
            .eq("designation", doc_data["designation"]) \
            .eq("year", doc_data["year"]) \
            .eq("type", doc_data["type"]) \
            .eq("visibility", "public") \
            .execute()

        # Генерируем document_family_id (если не передан)
        family_id = doc_data.get("document_family_id", str(uuid.uuid4()))

        if existing.data:
            # Документ существует - обновляем
            doc_id = existing.data[0]["id"]

            update_data = {
                "document_family_id": family_id,
                "official_title": doc_data["official_title"],
                "topic": doc_data.get("topic"),
                "valid_from": doc_data.get("valid_from"),
                "valid_to": doc_data.get("valid_to"),
                "is_mandatory": doc_data.get("is_mandatory", False),
                "version_status": doc_data.get("version_status", "active"),
                "source_type": doc_data.get("source_type", "parsed"),
                "processing_metadata": doc_data.get("processing_metadata", {}),
            }

            # Убираем None значения
            update_data = {k: v for k, v in update_data.items() if v is not None}

            self.supabase.table("documents") \
                .update(update_data) \
                .eq("id", doc_id) \
                .execute()

            print(f"  📝 Обновлен: {doc_data['type']} {doc_data['designation']}")
            return {"id": doc_id, "created": False}

        else:
            # Документ не существует - создаем новый
            insert_data = {
                "document_family_id": family_id,
                "type": doc_data["type"],
                "designation": doc_data["designation"],
                "official_title": doc_data["official_title"],
                "year": doc_data["year"],
                "topic": doc_data.get("topic"),
                "valid_from": doc_data.get("valid_from"),
                "valid_to": doc_data.get("valid_to"),
                "is_mandatory": doc_data.get("is_mandatory", False),
                "visibility": "public",
                "source_type": doc_data.get("source_type", "parsed"),
                "version_status": doc_data.get("version_status", "active"),
                "tags": doc_data.get("tags", []),
                "processing_metadata": doc_data.get("processing_metadata", {}),
            }

            # Убираем None значения
            insert_data = {k: v for k, v in insert_data.items() if v is not None}

            result = self.supabase.table("documents").insert(insert_data).execute()
            doc_id = result.data[0]["id"]

            print(f"  ✅ Создан: {doc_data['type']} {doc_data['designation']}")
            return {"id": doc_id, "created": True}

    def upsert_sections(self, doc_id: str, sections: List[Dict]) -> int:
        """
        Заменяет все секции документа на новые.

        Args:
            doc_id: UUID документа
            sections: список секций
  
        Returns:
            int: количество вставленных секций
        """

        # Удаляем старые секции
        self.supabase.table("document_sections") \
            .delete() \
            .eq("doc_id", doc_id) \
            .execute()

        if not sections:
            return 0

        # Подготавливаем секции для вставки
        sections_data = []
        section_map = {}  # code -> id для связи родитель-потомок

        for section in sections:
            section_data = {
                "doc_id": doc_id,
                "section_code": section.get("section_code"),
                "section_title": section["section_title"],
                "level": section.get("level", 1),
                "hierarchy_path": section.get("hierarchy_path"),
            }

            # Определяем родительскую секцию
            if section.get("level", 1) > 1 and section.get("section_code"):
                # Для "1.1" родитель "1", для "8.1.1" родитель "8.1"
                parts = section["section_code"].split(".")
                parent_code = ".".join(parts[:-1])
    
                if parent_code in section_map:
                    section_data["parent_section_id"] = section_map[parent_code]

            sections_data.append(section_data)

        # Вставляем секции и запоминаем их ID
        result = self.supabase.table("document_sections").insert(sections_data).execute()

        return len(result.data)

    def process_json_file(self, json_path: Path) -> Dict:
        """
        Обрабатывает один JSON файл: записывает документ и секции.

        Args:
            json_path: путь к JSON файлу
  
        Returns:
            Dict с результатами обработки
        """

        print(f"\n📄 Обработка: {json_path.name}")

        # Читаем JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doc_metadata = data["document"]["metadata"]
        sections = data["document"]["sections"]

        # Добавляем source_type = 'parsed'
        doc_metadata["source_type"] = "parsed"

        # UPSERT документа
        doc_result = self.upsert_document(doc_metadata)

        # UPSERT секций
        sections_count = self.upsert_sections(doc_result["id"], sections)

        print(f"  📑 Секций: {sections_count}")

        return {
            "file": json_path.name,
            "document_id": doc_result["id"],
            "created": doc_result["created"],
            "sections_count": sections_count
        }

    def process_all(self) -> List[Dict]:
        """
        Обрабатывает все JSON файлы в output/json/

        Returns:
            List[Dict]: результаты обработки всех файлов
        """

        json_files = list(self.json_dir.glob("*.json"))


        if not json_files:
            print("❌ Нет JSON файлов для обработки")
            return []

        print(f"\n🚀 Запись в Supabase ({len(json_files)} файлов)")
        print("=" * 50)

        results = []
        for json_path in json_files:
            try:
                result = self.process_json_file(json_path)
                results.append(result)
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                results.append({
                    "file": json_path.name,
                    "error": str(e)
                })

        # Итоги
        print("\n" + "=" * 50)
        print("📊 ИТОГИ:")

        created = sum(1 for r in results if r.get("created"))
        updated = sum(1 for r in results if r.get("created") is False)
        errors = sum(1 for r in results if "error" in r)
        total_sections = sum(r.get("sections_count", 0) for r in results)

        print(f"  ✅ Создано документов: {created}")
        print(f"  📝 Обновлено документов: {updated}")
        print(f"  ❌ Ошибок: {errors}")
        print(f"  📑 Всего секций: {total_sections}")

        return results


# ============================================================================
# Точка входа
# ============================================================================

if __name__ == "__main__":
    writer = SupabaseMetadataWriter()
    results = writer.process_all()
