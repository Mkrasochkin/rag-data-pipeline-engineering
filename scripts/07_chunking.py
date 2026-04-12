import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from embedder import Embedder

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MIN_BLOCK_CHARS = 200
MAX_BLOCK_CHARS = 1000
SEPARATORS = ["\n\n", "\n", ". ", " "]

#Регулярка находит строки, которые выглядят как пункты/разделы документа, и разбивает их на номер + заголовок
_CLAUSE = re.compile(
    r"(?:^\s*(?P<sub>\d{1,3}(?:\.\d{1,3})+)\.?\s+(?P<sub_title>[А-ЯЁа-яA-Za-z«].+)$)"
    r"|(?:^\s*(?P<sec>\d{1,2})\s+(?P<sec_title>[А-ЯЁA-Z«].+)$)",
    re.MULTILINE,
)

# Достаёт номер пункта/раздела из начала строки (например 5.3.6 или 12)
_FIRST_LINE_NUM = re.compile(
    r"^\s*((?:\d{1,3}(?:\.\d{1,3})+)|(?:\d{1,2}))\s*\.?\s+",
)

# Первая строка в начале файла, начинающаяся с СП
_FIRST_LINE_SP = re.compile(
    r"^\s*(?:#+\s*)?(?P<title>СП.+)$",
    re.MULTILINE,
)


class SPDocumentChunker:
    def __init__(
        self,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        min_block_chars: int = MIN_BLOCK_CHARS,
        max_block_chars: int = MAX_BLOCK_CHARS,
        separators: list[str] | None = None
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_block_chars = min_block_chars
        self.max_block_chars = max_block_chars
        self.separators = list(separators) if separators is not None else list(SEPARATORS)

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

    def read_text_from_file(self, file_path: str) -> str:
        """
        Читает текст из пути файла file_path и возвращает его в виде строки.

        Args:
            file_path: путь к файлу
        """
        with open(file_path, encoding="utf-8") as file:
            return file.read()

    def split_plain_sp_into_blocks(self, text: str) -> list[str]:
        """
        Разбивает текст на чанки по пунктам и возвращает список чанков.
        Если пункты не найдены, возвращает список чанков, разбитых по размеру.

        Args:
            text: текст для разбиения
        """
        # Ищем пункты в тексте
        matches = list(_CLAUSE.finditer(text))
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
                blocks.append(block)

        return self.merge_minimal_blocks(blocks)

    def merge_minimal_blocks(self, blocks: list[str]) -> list[str]:
        """
        Склеивает блоки, если их длина меньше MIN_BLOCK_CHARS символов и они находятся на одном уровне нумерации.
        Если блок меньше минимума, пытается склеить его с последующими блоками того же уровня,
        пока не наберётся максимум символов.

        Args:
            blocks: список чанков для склеивания
        """
        if not blocks:
            return []

        merged_blocks: list[str] = []
        i = 0

        while i < len(blocks):
            # Текущий блок и его размер
            current_block = blocks[i]
            current_block_size = len(current_block)

            # Если блок меньше минимума, пытаемся склеить его с последующими блоками того же уровня
            if current_block_size < self.min_block_chars:
                # Извлекаем номер пункта из первой строки блока в виде текста
                current_block_first_line = current_block.strip().split("\n", 1)[0]
                current_match = _FIRST_LINE_NUM.match(current_block_first_line)
                # Если номер пункта найден, добавляем его в словарь иначе пустая строка
                current_number_text = current_match.group(1) if current_match else ""

                # Индекс следующего блока
                j = i + 1

                while j < len(blocks):
                    # Следующий блок и его размер
                    next_block = blocks[j]
                    next_block_size = len(next_block)

                    # Извлекаем номер пункта из первой строки следующего блока в виде текста
                    next_block_first_line = next_block.strip().split("\n", 1)[0]
                    next_match = _FIRST_LINE_NUM.match(next_block_first_line)
                    next_number_text = next_match.group(1) if next_match else ""

                    # Проверяем, находятся ли два пункта на одном уровне и имеют ли одного родителя
                    check_level = self.is_same_level_and_parent(current_number_text, next_number_text)

                    # Если пункты не на одном уровне или сумма размеров блоков превышает максимум, прекращаем склеивание
                    if not check_level or len(current_block) + 2 + next_block_size > self.max_block_chars:
                        break

                    # Склеиваем текущий блок с следующим и переходим к следующему блоку
                    current_block += "\n\n" + next_block
                    current_block_size = len(current_block)
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
        Один пункт: «п. 5.26.1»; несколько: «пп. 5.26.1-5.26.3». Без пунктов - NULL.

        Args:
            nums: список номеров пунктов
        """
        if not nums:
            return None
        if len(nums) == 1:
            return f"п. {nums[0]}"
        return f"пп. {nums[0]}-{nums[-1]}"

    def add_metadata(
        self,
        blocks: list[str],
        doc_id: str = "",
        *,
        embedder: Embedder,
        document_text: str | None = None,
    ) -> list[dict]:
        """
        Оборачивает разбитые на чанки тексты в словари с метаданными.

        token_count для каждого чанка — через count_tokens_for_embedding_model
        (токенайзер EMBEDDING_MODEL из embedder).

        Args:
            blocks: список чанков для добавления метаданных
            doc_id: идентификатор документа (например, СП 48.13330.2019)
            embedder: экземпляр Embedder для подсчёта токенов
        """
        # Определяем идентификатор документа
        resolved_doc_id = doc_id or ""
        if document_text:
            head = "\n".join(document_text.splitlines()[:200])
            m = _FIRST_LINE_SP.search(head)
            if m:
                title = m.group("title").strip()
                code_m = re.match(
                    r"СП\s*(\d+(?:\.\d+)*)",
                    title,
                )
                resolved_doc_id = (
                    f"СП {code_m.group(1)}" if code_m else title
                )
        result: list[dict] = []

        # Оборачиваем чанки в словари с метаданными
        for chunk_index, text in enumerate(blocks):
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

            result.append(
                {
                    "text": text,
                    "metadata": {
                        "doc_id": resolved_doc_id,
                        "chunk_index": chunk_index,
                        "first_item_number": first_item_number,
                        "clause_start": clause_start,
                        "clause_end": clause_end,
                        "section_path": section_path,
                        "clause_numbers": nums,
                        "clause_display": clause_display_str,
                        "merged_clauses_count": len(nums),
                        "content_type": "text",
                        "content_url": None,
                        "token_count": embedder.count_tokens(text),
                    },
                }
            )
        return result
