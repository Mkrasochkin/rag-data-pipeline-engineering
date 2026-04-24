import os
import re
from pathlib import Path
from docling.document_converter import DocumentConverter

def clean_text(text):
    """Схлопывает повторяющиеся слова и лишние пустые строки."""
    # Схлопываем "область область" -> "область"
    text = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)
    # Убираем лишние пустые строки (больше двух подряд)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def convert_pdfs_to_md(input_dir: str, output_dir: str):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Создаем папку для markdown, если ее еще нет
    output_path.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter()
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ PDF файлы не найдены в {input_dir}")
        return

    print(f"🔍 Найдено файлов: {len(pdf_files)}. Начинаю конвертацию...")

    for pdf_file in pdf_files:
        try:
            # Формируем путь для сохранения в папку output/markdown/
            output_file = output_path / f"{pdf_file.stem}.md"
            
            if output_file.exists():
                print(f"⏩ Пропуск: {output_file.name} уже существует.")
                continue

            print(f"⚙️ Обработка: {pdf_file.name}...")
            result = converter.convert(pdf_file)
            md_content = result.document.export_to_markdown()
            
            # Применяем очистку
            cleaned_md = clean_text(md_content)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(cleaned_md)
                
            print(f"✅ Готово! Сохранено в: {output_file}")
            
        except Exception as e:
            print(f"⚠️ Ошибка при обработке {pdf_file.name}: {e}")

if __name__ == "__main__":
    # Указываем пути строго по твоей новой схеме
    # Берем из корня проекта (так как запускаем из корня)
    BASE_DIR = Path(__file__).parent.parent
    
    INPUT_PDF_DIR = BASE_DIR / "data" / "pdfs"
    OUTPUT_MD_DIR = BASE_DIR / "output" / "markdown"
    
    convert_pdfs_to_md(INPUT_PDF_DIR, OUTPUT_MD_DIR)

