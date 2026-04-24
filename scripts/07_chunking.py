import re
import uuid
import importlib
import json

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
Embedder = importlib.import_module("scripts.08_embedding").Embedder


DEFAULT_CHUNK_SIZE_TOKENS = 412
DEFAULT_CHUNK_OVERLAP_TOKENS = 100
MIN_BLOCK_TOKENS = 200
MAX_BLOCK_TOKENS = 500
SEPARATORS = ["\n\n", "\n", ". ", " "]
PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = PROJECT_ROOT / "output" / "json"

# Два случая:
# 1) Номер с точками (подпункты): 3.24, 4.9, 1.1, 5.3.6 — иногда после номера ещё точка: «5.3.6. В…».
# 2) Только цифры без точки (разделы): 4 Общие, 12 Сведения — только ЗАГЛАВНАЯ после номера,
#    иначе ловятся обрывы вроде «7 следующих…», «8 такие…» с середины абзаца.
_CLAUSE = re.compile(
    r"(?:^\s*(?P<sub>\d{1,3}(?:\.\d{1,3})+)\.?\s+(?P<sub_title>[А-ЯЁа-яA-Za-z«].+)$)"
    r"|(?:^\s*(?P<sec>\d{1,2})\s+(?P<sec_title>[А-ЯЁA-Z«].+)$)",
    re.MULTILINE,
)

# Только первая строка блока: «5.3.6 …» или «12 Сведения…» — для поля clause_ref в metadata
_FIRST_LINE_NUM = re.compile(
    r"^\s*((?:\d{1,3}(?:\.\d{1,3})+)|(?:\d{1,2}))\s*\.?\s+",
)


