import subprocess
import sys
import time
from pathlib import Path

# Список этапов (запускаем только те, что являются самостоятельными скриптами)
PIPELINE_STEPS = [
    "scripts/02_pdf_to_markdown.py",   # Конвертация
    "scripts/03_clean_markdown.py",    # Очистка и JSON
    "scripts/10_supabase_writer.py",   # Метаданные (Каркас)
    "scripts/09_upsert_chunks_supb.py",# Чанки в Supabase
    "scripts/11_insert_to_qdrant.py"   # Векторы в Qdrant
]

def get_file_counts():
    """Считает количество файлов в ключевых папках для отчета."""
    pdfs = list(Path("data/pdfs").glob("*.pdf"))
    markdowns = list(Path("output/markdown").glob("*.md"))
    jsons = list(Path("output/json").glob("*.json"))
    return len(pdfs), len(markdowns), len(jsons)

def execute_step(step_path):
    print(f"\n--- 🛠 ЭТАП: {Path(step_path).name} ---")
    start = time.time()
    try:
        subprocess.run([sys.executable, step_path], check=True)
        print(f"✅ Успешно за {time.time() - start:.1f} сек.")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ ОШИБКА на этапе {step_path}. Пайплайн прерван.")
        return False

def main():
    print("🚀 СИСТЕМА ОБОГАЩЕНИЯ БАЗЫ ЗНАНИЙ СТАРТОВАЛА")
    
    # 1. Проверка наличия исходных файлов
    pdf_count, _, _ = get_file_counts()
    if pdf_count == 0:
        print("⚠️ В папке 'data/pdfs' нет файлов для обработки. Выход.")
        return

    print(f"📂 Найдено исходных документов (PDF): {pdf_count}")
    full_start = time.time()

    # 2. Запуск этапов
    for step in PIPELINE_STEPS:
        if not execute_step(step):
            sys.exit(1)

    # 3. Сбор финальной статистики
    _, md_count, json_count = get_file_counts()
    
    print("\n" + "="*40)
    print("🎉 ПАЙПЛАЙН УСПЕШНО ЗАВЕРШЕН!")
    print(f"⏱ Общее время работы: {(time.time() - full_start)/60:.1f} мин.")
    print("-" * 40)
    print(f"📈 ИТОГОВЫЙ ОТЧЕТ:")
    print(f"   - Обработано PDF: {pdf_count}")
    print(f"   - Создано Markdown: {md_count}")
    print(f"   - Сгенерировано JSON: {json_count}")
    print(f"   - Данные синхронизированы с Supabase и Qdrant.")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()