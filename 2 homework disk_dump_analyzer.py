#!/usr/bin/env python3
"""
Полное решение задачи анализа FAT16 раздела
Создание диска с разными разделами, форматирование FAT16,
снятие дампа и анализ корневого каталога
"""

import struct
import os
import sys
import subprocess
from datetime import datetime

class FAT16DiskAnalyzer:
    def __init__(self, disk_size_mb=100):
        self.disk_size = disk_size_mb * 1024 * 1024
        self.sector_size = 512
        self.disk_image = "multipartition_disk.img"
        
    def create_partitioned_disk(self):
        """Создание диска с тремя разделами разных типов"""
        print("="*70)
        print("СОЗДАНИЕ ДИСКА С РАЗНЫМИ РАЗДЕЛАМИ")
        print("="*70)
        
        # 1. Создаем пустой образ диска
        print(f"Создаю диск {self.disk_image} размером {self.disk_size//(1024*1024)}MB...")
        with open(self.disk_image, 'wb') as f:
            f.write(b'\x00' * self.disk_size)
        
        # 2. Создаем MBR с таблицей разделов
        self.create_mbr_with_partitions()
        
        # 3. Форматируем первый раздел в FAT16
        self.format_fat16_partition()
        
        # 4. Создаем тестовые файлы
        self.create_test_files()
        
        print(f"\n✓ Диск создан: {self.disk_image}")
        
    def create_mbr_with_partitions(self):
        """Создание MBR с таблицей разделов"""
        mbr = bytearray(512)
        
        # Загрузочный код (NOP)
        mbr[0] = 0xEB
        mbr[1] = 0x3C
        mbr[2] = 0x90
        
        # OEM Name
        mbr[3:11] = b'ANALYZER '
        
        # Таблица разделов (4 записи по 16 байт)
        # Раздел 1: FAT16 (тип 0x0E)
        # Смещение 446
        mbr[446] = 0x80  # Активный раздел
        
        # CHS начала (C=0, H=1, S=1)
        mbr[447] = 0x01  # Головка
        mbr[448] = 0x01  # Сектор
        mbr[449] = 0x00  # Цилиндр
        
        mbr[450] = 0x0E  # FAT16 (LBA)
        
        # CHS конца
        mbr[451] = 0xFE  # Головка
        mbr[452] = 0xFF  # Сектор  
        mbr[453] = 0xFF  # Цилиндр
        
        # LBA начало (сектор 2048 = 1MB отступ)
        lba_start1 = 2048
        mbr[454:458] = struct.pack('<I', lba_start1)
        
        # Размер раздела (50MB в секторах)
        sectors1 = (50 * 1024 * 1024) // self.sector_size
        mbr[458:462] = struct.pack('<I', sectors1)
        
        # Раздел 2: Linux (тип 0x83)
        # Смещение 462
        mbr[462] = 0x00  # Неактивный
        
        # CHS начала
        mbr[463] = 0xFE
        mbr[464] = 0xFF
        mbr[465] = 0xFF
        
        mbr[466] = 0x83  # Linux
        
        # CHS конца
        mbr[467] = 0xFE
        mbr[468] = 0xFF
        mbr[469] = 0xFF
        
        # LBA начало раздела 2
        lba_start2 = lba_start1 + sectors1
        mbr[470:474] = struct.pack('<I', lba_start2)
        
        # Размер раздела 2 (30MB)
        sectors2 = (30 * 1024 * 1024) // self.sector_size
        mbr[474:478] = struct.pack('<I', sectors2)
        
        # Раздел 3: FAT32 (тип 0x0B)
        # Смещение 478
        mbr[478] = 0x00  # Неактивный
        
        # CHS начала
        mbr[479] = 0xFE
        mbr[480] = 0xFF
        mbr[481] = 0xFF
        
        mbr[482] = 0x0B  # FAT32
        
        # CHS конца
        mbr[483] = 0xFE
        mbr[484] = 0xFF
        mbr[485] = 0xFF
        
        # LBA начало раздела 3
        lba_start3 = lba_start2 + sectors2
        mbr[486:490] = struct.pack('<I', lba_start3)
        
        # Размер раздела 3 (остаток)
        total_sectors = self.disk_size // self.sector_size
        sectors3 = total_sectors - lba_start3
        mbr[490:494] = struct.pack('<I', sectors3)
        
        # Сигнатура MBR
        mbr[510] = 0x55
        mbr[511] = 0xAA
        
        # Записываем MBR
        with open(self.disk_image, 'r+b') as f:
            f.write(mbr)
        
        print(f"✓ MBR создана с тремя разделами:")
        print(f"  1. FAT16: LBA {lba_start1}, {sectors1} секторов")
        print(f"  2. Linux: LBA {lba_start2}, {sectors2} секторов")  
        print(f"  3. FAT32: LBA {lba_start3}, {sectors3} секторов")
        
    def format_fat16_partition(self):
        """Форматирование первого раздела в FAT16"""
        print("\nФорматирование первого раздела в FAT16...")
        
        # Создаем загрузочный сектор FAT16
        boot = bytearray(512)
        
        # Jump instruction
        boot[0] = 0xEB
        boot[1] = 0x3C
        boot[2] = 0x90
        
        # OEM Name
        boot[3:11] = b'MYFAT16  '
        
        # BPB (BIOS Parameter Block)
        boot[11:13] = struct.pack('<H', 512)      # Bytes per sector
        boot[13] = 4                              # Sectors per cluster (2KB clusters)
        boot[14:16] = struct.pack('<H', 1)        # Reserved sectors
        boot[16] = 2                              # Number of FATs
        boot[17:19] = struct.pack('<H', 512)      # Root directory entries
        boot[19:21] = struct.pack('<H', 0)        # Total sectors 16-bit (0 = use 32-bit)
        boot[21] = 0xF8                           # Media descriptor
        boot[22:24] = struct.pack('<H', 200)      # Sectors per FAT
        
        # Extended BPB
        boot[24:26] = struct.pack('<H', 32)       # Sectors per track
        boot[26:28] = struct.pack('<H', 64)       # Number of heads
        boot[28:32] = struct.pack('<I', 0)        # Hidden sectors
        boot[32:36] = struct.pack('<I', 102400)   # Total sectors 32-bit (50MB)
        
        # Boot code
        boot[36:62] = b'\x00' * 26
        boot[62] = 0x29                           # Extended boot signature
        
        # Volume serial number (генерация из текущего времени)
        import time
        serial = int(time.time())
        boot[63:67] = struct.pack('<I', serial)
        
        # Volume label
        boot[67:79] = b'FAT16_VOLUME '
        
        # File system type
        boot[82:90] = b'FAT16   '
        
        # Boot sector signature
        boot[510] = 0x55
        boot[511] = 0xAA
        
        # Записываем загрузочный сектор в начало раздела
        partition_start = 2048 * 512
        with open(self.disk_image, 'r+b') as f:
            f.seek(partition_start)
            f.write(boot)
        
        # Создаем FAT таблицы
        fat_size = 200 * 512  # 200 секторов на FAT
        fat = bytearray(fat_size)
        
        # Первые 2 записи FAT
        fat[0] = 0xF8  # Media descriptor
        fat[1] = 0xFF
        fat[2] = 0xFF  # Конец цепочки
        fat[3] = 0xFF
        
        # Записываем первую FAT
        fat1_offset = partition_start + 512  # После загрузочного сектора
        with open(self.disk_image, 'r+b') as f:
            f.seek(fat1_offset)
            f.write(fat)
            
            # Копируем для второй FAT
            f.seek(fat1_offset + fat_size)
            f.write(fat)
        
        print("✓ Раздел отформатирован в FAT16")
        
    def create_test_files(self):
        """Создание тестовых файлов в FAT16 разделе"""
        print("\nСоздание тестовых файлов в корневом каталоге...")
        
        # Корневой каталог начинается после двух FAT таблиц
        root_dir_offset = (2048 * 512) + 512 + (200 * 512 * 2)
        
        # Создаем записи каталога
        files = [
            ("README  ", "TXT", 0x20, b"Welcome to FAT16 analyzer\nCreated: " + 
             datetime.now().strftime("%Y-%m-%d %H:%M:%S").encode()),
            ("CONFIG  ", "INI", 0x20, b"[Settings]\nVersion=1.0\nType=FAT16\n"),
            ("DATA    ", "BIN", 0x20, bytes(range(256)) * 4),  # 1KB данных
            ("DOCS    ", "", 0x10, b""),  # Директория
            ("SYSTEM  ", "SYS", 0x04, b"System file"),  # Системный файл
        ]
        
        with open(self.disk_image, 'r+b') as f:
            f.seek(root_dir_offset)
            
            for i, (name, ext, attr, data) in enumerate(files):
                entry = self.create_directory_entry(name, ext, attr, data, i+2)
                f.write(entry)
                
                # Записываем данные файла (для не-директорий)
                if attr != 0x10 and data:  # Не директория и есть данные
                    # Данные начинаются с кластера 2
                    cluster_size = 4 * 512  # 4 сектора по 512 байт
                    data_offset = root_dir_offset + (512 * 32 * 512 // 512)  # После каталога
                    data_offset += (i * cluster_size)  # Каждый файл в своем кластере
                    
                    f.seek(data_offset)
                    f.write(data[:cluster_size])
        
        print(f"✓ Создано {len(files)} файлов/директорий")
        
    def create_directory_entry(self, name, ext, attributes, data, first_cluster):
        """Создание записи в каталоге FAT16"""
        entry = bytearray(32)
        
        # Имя (8 символов)
        entry[0:8] = name.encode('ascii')
        
        # Расширение (3 символа)
        entry[8:11] = ext.encode('ascii')
        
        # Атрибуты
        entry[11] = attributes
        
        # Резервные байты
        entry[12:22] = b'\x00' * 10
        
        # Время создания
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        second = now.second // 2  # FAT хранит секунды/2
        
        time_word = (hour << 11) | (minute << 5) | second
        entry[22:24] = struct.pack('<H', time_word)
        
        # Дата создания
        year = now.year - 1980
        month = now.month
        day = now.day
        
        date_word = (year << 9) | (month << 5) | day
        entry[24:26] = struct.pack('<H', date_word)
        
        # Дата последнего доступа
        entry[26:28] = struct.pack('<H', date_word)
        
        # Начальный кластер (High 16 bits для FAT32, для FAT16 = 0)
        entry[20:22] = struct.pack('<H', 0)
        
        # Время последней модификации
        entry[22:24] = struct.pack('<H', time_word)
        entry[24:26] = struct.pack('<H', date_word)
        
        # Начальный кластер (Low 16 bits)
        entry[26:28] = struct.pack('<H', first_cluster)
        
        # Размер файла
        file_size = len(data) if attributes != 0x10 else 0  # Для директорий размер = 0
        entry[28:32] = struct.pack('<I', file_size)
        
        return entry
    
    def create_dump(self, dump_name="fat16_dump.bin"):
        """Создание дампа FAT16 раздела"""
        print("\n" + "="*70)
        print("СОЗДАНИЕ ДАМПА FAT16 РАЗДЕЛА")
        print("="*70)
        
        # Читаем смещение первого раздела из MBR
        with open(self.disk_image, 'rb') as f:
            f.seek(454)  # LBA начала первого раздела
            lba_start = struct.unpack('<I', f.read(4))[0]
            
            f.seek(458)  # Размер первого раздела
            sectors = struct.unpack('<I', f.read(4))[0]
        
        offset = lba_start * self.sector_size
        size = sectors * self.sector_size
        
        print(f"Первый раздел (FAT16):")
        print(f"  LBA начало: {lba_start}")
        print(f"  Секторов: {sectors}")
        print(f"  Смещение в файле: {offset:,} байт")
        print(f"  Размер: {size:,} байт ({size/(1024*1024):.1f} MB)")
        
        # Создаем дамп
        with open(self.disk_image, 'rb') as src, open(dump_name, 'wb') as dst:
            src.seek(offset)
            
            # Читаем и записываем по 1MB
            chunk_size = 1024 * 1024
            total_read = 0
            
            while total_read < size:
                chunk = src.read(min(chunk_size, size - total_read))
                if not chunk:
                    break
                    
                dst.write(chunk)
                total_read += len(chunk)
        
        print(f"\n✓ Дамп создан: {dump_name}")
        print(f"  Размер дампа: {total_read:,} байт")
        
        return dump_name
    
    def analyze_root_directory(self, dump_file):
        """Анализ корневого каталога из дампа"""
        print("\n" + "="*70)
        print("АНАЛИЗ КОРНЕВОГО КАТАЛОГА FAT16")
        print("="*70)
        
        with open(dump_file, 'rb') as f:
            # Читаем загрузочный сектор из дампа
            boot = f.read(512)
            
            # Парсим BPB
            bytes_per_sector = struct.unpack('<H', boot[11:13])[0]
            sectors_per_cluster = boot[13]
            reserved_sectors = struct.unpack('<H', boot[14:16])[0]
            num_fats = boot[16]
            root_entries = struct.unpack('<H', boot[17:19])[0]
            sectors_per_fat = struct.unpack('<H', boot[22:24])[0]
            
            # Рассчитываем смещения
            fat_size = sectors_per_fat * bytes_per_sector
            root_dir_offset = reserved_sectors * bytes_per_sector + num_fats * fat_size
            root_dir_size = root_entries * 32
            
            print("Параметры FAT16:")
            print(f"  Байт в секторе: {bytes_per_sector}")
            print(f"  Секторов в кластере: {sectors_per_cluster}")
            print(f"  Размер кластера: {sectors_per_cluster * bytes_per_sector} байт")
            print(f"  FAT таблиц: {num_fats}")
            print(f"  Секторов на FAT: {sectors_per_fat}")
            print(f"  Записей в корневом каталоге: {root_entries}")
            print(f"  Смещение корневого каталога: {root_dir_offset:,} байт")
            
            # Переходим к корневому каталогу
            f.seek(root_dir_offset)
            
            print(f"\nСодержимое корневого каталога ({root_entries} записей):")
            print("-"*80)
            
            entries_found = 0
            for i in range(root_entries):
                entry = f.read(32)
                if len(entry) < 32:
                    break
                
                # Проверяем первый байт
                first_byte = entry[0]
                
                if first_byte == 0x00:
                    # Конец каталога
                    break
                elif first_byte == 0xE5:
                    # Удаленная запись
                    continue
                
                # Парсим запись
                self.parse_and_print_directory_entry(entry, i, bytes_per_sector, sectors_per_cluster)
                entries_found += 1
            
            print(f"\nВсего найдено записей: {entries_found}")
    
    def parse_and_print_directory_entry(self, entry, index, bytes_per_sector, sectors_per_cluster):
        """Парсинг и вывод информации о записи каталога"""
        # Имя файла (8.3)
        name = entry[0:8].decode('ascii', errors='ignore').strip()
        ext = entry[8:11].decode('ascii', errors='ignore').strip()
        
        if not name:
            return
        
        # Атрибуты
        attributes = entry[11]
        attr_names = []
        if attributes & 0x01: attr_names.append("RO")
        if attributes & 0x02: attr_names.append("HIDDEN")
        if attributes & 0x04: attr_names.append("SYSTEM")
        if attributes & 0x08: attr_names.append("VOLUME")
        if attributes & 0x10: attr_names.append("DIR")
        if attributes & 0x20: attr_names.append("ARCHIVE")
        
        # Время создания
        create_time = struct.unpack('<H', entry[22:24])[0]
        hour = (create_time >> 11) & 0x1F
        minute = (create_time >> 5) & 0x3F
        second = (create_time & 0x1F) * 2
        
        # Дата создания
        create_date = struct.unpack('<H', entry[24:26])[0]
        year = ((create_date >> 9) & 0x7F) + 1980
        month = (create_date >> 5) & 0x0F
        day = create_date & 0x1F
        
        # Начальный кластер
        first_cluster = struct.unpack('<H', entry[26:28])[0]
        
        # Размер файла
        file_size = struct.unpack('<I', entry[28:32])[0]
        
        # Формируем имя файла
        filename = f"{name}.{ext}" if ext else name
        
        # Вывод информации
        print(f"\nЗапись {index}:")
        print(f"  Имя: {filename}")
        print(f"  Атрибуты: 0x{attributes:02X} ({', '.join(attr_names)})")
        print(f"  Дата создания: {year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}")
        print(f"  Начальный кластер: {first_cluster}")
        print(f"  Размер файла: {file_size} байт")
        
        # Преобразование Байт -> Кластеры
        if file_size > 0 and sectors_per_cluster > 0:
            cluster_size = sectors_per_cluster * bytes_per_sector
            clusters_needed = (file_size + cluster_size - 1) // cluster_size
            print(f"  Занимает кластеров: {clusters_needed}")
            print(f"  Эффективность: {(file_size / (clusters_needed * cluster_size)) * 100:.1f}%")
        
        # Смещение данных (если не директория и не метка тома)
        if first_cluster >= 2 and not (attributes & 0x08) and not (attributes & 0x10):
            # Рассчитываем смещение данных
            # Для упрощения предполагаем, что данные начинаются после корневого каталога
            data_sector = first_cluster - 2  # Кластеры 0 и 1 зарезервированы
            print(f"  Смещение данных: ~{data_sector * sectors_per_cluster * bytes_per_sector:,} байт")
    
    def find_partition_offsets(self):
        """Поиск смещений разделов по парам в таблице разделов"""
        print("\n" + "="*70)
        print("ПОИСК СМЕЩЕНИЙ РАЗДЕЛОВ (ПАРАМИ В ТАБЛИЦЕ РАЗДЕЛОВ)")
        print("="*70)
        
        with open(self.disk_image, 'rb') as f:
            # Читаем MBR
            f.seek(0)
            mbr = f.read(512)
            
            # Таблица разделов (64 байта, 4 записи по 16 байт)
            partition_table = mbr[446:510]
            
            print("Таблица разделов (смещение 446-510 байт):")
            print("Байты    Статус CHS_нач Тип CHS_кон LBA_нач    Секторов")
            print("-"*70)
            
            for i in range(4):
                offset = i * 16
                entry = partition_table[offset:offset+16]
                
                if len(entry) == 16:
                    # Парсим запись
                    status = entry[0]
                    type_code = entry[4]
                    lba_start = struct.unpack('<I', entry[8:12])[0]
                    sectors = struct.unpack('<I', entry[12:16])[0]
                    
                    # Форматируем вывод
                    status_str = "Активн" if status == 0x80 else "Неактв"
                    type_str = self.get_partition_type_name(type_code)
                    
                    print(f"{446+offset:03d}-{446+offset+15:03d} "
                          f"{status_str:6s} "
                          f"{type_str:10s} "
                          f"{lba_start:8d} "
                          f"{sectors:10d}")
                    
                    if lba_start > 0:
                        byte_offset = lba_start * self.sector_size
                        print(f"          → Смещение: {byte_offset:,} байт (0x{byte_offset:08X})")
    
    def get_partition_type_name(self, type_code):
        """Получение имени типа раздела"""
        types = {
            0x01: "FAT12",
            0x04: "FAT16",
            0x06: "FAT16B",
            0x07: "NTFS",
            0x0B: "FAT32",
            0x0C: "FAT32LBA",
            0x0E: "FAT16LBA",
            0x0F: "ExtLBA",
            0x83: "Linux",
            0x82: "LinuxSwap",
            0x8E: "LinuxLVM",
            0xEE: "GPT"
        }
        return types.get(type_code, f"0x{type_code:02X}")
    
    def hex_dump_partition_table(self):
        """HEX дамп таблицы разделов"""
        print("\n" + "="*70)
        print("HEX ДАМП ТАБЛИЦЫ РАЗДЕЛОВ И ЗАГРУЗОЧНОГО СЕКТОРА FAT16")
        print("="*70)
        
        with open(self.disk_image, 'rb') as f:
            # 1. Дамп MBR и таблицы разделов
            print("\nMBR и таблица разделов (смещение 0-511):")
            f.seek(0)
            data = f.read(512)
            
            for i in range(0, 512, 16):
                hex_part = ' '.join(f'{b:02X}' for b in data[i:i+8])
                hex_part2 = ' '.join(f'{b:02X}' for b in data[i+8:i+16])
                ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
                
                # Подсветка важных областей
                if i == 0:
                    prefix = "BOOT:"
                elif i == 446:
                    prefix = "PART1:"
                elif i == 462:
                    prefix = "PART2:"
                elif i == 478:
                    prefix = "PART3:"
                elif i == 494:
                    prefix = "PART4:"
                elif i == 510:
                    prefix = "SIG:"
                else:
                    prefix = "     "
                
                print(f"{prefix} {i:03X}: {hex_part}  {hex_part2:23s} |{ascii_part}|")
            
            # 2. Дамп загрузочного сектора FAT16
            print("\n\nЗагрузочный сектор FAT16 (смещение 1MB):")
            f.seek(2048 * 512)  # Начало первого раздела
            fat16_boot = f.read(512)
            
            for i in range(0, 512, 16):
                hex_part = ' '.join(f'{b:02X}' for b in fat16_boot[i:i+8])
                hex_part2 = ' '.join(f'{b:02X}' for b in fat16_boot[i+8:i+16])
                ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in fat16_boot[i:i+16])
                
                # Подсветка важных областей BPB
                if i == 0:
                    prefix = "JUMP:"
                elif i == 3:
                    prefix = "OEM:"
                elif i == 11:
                    prefix = "BPB:"
                elif i == 36:
                    prefix = "BOOT:"
                elif i == 510:
                    prefix = "SIG:"
                else:
                    prefix = "     "
                
                print(f"{prefix} {i:03X}: {hex_part}  {hex_part2:23s} |{ascii_part}|")