# Старт табличного блока (в т.ч. OCR-варианты: "аблица", "Т а б л и ц а").
_TABLE_START = re.compile(
    r"^\s*(?:#+\s*)?(?:(?:Окончание|Продолжение)\s+)?(?:[ТT]\s*а\s*б\s*л\s*и\s*ц\s*а|[ТT]?аблица)\s*[A-Za-zА-Яа-я0-9\.\-]*\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Заголовки/границы, после которых таблица обычно заканчивается.
_TABLE_HARD_BOUNDARY = re.compile(
    r"^\s*(?:Приложение\s+[А-ЯA-Z]|СП\s+\d|#{1,6}\s+|(?:\d{1,3}(?:\.\d{1,3})+|\d{1,2})\s+)",
    re.IGNORECASE,
)


class SPDocumentChunker:
    def __init__(
        self,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
        min_block_tokens: int = MIN_BLOCK_TOKENS,
        max_block_tokens: int = MAX_BLOCK_TOKENS,
        embedder: Embedder,
        separators: list[str] | None = None
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_block_tokens = min_block_tokens
        self.max_block_tokens = max_block_tokens
        self.separators = list(separators) if separators is not None else list(SEPARATORS)
        self.embedder = embedder

    def split_text_into_chunks(self, text: str) -> list[str]:
        """
        Стандартная функция RecursiveCharacterTextSplitter для разбиения
        текста на чанки по размеру chunk_size с перекрытием chunk_overlap.

        Args:
            text: текст для разбиения
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=self.embedder.count_tokens,
        )
        return splitter.split_text(text)

    def is_same_level_and_parent(self, first_number_text: str, second_number_text: str) -> bool:
        """
        Проверяет, находятся ли два пункта на одном уровне
        и имеют ли одного родителя.

        Args:
            first_number_text: первый номер пункта в виде текста
            second_number_text: второй номер пункта в виде текста
        """
        if not first_number_text or not second_number_text:
            return False

        # Убираем точки и разделяем на части
        first_parts = first_number_text.rstrip(".").split(".")
        second_parts = second_number_text.rstrip(".").split(".")

        # Проверяем, находятся ли два пункта на одном уровне
        # и не являются ли они корневыми элементами
        return (
            len(first_parts) == len(second_parts) and
            len(first_parts) > 1 and
            first_parts[:-1] == second_parts[:-1]
        )

    def filter_false_boundaries(self, matches: list[re.Match[str]]) -> list[re.Match[str]]:
        """
        Убираем ложные границы sec после sub.

        Args:
            matches: список совпадений для склеивания
        """
        if not matches:
            return []

        result: list[re.Match[str]] = []
        last: re.Match[str] | None = None

        for m in matches:
            sec = m.group("sec")

            if sec is not None and last is not None:
                prev_sub = last.group("sub")

                if prev_sub is not None:
                    try:
                        prev_sub_int = int(prev_sub.split(".", 1)[0])
                        sec_int = int(sec)
                        if sec_int < prev_sub_int:
                            # Убираем ложную границу
                            continue
                    except ValueError:
                        pass
            result.append(m)
            last = m

        return result

    def split_plain_sp_into_blocks(self, text: str) -> list[str]:
        """
        Разбивает текст на чанки по пунктам и возвращает список чанков.
        Если пункты не найдены, возвращает список чанков, разбитых по размеру.

        Args:
            text: текст для разбиения
        """
        # Ищем пункты в тексте
        matches = list(_CLAUSE.finditer(text))
        matches = self.filter_false_boundaries(matches)
        if not matches:
            if not text:
                return []
            return self.split_text_into_chunks(text)

        blocks: list[str] = []
        # Если первый пункт не в начале текста, добавляем текст до первого пункта в отдельный блок
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                blocks.append(preamble)

        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            if block:
                # Ищем табличные блоки
                # tables_blocks_start = list(_TABLE_START.finditer(block))
                # if tables_blocks_start:
                #     # Берем срез текста от начало таблицы до конца текста
                #     block_start_table = block[tables_blocks_start[0].start():end]
                #     tables_blocks_end = list(_TABLE_HARD_BOUNDARY.finditer(block_start_table))
                #     for table_block_start in tables_blocks_start:
                #         print("----------------START-------------")
                #         print(block_start_table)
                #         print(table_block_start.group(0))
                #     if tables_blocks_end:
                #         for table_block_end in tables_blocks_end:
                #             print("----------------END-------------")
                #             print(table_block_end.group(0))
                first = block.strip().split("\n", 1)[0] if text.strip() else ""
                m = _FIRST_LINE_NUM.match(first)
                first_item_number = m.group(1) if m else ""
                print(first_item_number)

                blocks.append(block)

        return self.merge_minimal_blocks(blocks)

    def merge_minimal_blocks(self, blocks: list[str]) -> list[str]:
        """
        Склеивает блоки, если их длина меньше MIN_BLOCK_TOKENS токенов и они находятся на одном уровне нумерации.
        Если блок меньше минимума, пытается склеить его с последующими блоками того же уровня,
        пока не наберётся максимум токенов.

        Args:
            blocks: список чанков для склеивания
        """
        if not blocks:
            return []

        merged_blocks: list[str] = []
        i = 0

        while i < len(blocks):
            # Текущий блок и его размер в токенах
            current_block = blocks[i]
            current_block_tokens = self.embedder.count_tokens(current_block)

            # Если блок меньше минимума, пытаемся склеить его с последующими блоками того же уровня
            if current_block_tokens < self.min_block_tokens:
                # Извлекаем номер пункта из первой строки блока в виде текста
                current_block_first_line = current_block.strip().split("\n", 1)[0]
                current_match = _FIRST_LINE_NUM.match(current_block_first_line)
                # Если номер пункта найден, добавляем его в словарь иначе пустая строка
                current_number_text = current_match.group(1) if current_match else ""

                # Индекс следующего блока
                j = i + 1

                while j < len(blocks):
                    # Следующий блок и его размер в токенах
                    next_block = blocks[j]
                    next_block_tokens = self.embedder.count_tokens(next_block)

                    # Извлекаем номер пункта из первой строки следующего блока в виде текста
                    next_block_first_line = next_block.strip().split("\n", 1)[0]
                    next_match = _FIRST_LINE_NUM.match(next_block_first_line)
                    next_number_text = next_match.group(1) if next_match else ""

                    # Проверяем, находятся ли два пункта на одном уровне и имеют ли одного родителя
                    check_level = self.is_same_level_and_parent(current_number_text, next_number_text)

                    # Если пункты не на одном уровне или сумма токенов превышает максимум, прекращаем склеивание
                    if not check_level or current_block_tokens + next_block_tokens > self.max_block_tokens:
                        break

                    # Склеиваем текущий блок с следующим и переходим к следующему блоку
                    current_block += "\n\n" + next_block
                    current_block_tokens += next_block_tokens
                    j += 1

                # Добавляем склеенный блок в список и переходим к следующему блоку
                merged_blocks.append(current_block)
                i = j
                continue

            else:
                # Добавляем текущий блок в список и переходим к следующему блоку
                merged_blocks.append(current_block)
                i += 1

        return merged_blocks

    def get_section_path(self, section_number: str) -> str:
        """
        Путь в иерархии номеров: для 5.3.6 — «5 > 5.3 > 5.3.6», для 12 — «12».

        Args:
            section_number: номер раздела
        """
        if not section_number:
            return ""
        result = []
        # Навсякий убираем точку справа и сплитим по точкам
        section_number = section_number.rstrip(".").split(".")

        for i, _ in enumerate(section_number):
            result.append(".".join(section_number[:i+1]))
        return " > ".join(result)

    def clause_display(self, nums: list[str]) -> str | None:
        """
        Человеко-читаемая подпись пунктов для UI (поле clause_display в БД).
        Один пункт: «п. 5.26.1»; несколько: «пп. 5.26.1-5.26.3».

        Args:
            nums: список номеров пунктов
        """
        if not nums:
            return None
        if len(nums) == 1:
            return f"п. {nums[0]}"
        return f"пп. {nums[0]}-{nums[-1]}"

    def get_data_from_json(self, json_path: Path) -> dict | None:
        """
        Читаем JSON-файл и возвращаем часть метаданных.

        Args:
            json_path: путь к JSON-файлу
        """
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        if json_data:
            return {
                "designation": json_data["document"]["metadata"]["designation"],
                "year": json_data["document"]["metadata"]["year"],
                "type": json_data["document"]["metadata"]["type"],
            }
        return None

    def add_metadata(
        self,
        *,
        blocks: list[str],
        document_text: str | None = None,
        json_path: Path = JSON_DIR / "СП_48_13330_2019.json",
    ) -> list[dict]:
        """
        Оборачивает разбитые на чанки тексты в словари с метаданными.

        token_count для каждого чанка — через count_tokens_for_embedding_model
        (токенайзер EMBEDDING_MODEL из embedder).

        Args:
            blocks: список чанков для добавления метаданных
            embedder: экземпляр Embedder для подсчёта токенов
        """
        result: list[dict] = []
        # Получаем год и код из JSON-файла один раз на весь документ
        data_json = self.get_data_from_json(json_path)
        designation = data_json["designation"]
        year = data_json["year"]
        type = data_json["type"]

        # Оборачиваем чанки в словари с метаданными
        for text in blocks:
            # Получаем первую строку блока и извлекаем номер пункта
            first = text.strip().split("\n", 1)[0] if text.strip() else ""
            m = _FIRST_LINE_NUM.match(first)
            first_item_number = m.group(1) if m else ""

            nums: list[str] = []
            for cm in _CLAUSE.finditer(text):
                d = cm.groupdict()
                n = d.get("sub") or d.get("sec")
                if n:
                    nums.append(n)
            clause_start: str | None = nums[0] if nums else None
            clause_end: str | None = nums[-1] if nums else None
            section_path = (
                self.get_section_path(clause_start) if clause_start else None
            )
            clause_display_str = self.clause_display(nums)

            # Проверяем, если токены в блоке больше максимума, то разбиваем на чанки
            cur_token_count = self.embedder.count_tokens(text)
            pieces = [text] if cur_token_count <= self.max_block_tokens else self.split_text_into_chunks(text)

            for piece in pieces:
                result.append(
                    {
                        "metadata": {
                            "qdrant_point_id": str(uuid.uuid4()),
                            "designation": designation,
                            "year": year,
                            "type": type,
                            "chunk_index": len(result),
                            "section_id": None,
                            "first_item_number": first_item_number,
                            "clause_start": clause_start,
                            "clause_end": clause_end,
                            "section_path": section_path,
                            "clause_numbers": nums,
                            "clause_display": clause_display_str,
                            "merged_clauses_count": len(nums),
                            "content_type": "text",
                            "parent_chunk_id": None,
                            "content_url": None,
                            "text_content": piece,
                            "token_count": self.embedder.count_tokens(piece),
                        },
                    }
                )
        return result
