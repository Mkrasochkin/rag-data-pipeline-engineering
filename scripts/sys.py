# diagnostic_check.py
import struct
import platform
import psutil
import os
import sys

print("=" * 60)
print("🔍 ДИАГНОСТИКА СИСТЕМЫ")
print("=" * 60)

# Информация о системе
print(f"\n🖥️ Система: {platform.system()} {platform.release()}")
print(f"💻 Процессор: {platform.processor()}")

# Проверка архитектуры Python
python_bits = struct.calcsize('P') * 8
print(f"\n🐍 Python {platform.python_version()} ({python_bits}-bit)")
print(f"📍 Расположение: {sys.executable}")

# Проверка RAM
memory = psutil.virtual_memory()
print(f"\n💾 Оперативная память:")
print(f"  Всего: {memory.total / 1024**3:.2f} GB")
print(f"  Доступно: {memory.available / 1024**3:.2f} GB")
print(f"  Используется: {memory.percent}%")

# Проверка виртуальной памяти
swap = psutil.swap_memory()
print(f"\n📄 Файл подкачки:")
print(f"  Всего: {swap.total / 1024**3:.2f} GB")
print(f"  Доступно: {swap.free / 1024**3:.2f} GB")

# Проверка текущего процесса
process = psutil.Process(os.getpid())
print(f"\n📈 Текущий процесс:")
print(f"  RAM используется: {process.memory_info().rss / 1024**2:.2f} MB")
print(f"  Пиковое использование: {process.memory_info().peak_wset / 1024**2:.2f} MB")

# Проверка лимитов памяти (Windows)
if platform.system() == "Windows":
    try:
        import ctypes
        import ctypes.wintypes
        
        # Проверка лимита памяти процесса
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.wintypes.DWORD),
                ('dwMemoryLoad', ctypes.wintypes.DWORD),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]
        
        mem_status = MEMORYSTATUSEX()
        mem_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status))
        
        print(f"\n🪟 Windows лимиты памяти:")
        print(f"  Виртуальная доступно: {mem_status.ullAvailVirtual / 1024**3:.2f} GB")
        
        # Проверка лимита адресного пространства
        if python_bits == 32:
            print(f"\n⚠️ ВАЖНО: У вас {python_bits}-битный Python!")
            print(f"  Максимум RAM на процесс: 2-4 GB")
            print(f"  Это объясняет проблему с большими PDF!")
            print(f"  Решение: Установите 64-битный Python с python.org")
        else:
            print(f"✅ Архитектура Python корректная ({python_bits}-bit)")
            
    except Exception as e:
        print(f"  Не удалось получить Windows-специфичные данные: {e}")

# Проверка важных библиотек
print(f"\n📦 Версии ключевых библиотек:")
packages = ['torch', 'docling', 'numpy', 'PyPDF2', 'pypdf']
for package in packages:
    try:
        module = __import__(package)
        version = getattr(module, '__version__', 'неизвестно')
        print(f"  {package}: {version}")
    except ImportError:
        print(f"  {package}: не установлен")

print("\n" + "=" * 60)
print("Диагностика завершена!")
print("=" * 60)