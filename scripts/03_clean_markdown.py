#!/usr/bin/env python3
"""
Скрипт 03_clean_markdown.py
Полная обработка документов: очистка + разбивка на секции + JSON
Вход: output/markdown/*.md
Выход:
- output/cleaned/СП_XX.XXX.XXXX.md (очищенный текст)
- output/json/СП_XX.XXX.XXXX.json (для САШИ)
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "output" / "markdown"
CLEANED_DIR = PROJECT_ROOT / "output" / "cleaned"
OUTPUT_DIR = PROJECT_ROOT / "output" / "json"
TOPICS_FILE = PROJECT_ROOT / "sp_topics.json"


def load_topics() -> Dict:
    """Загружает классификатор тематик СП из sp_topics.json"""
    if not TOPICS_FILE.exists():
        print(f"⚠️  Файл {TOPICS_FILE} не найден, тематики не будут определены")
        return {}
    try:
        with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            return _strip_json_recursive(raw_data)  # Автоочистка от пробелов
    except Exception as e:
        print(f"⚠️  Ошибка загрузки {TOPICS_FILE}: {e}")
        return {}

def get_topic_for_sp(sp_number: str, topics_data: Dict) -> str:
    """Определяет тематику СП по его номеру."""
    if not topics_data or not sp_number:
        return ""
    
    # 1. Точное соответствие в specific_topics (высший приоритет)
    specific = topics_data.get("specific_topics", {})
    if sp_number in specific:
        return specific[sp_number]
        
    # 2. Определяем по серии
    series_match = re.search(r'\.(\d{5})', sp_number)
    if series_match:
        series = series_match.group(1)
        topic_by_series = topics_data.get("topic_by_series", {})
        if series in topic_by_series:
            return topic_by_series[series]
        # Явные паттерны для пожарных серий
        if series in ("13130", "13150"):
            return "Пожарная безопасность"
            
    # 3. Извлекаем первую часть номера и определяем по диапазонам
    match = re.match(r'^(\d+)', sp_number)
    if match:
        sp_num = int(match.group(1))
        ranges = topics_data.get("sp_topics_by_range", {})
        for range_str, topic in ranges.items():
            try:
                start, end = map(int, range_str.split('-'))
                if start <= sp_num <= end:
                    return topic
            except ValueError:
                continue
                
    # 4. Тематика не определена
    return topics_data.get("default_topic", "Строительство")

def extract_metadata_from_text(text: str, filename: str, topics_data: Dict = None) -> Dict:
    """Извлекает метаданные из текста документа."""
    if topics_data is None:
        topics_data = {}
    metadata = {
        "type": "СП",
        "designation": "",
        "year": 0,
        "official_title": "",
        "valid_from": None,
        "is_mandatory": False,
        "topic": ""
    }
    search_text = text[:20000]
    
    # 1. Обозначение СП и год
    sp_patterns = [
        r'СП\s+(\d{1,3}\.\d{5}\.\d{4})',
        r'СП(\d{1,3}\.\d{5}\.\d{4})',
        r'СП\s*\n+\s*(\d{1,3}\.\d{5}\.\d{4})',
        r'Свод\s+правил\s+(\d{1,3}\.\d{5}\.\d{4})',
        r'СП.*?(\d{1,3}\.\d{5}\.\d{4})',
    ]
    for pattern in sp_patterns:
        sp_match = re.search(pattern, search_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
        if sp_match:
            designation = sp_match.group(1)
            metadata["designation"] = designation
            metadata["year"] = int(designation.split('.')[-1])
            print(f"    ✓ Найден номер СП: {designation}")
            break
            
    if not metadata["designation"]:
        metadata_from_filename = parse_filename_metadata(filename)
        metadata.update(metadata_from_filename)
        if metadata.get("designation"):
            print(f"    ✓ Номер из имени файла: {metadata['designation']}")
            
    if metadata["designation"]:
        sp_core = re.match(r'^(\d+\.\d+)', metadata["designation"])
        if sp_core:
            topic = get_topic_for_sp(sp_core.group(1), topics_data)
            metadata["topic"] = topic
            if topic:
                print(f"    ✓ Определена тематика: {topic}")
            else:
                print(f"    ⚠️ Тематика не определена для {sp_core.group(1)}")
        else:
            print(f"    ❌ Обозначение СП не найдено!")
            
    # 2. Полное название
    title_patterns = [
        r'СВОД\s+ПРАВИЛ\s*\n+\s*([А-ЯЁA-Z][А-ЯЁA-Z\s\-]+?)(?:\n|$)',
        r'СП\s*\d+\.\d+\.\d+\s*\n+\s*СВОД\s+ПРАВИЛ\s*\n+\s*([А-ЯЁA-Z][А-ЯЁA-Z\s\-]+?)(?:\n|$)',
        r'СП\s*\d+\.\d+\.\d+\s*\n+\s*([А-ЯЁA-Z][А-ЯЁA-Z\s\-]{5,80}?)(?:\n|$)',
    ]
    for pattern in title_patterns:
        match = re.search(pattern, search_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            title = re.sub(r'\s+', ' ', title)
            exclude_words = ['ПРЕДИСЛОВИЕ', 'ВВЕДЕНИЕ', 'СОДЕРЖАНИЕ', 'ОБЛАСТЬ', 'ИЗДАНИЕ', 'СВЕДЕНИЯ']
            if not any(word in title.upper() for word in exclude_words):
                metadata["official_title"] = title
                print(f"    ✓ Найдено название: {title[:50]}...")
                break
                
    if not metadata["official_title"]:
        metadata["official_title"] = parse_filename_metadata(filename).get("official_title", "")
        
    # 3. Дата введения
    date_patterns = [
        r'Дата\s+введения\s+(\d{4}\s*-\s*\d{2}\s*-\s*\d{2})',
        r'Дата\s+введения\s+(\d{2}\.\d{2}\.\d{4})',
        r'введен\s+в\s+действие\s+с\s+(\d{1,2}\s+[а-я]+\s+\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            if '-' in date_str:
                metadata["valid_from"] = re.sub(r'\s+', '', date_str)
            elif '.' in date_str:
                parts = date_str.split('.')
                if len(parts) == 3:
                    metadata["valid_from"] = f"{parts[2]}-{parts[1]}-{parts[0]}"
            print(f"    ✓ Найдена дата введения: {metadata['valid_from']}")
            break
            
    # 4. Обязательность
    if re.search(r'обязательный|обязательного|носит\s+обязательный', search_text, re.IGNORECASE):
        metadata["is_mandatory"] = True
        print(f"    ✓ Документ имеет обязательный характер")
        
    return metadata

def parse_filename_metadata(filename: str) -> Dict:
    """Извлечение метаданных из имени файла."""
    name = filename.replace('.md', '')
    patterns = [
        r'(СП|ГОСТ|СанПиН|СНиП|ТР\s+TS)\s+(\d+(?:\.\d+)*)\.(\d{4})_(.+)$',
        r'(СП|ГОСТ|СанПиН|СНиП|ТР_TS)_(\d+(?:\.\d+)*)\.(\d{4})_(.+)$',
        r'(SP|GOST)\s+(\d+(?:\.\d+)*)\.(\d{4})_(.+)$',
        r'.*?(\d{1,3}\.\d{5}\.\d{4}).*',
    ]
    for pattern in patterns:
        match = re.match(pattern, name, re.IGNORECASE)
        if match:
            if len(match.groups()) == 4:
                doc_type = match.group(1).replace('_', ' ').upper()
                if doc_type == 'SP': doc_type = 'СП'
                return {
                    "type": doc_type,
                    "designation": f"{match.group(2)}.{match.group(3)}",
                    "year": int(match.group(3)),
                    "official_title": match.group(4).replace('_', ' ')
                }
            elif len(match.groups()) == 1:
                designation = match.group(1)
                return {
                    "type": "СП",
                    "designation": designation,
                    "year": int(designation.split('.')[-1]),
                    "official_title": name.replace('_', ' ')
                }
    return {"type": "СП", "designation": "", "year": 0, "official_title": name.replace('_', ' ')}

def clean_text(text: str) -> str:
    """Базовая очистка текста."""
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    text = re.sub(r'(\w+)-\n\s+(\w+)', r'\1\2', text)
    
    lines = text.split('\n')
    cleaned_lines = []
    trash_patterns = [
        re.compile(p, re.IGNORECASE) for p in [
            r'^\s*\d+\s*$', r'СП\s+\d+\.\d+\.\d+\s*$',
            r'^\s*Страница\s+\d+\s*$', r'^\s*Издание официальное\s*$',
            r'^\s*Титульный лист\s*$', r'^\s*Предисловие\s*$',
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
    text = re.sub(r'\n\s*\n\s*\n+', '\n', text)
    return text.strip()

def extract_main_content(text: str) -> str:
    """Вырезает основной нормативный текст."""
    start_patterns = [r"^\s*1\.\s+Область\s+применения", r"^\s*1\s+Область\s+применения"]
    start_pos = None
    for pattern in start_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            start_pos = match.start()
            break
    if start_pos is None:
        match = re.search(r"^\s*1\s+[А-Я]", text, re.IGNORECASE | re.MULTILINE)
        if match: start_pos = match.start()
        else: return text
    text = text[start_pos:]
    
    end_patterns = [r"^\s*Приложение\s+[А-ЯA-Z]", r"^\s*Библиография"]
    end_pos = None
    for pattern in end_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            end_pos = match.start()
            break
    if end_pos: text = text[:end_pos]
    return text.strip()

def extract_sections(text: str) -> List[Dict]:
    """Разбивает текст на секции по заголовкам."""
    sections = []
    lines = text.split('\n')
    header_pattern = r'^\s*(\d+(?:\.\d+)*)\s+([А-ЯA-Z].+)$'
    current_section = None
    section_lines = []
    hierarchy = []
    
    for line in lines:
        match = re.match(header_pattern, line, re.IGNORECASE)
        if match:
            if current_section:
                current_section["content"] = '\n'.join(section_lines).strip()
                if current_section["content"]:
                    sections.append(current_section)
                section_lines = []
                
            section_code = match.group(1)
            section_title = match.group(2).strip()
            level = section_code.count('.') + 1
            
            while hierarchy and hierarchy[-1]["level"] >= level:
                hierarchy.pop()
            hierarchy.append({"level": level, "code": section_code, "title": section_title})
            
            path_parts = [f"{h['code']} {h['title']}" for h in hierarchy]
            current_section = {
                "section_code": section_code,
                "section_title": section_title,
                "level": level,
                "hierarchy_path": "/".join(path_parts),
                "content": ""
            }
            section_lines.append(line)
        else:
            if current_section:
                section_lines.append(line)
            elif line.strip():
                current_section = {
                    "section_code": None, "section_title": "Введение",
                    "level": 0, "hierarchy_path": "Введение", "content": ""
                }
                section_lines.append(line)
                
    if current_section:
        current_section["content"] = '\n'.join(section_lines).strip()
        if current_section["content"]:
            sections.append(current_section)
    return sections

def get_clean_filename(metadata: Dict, original_filename: str) -> str:
    if metadata.get("designation"):
        return f"СП_{metadata['designation'].replace('.', '_')}.md"
    name = original_filename.replace('.md', '')
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return f"{re.sub(r'\s+', '_', name)}_clean.md"

def process_document(md_file: Path, topics_data: Dict) -> Optional[Dict]:
    print(f"\n🔍 Обработка: {md_file.name}")
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    except UnicodeDecodeError:
        with open(md_file, 'r', encoding='cp1251') as f:
            raw_text = f.read()
    except Exception as e:
        print(f"  ❌ Ошибка чтения: {e}")
        return None

    metadata = extract_metadata_from_text(raw_text, md_file.name, topics_data)
    cleaned_text = clean_text(raw_text)
    main_text = extract_main_content(cleaned_text)
    if not main_text: main_text = cleaned_text
    
    sections = extract_sections(main_text)
    clean_filename = get_clean_filename(metadata, md_file.name)
    clean_file = CLEANED_DIR / clean_filename
    with open(clean_file, 'w', encoding='utf-8') as f:
        f.write(main_text)
    print(f"  📄 Очищенный текст: {clean_filename}")
    
    return {"document": {"filename": md_file.name, "metadata": metadata, "sections": sections}}

def process_all_documents(input_dir: Path = INPUT_DIR, cleaned_dir: Path = CLEANED_DIR, output_dir: Path = OUTPUT_DIR):
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        print(f"❌ Входная папка '{input_dir}' не существует!")
        return
        
    topics_data = load_topics()
    if topics_data: print("📚 Классификатор тематик загружен")
    
    md_files = list(input_dir.glob("*.md"))
    if not md_files:
        print(f"❌ Файлы .md не найдены в '{input_dir}'")
        return
        
    print(f"\n📁 Найдено файлов: {len(md_files)}")
    results = []
    
    for md_file in md_files:
        doc_data = process_document(md_file, topics_data)
        if not doc_data: continue
        
        metadata = doc_data["document"]["metadata"]
        sections = doc_data["document"]["sections"]
        
        json_filename = f"СП_{metadata['designation'].replace('.', '_')}.json" if metadata.get("designation") else md_file.stem + ".json"
        with open(output_dir / json_filename, 'w', encoding='utf-8') as f:
            json.dump(doc_data, f, ensure_ascii=False, indent=2)
            
        sections_count = len(sections)
        total_chars = sum(len(s["content"]) for s in sections)
        
        print(f"📋 Метаданные: {metadata['type']} | {metadata['designation']} | {metadata['year']} | Тема: {metadata['topic']}")
        print(f"📊 Секций: {sections_count} | Символов: {total_chars:,} | 💾 {json_filename}")
        
        results.append({"file": md_file.name, "designation": metadata.get("designation", ""), "topic": metadata.get("topic", ""), "sections": sections_count, "chars": total_chars})

    print("\n" + "=" * 60)
    print(f"📊 ИТОГО: Обработано {len(results)} документов")
    print(f"📁 Результаты сохранены в: {cleaned_dir} и {output_dir}")

if __name__ == "__main__":
    print("=" * 60)
    print("📦 ПОЛНАЯ ОБРАБОТКА ДОКУМЕНТОВ")
    print("=" * 60)
    process_all_documents()
    print("\n✅ ГОТОВО!")