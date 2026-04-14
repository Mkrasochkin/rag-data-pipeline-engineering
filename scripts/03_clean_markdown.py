#!/usr/bin/env python3
"""
Скрипт 03_process_documents.py
Полная обработка документов: очистка + разбивка на секции + JSON

Вход: output/markdown/*.md
Выход: 
  - output/cleaned/СП_XX.XXX.XXXX.md (очищенный текст)
  - output/json/СП_XX.XXX.XXXX.json (для САШИ)

Извлекает из текста:
- official_title (из "СВОД ПРАВИЛ")
- valid_from (из "Дата введения")
- designation, year, type (из текста или имени файла)
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "output" / "markdown"
CLEANED_DIR = PROJECT_ROOT / "output" / "cleaned"
OUTPUT_DIR = PROJECT_ROOT / "output" / "json"

def extract_metadata_from_text(text: str, filename: str) -> Dict:
    """
    Извлекает метаданные из текста документа.
    Приоритет: текст > имя файла
    """
    metadata = {
        "type": "СП",
        "designation": "",
        "year": 0,
        "official_title": "",
        "valid_from": None,
        "is_mandatory": False
    }
    
    # Ищем в первых 15000 символах
    search_text = text[:15000]
    
    # 1. Извлекаем обозначение СП и год
    # "СП 48.13330.2019" или "СП 113.13330.2023"
    sp_match = re.search(
        r'СП\s+(\d{1,3}\.\d{5}\.\d{4})',
        search_text,
        re.IGNORECASE
    )
    
    if sp_match:
        designation = sp_match.group(1)
        metadata["designation"] = designation
        metadata["year"] = int(designation.split('.')[-1])
    else:
        # Пробуем найти "Свод правил XX.XXX.XXXX"
        sp_match = re.search(
            r'Свод\s+правил\s+(\d{1,3}\.\d{5}\.\d{4})',
            search_text,
            re.IGNORECASE
        )
        if sp_match:
            designation = sp_match.group(1)
            metadata["designation"] = designation
            metadata["year"] = int(designation.split('.')[-1])
        else:
            # Если не нашли в тексте, пробуем из имени файла
            metadata_from_filename = parse_filename_metadata(filename)
            metadata.update(metadata_from_filename)
    
    # 2. Извлекаем полное название из "СВОД ПРАВИЛ"
    # Ищем: "СВОД ПРАВИЛ\n\nОРГАНИЗАЦИЯ СТРОИТЕЛЬСТВА"
    title_patterns = [
        # После "СВОД ПРАВИЛ" с пустыми строками
        r'СВОД\s+ПРАВИЛ\s*\n+\s*([А-ЯЁA-Z][А-ЯЁA-Z\s]+?)(?:\n|$)',
        # После номера СП и "СВОД ПРАВИЛ"
        r'СП\s+\d+\.\d+\.\d+\s*\n+\s*СВОД\s+ПРАВИЛ\s*\n+\s*([А-ЯЁA-Z][А-ЯЁA-Z\s]+?)(?:\n|$)',
        # Просто текст в верхнем регистре после номера СП
        r'СП\s+\d+\.\d+\.\d+\s*\n+\s*([А-ЯЁA-Z][А-ЯЁA-Z\s]{5,50}?)(?:\n|$)',
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, search_text, re.IGNORECASE | re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Очищаем от лишних пробелов и переносов
            title = re.sub(r'\s+', ' ', title)
            # Проверяем, что это не служебный раздел
            exclude_words = ['ПРЕДИСЛОВИЕ', 'ВВЕДЕНИЕ', 'СОДЕРЖАНИЕ', 'ОБЛАСТЬ', 'ИЗДАНИЕ']
            if not any(word in title.upper() for word in exclude_words):
                metadata["official_title"] = title
                break
    
    # Если не нашли в тексте, берем из имени файла
    if not metadata["official_title"]:
        filename_meta = parse_filename_metadata(filename)
        metadata["official_title"] = filename_meta.get("official_title", "")
    
    # 3. Извлекаем дату введения
    date_patterns = [
        r'Дата\s+введения\s+(\d{4}\s*-\s*\d{2}\s*-\s*\d{2})',
        r'Дата\s+введения\s+(\d{2}\.\d{2}\.\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            # Приводим к формату YYYY-MM-DD
            if '-' in date_str:
                # Уже в нужном формате, убираем пробелы
                date_str = re.sub(r'\s+', '', date_str)
                metadata["valid_from"] = date_str
            elif '.' in date_str:
                # Конвертируем DD.MM.YYYY -> YYYY-MM-DD
                parts = date_str.split('.')
                if len(parts) == 3:
                    metadata["valid_from"] = f"{parts[2]}-{parts[1]}-{parts[0]}"
            break
    
    # 4. Определяем обязательность
    if re.search(r'обязательный|обязательного|носит\s+обязательный', search_text, re.IGNORECASE):
        metadata["is_mandatory"] = True
    
    return metadata

def parse_filename_metadata(filename: str) -> Dict:
    """
    Извлечение метаданных из имени файла (запасной вариант).
    Примеры:
    - "СП 113.13330.2023_Стоянки автомобилей.md"
    - "СП_48.13330.2019_Организация_строительства.md"
    """
    name = filename.replace('.md', '')
    
    # Паттерны для разных форматов имен
    patterns = [
        r'(СП|ГОСТ|СанПиН|СНиП|ТР\s+ТС)\s+(\d+(?:\.\d+)*)\.(\d{4})_(.+)$',
        r'(СП|ГОСТ|СанПиН|СНиП|ТР_ТС)_(\d+(?:\.\d+)*)\.(\d{4})_(.+)$',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, name, re.IGNORECASE)
        if match:
            doc_type = match.group(1).replace('_', ' ')
            return {
                "type": doc_type,
                "designation": f"{match.group(2)}.{match.group(3)}",
                "year": int(match.group(3)),
                "official_title": match.group(4).replace('_', ' ')
            }
    
    return {
        "type": "СП",
        "designation": "",
        "year": 0,
        "official_title": name.replace('_', ' ')
    }

def clean_text(text: str) -> str:
    """
    Базовая очистка текста:
    1. Склеивание переносов
    2. Удаление колонтитулов
    3. Удаление лишних пустых строк
    """
    # Склеивание слов с переносами
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    text = re.sub(r'(\w+)-\n\s+(\w+)', r'\1\2', text)

    # Удаление колонтитулов и мусорных строк
    lines = text.split('\n')
    cleaned_lines = []
    
    trash_patterns = [
        re.compile(p, re.IGNORECASE) for p in [
            r'^\s*\d+\s*$',                 # Номер страницы
            r'СП\s+\d+\.\d+\.\d+\s*$',      # Обозначение в колонтитуле
            r'^\s*Страница\s+\d+\s*$',      # "Страница N"
            r'^\s*Издание официальное\s*$', # Служебная надпись
            r'^\s*Титульный лист\s*$',      # Заголовок титула
            r'^\s*Предисловие\s*$',         # Заголовок предисловия
        ]
    ]

    for line in lines:
        if any(p.search(line) for p in trash_patterns):
            continue
            
        stripped = line.strip()
        if len(stripped) <= 3 and not re.match(r'^[а-я]\)$|^\d+\.?$', stripped):
            continue
                
        cleaned_lines.append(line)
            
    text = '\n'.join(cleaned_lines)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    return text.strip()

def extract_main_content(text: str) -> str:
    """
    Вырезает основной нормативный текст:
    - От "1. Область применения"
    - До "Приложение" или "Библиография"
    """
    
    # Находим начало - "1. Область применения"
    start_patterns = [
        r"^\s*1\.\s+Область\s+применения",
        r"^\s*1\s+Область\s+применения",
    ]
    
    start_pos = None
    for pattern in start_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            start_pos = match.start()
            break
    
    if start_pos is None:
        # Пробуем найти любой раздел с номером 1
        match = re.search(r"^\s*1\s+[А-Я]", text, re.IGNORECASE | re.MULTILINE)
        if match:
            start_pos = match.start()
        else:
            return text
    
    text = text[start_pos:]
    
    # Находим конец - "Приложение" или "Библиография"
    end_patterns = [
        r"^\s*Приложение\s+[А-ЯA-Z]",
        r"^\s*Библиография",
    ]
    
    end_pos = None
    for pattern in end_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            end_pos = match.start()
            break
    
    if end_pos:
        text = text[:end_pos]
    
    return text.strip()

def extract_sections(text: str) -> List[Dict]:
    """
    Разбивает текст на секции по заголовкам.
    Заголовки определяются по номерам разделов в начале строки.
    """
    sections = []
    lines = text.split('\n')
    
    # Паттерн для поиска заголовков разделов
    # Примеры: "1 Область применения", "5.26 Уклоны рамп"
    header_pattern = r'^\s*(\d+(?:\.\d+)*)\s+([А-ЯA-Z].+)$'
    
    current_section = None
    section_lines = []
    
    # Стек для отслеживания иерархии
    hierarchy = []
    
    for line in lines:
        match = re.match(header_pattern, line, re.IGNORECASE)
        
        if match:
            # Сохраняем предыдущую секцию
            if current_section:
                current_section["content"] = '\n'.join(section_lines).strip()
                if current_section["content"]:
                    sections.append(current_section)
                section_lines = []
            
            section_code = match.group(1)
            section_title = match.group(2).strip()
            
            # Определяем уровень вложенности
            level = section_code.count('.') + 1
            
            # Обновляем иерархию
            while hierarchy and hierarchy[-1]["level"] >= level:
                hierarchy.pop()
            
            hierarchy.append({
                "level": level,
                "code": section_code,
                "title": section_title
            })
            
            # Строим hierarchy_path через слеш
            path_parts = [f"{h['code']} {h['title']}" for h in hierarchy]
            hierarchy_path = "/".join(path_parts)
            
            current_section = {
                "section_code": section_code,
                "section_title": section_title,
                "level": level,
                "hierarchy_path": hierarchy_path,
                "content": ""
            }
            
            section_lines.append(line)
        else:
            if current_section:
                section_lines.append(line)
            elif line.strip():
                # Текст до первого заголовка
                current_section = {
                    "section_code": None,
                    "section_title": "Введение",
                    "level": 0,
                    "hierarchy_path": "Введение",
                    "content": ""
                }
                section_lines.append(line)
    
    # Сохраняем последнюю секцию
    if current_section:
        current_section["content"] = '\n'.join(section_lines).strip()
        if current_section["content"]:
            sections.append(current_section)
    
    return sections

def get_clean_filename(metadata: Dict, original_filename: str) -> str:
    """
    Формирует имя файла для очищенного текста.
    Пример: СП_48.13330.2019.md
    """
    if metadata.get("designation"):
        # Убираем точки из обозначения для имени файла
        designation = metadata["designation"].replace('.', '_')
        return f"СП_{designation}.md"
    else:
        # Запасной вариант - берем из оригинального имени
        name = original_filename.replace('.md', '')
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = re.sub(r'\s+', '_', name)
        return f"{name}_clean.md"

def process_document(md_file: Path) -> Optional[Dict]:
    """
    Полная обработка одного документа.
    Возвращает данные для JSON и сохраняет очищенный текст.
    """
    print(f"🔍 Обработка: {md_file.name}")
    
    # Чтение
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    except UnicodeDecodeError:
        with open(md_file, 'r', encoding='cp1251') as f:
            raw_text = f.read()
    except Exception as e:
        print(f"  ❌ Ошибка чтения: {e}")
        return None
    
    # 1. Извлечение метаданных из ПОЛНОГО текста (до очистки)
    metadata = extract_metadata_from_text(raw_text, md_file.name)
    
    # 2. Базовая очистка текста
    cleaned_text = clean_text(raw_text)
    
    # 3. Извлечение основного контента (для секций)
    main_text = extract_main_content(cleaned_text)
    
    if not main_text:
        print(f"  ⚠️  Не найден основной контент")
        main_text = cleaned_text
    
    # 4. Разбивка на секции
    sections = extract_sections(main_text)
    
    # 5. Сохранение очищенного текста
    clean_filename = get_clean_filename(metadata, md_file.name)
    clean_file = CLEANED_DIR / clean_filename
    
    with open(clean_file, 'w', encoding='utf-8') as f:
        f.write(main_text)
    
    print(f"  📄 Очищенный текст: {clean_filename}")
    
    # 6. Формирование итоговой структуры для JSON
    return {
        "document": {
            "filename": md_file.name,
            "metadata": metadata,
            "sections": sections
        }
    }

def process_all_documents(
    input_dir: Path = INPUT_DIR,
    cleaned_dir: Path = CLEANED_DIR,
    output_dir: Path = OUTPUT_DIR
):
    """
    Обрабатывает все документы и создает:
    1. Очищенные MD-файлы в cleaned/
    2. JSON-файлы в json/
    """
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        print(f"❌ Входная папка '{input_dir}' не существует!")
        return
    
    md_files = list(input_dir.glob("*.md"))
    if not md_files:
        print(f"❌ Файлы .md не найдены в '{input_dir}'")
        return
    
    print(f"📁 Найдено файлов: {len(md_files)}")
    print(f"📂 Вход:  {input_dir}")
    print(f"📂 Очищенные: {cleaned_dir}")
    print(f"📂 JSON: {output_dir}")
    print("-" * 60)
    
    results = []
    
    for md_file in md_files:
        # Обработка документа
        doc_data = process_document(md_file)
        
        if not doc_data:
            print(f"  ❌ Пропущен\n")
            continue
        
        metadata = doc_data["document"]["metadata"]
        sections = doc_data["document"]["sections"]
        
        # Сохранение JSON
        if metadata.get("designation"):
            json_filename = f"СП_{metadata['designation'].replace('.', '_')}.json"
        else:
            json_filename = md_file.stem + ".json"
        
        json_file = output_dir / json_filename
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(doc_data, f, ensure_ascii=False, indent=2)
        
        # Статистика
        sections_count = len(sections)
        total_chars = sum(len(s["content"]) for s in sections)
        
        # Подсчет таблиц
        tables_count = 0
        for section in sections:
            if '|' in section["content"] and '---' in section["content"]:
                tables_count += 1
        
        print(f"  📋 Метаданные:")
        print(f"     - Тип: {metadata.get('type', '—')}")
        print(f"     - Обозначение: {metadata.get('designation', '—')}")
        print(f"     - Название: {metadata.get('official_title', '—')}")
        print(f"     - Дата введения: {metadata.get('valid_from', '—')}")
        print(f"     - Обязательный: {'Да' if metadata.get('is_mandatory') else 'Нет'}")
        print(f"  📊 Секций: {sections_count}")
        print(f"  📊 Объем: {total_chars:,} символов")
        if tables_count > 0:
            print(f"  📊 Таблиц: {tables_count}")
        print(f"  💾 JSON: {json_file}")
        print()
        
        results.append({
            "file": md_file.name,
            "designation": metadata.get("designation", ""),
            "title": metadata.get("official_title", ""),
            "sections": sections_count,
            "chars": total_chars,
            "tables": tables_count
        })
    
    # Итоговая статистика
    print("-" * 60)
    print(f"📊 ИТОГО:")
    print(f"  - Обработано документов: {len(results)}")
    print(f"  - Всего секций: {sum(r['sections'] for r in results)}")
    print(f"  - Всего символов: {sum(r['chars'] for r in results):,}")
    print(f"  - Всего таблиц: {sum(r['tables'] for r in results)}")
    
    print("\n📁 Результаты:")
    print(f"  - Очищенные MD: {cleaned_dir}")
    print(f"  - JSON для САШИ: {output_dir}")

if __name__ == "__main__":
    print("=" * 60)
    print("📦 ПОЛНАЯ ОБРАБОТКА ДОКУМЕНТОВ")
    print("=" * 60)
    process_all_documents()
    print("\n✅ ГОТОВО!")
    print("💡 Очищенные MD: output/cleaned/")
    print("💡 JSON для САШИ: output/json/")