def main():
    """Основная функция выполнения задания"""
    print("="*70)
    print("РЕШЕНИЕ ЗАДАЧИ ПО АНАЛИЗУ FAT16")
    print("="*70)
    
    analyzer = FAT16DiskAnalyzer(disk_size_mb=100)
    
    try:
        # 1. Создание диска с разными разделами
        analyzer.create_partitioned_disk()
        
        # 2. Поиск смещений разделов (парами в таблице разделов)
        analyzer.find_partition_offsets()
        
        # 3. Создание дампа FAT16 раздела
        dump_file = analyzer.create_dump()
        
        # 4. Анализ корневого каталога из дампа
        analyzer.analyze_root_directory(dump_file)
        
        # 5. HEX дамп ключевых структур
        analyzer.hex_dump_partition_table()
        
        print("\n" + "="*70)
        print("ВСЕ ЭТАПЫ ВЫПОЛНЕНЫ УСПЕШНО")
        print("="*70)
        print("\nСозданные файлы:")
        print(f"  1. {analyzer.disk_image} - диск с разными разделами")
        print(f"  2. fat16_dump.bin - дамп FAT16 раздела")
        print("\nДля проверки можно использовать команды:")
        print(f"  file {analyzer.disk_image}")
        print(f"  sudo fdisk -l {analyzer.disk_image}")
        print(f"  hexdump -C fat16_dump.bin | head -30")
        
    except Exception as e:
        print(f"\nОшибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()