# Программа читает образ диска с MBR и FAT16,
# находит файл HELLO.TXT и выводит его содержимое в hex-дампе
import struct
import sys

SECTOR_SIZE = 512  # размер одного сектора в байтах


def hexdump(data, base_offset=0):
    # Функция для красивого hex-дампа
    # data — байты
    # base_offset — адрес, с которого начинаются данные
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{base_offset+i:08x}  {hex_part:<47}  |{ascii_part}|")


def read_sector(f, lba, count=1):
    # Читает один или несколько секторов по LBA
    f.seek(lba * SECTOR_SIZE)
    return f.read(count * SECTOR_SIZE)


# ---------- main ----------

# Проверяем аргументы командной строки
if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} vdisk.img")
    sys.exit(1)

image = sys.argv[1]  # имя файла образа диска

with open(image, 'rb') as f:

    # === MBR ===
    # Читаем первый сектор диска (MBR)
    mbr = read_sector(f, 0)

    # Берём первую запись таблицы разделов
    part_entry = mbr[446:462]

    # Извлекаем начальный LBA раздела
    start_lba = struct.unpack('<I', part_entry[8:12])[0]

    print(f"[+] Partition start LBA: {start_lba}")

    # === Boot sector ===
    # Читаем загрузочный сектор FAT16
    boot = read_sector(f, start_lba)

    # Читаем основные параметры файловой системы
    bytes_per_sector = struct.unpack('<H', boot[11:13])[0]
    sectors_per_cluster = boot[13]
    reserved_sectors = struct.unpack('<H', boot[14:16])[0]
    fats = boot[16]
    root_entries = struct.unpack('<H', boot[17:19])[0]
    sectors_per_fat = struct.unpack('<H', boot[22:24])[0]

    # Считаем, сколько секторов занимает корневой каталог
    root_dir_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector

    # Вычисляем расположение областей FAT16
    fat_start = start_lba + reserved_sectors
    root_start = fat_start + fats * sectors_per_fat
    data_start = root_start + root_dir_sectors

    print(f"[+] FAT16 detected")
    print(f"[+] Root dir LBA: {root_start}")
    print(f"[+] Data area LBA: {data_start}")

    # === Root directory ===
    # Читаем корневой каталог
    root_dir = read_sector(f, root_start, root_dir_sectors)

    file_cluster = None  # стартовый кластер файла
    file_size = None     # размер файла

    # Проходим по записям каталога (по 32 байта)
    for i in range(0, len(root_dir), 32):
        entry = root_dir[i:i+32]
        name = entry[0:11]

        # Ищем файл HELLO.TXT (формат 8.3)
        if name == b'HELLO   TXT':
            file_cluster = struct.unpack('<H', entry[26:28])[0]
            file_size = struct.unpack('<I', entry[28:32])[0]
            print(f"[+] Found HELLO.TXT")
            print(f"    Start cluster: {file_cluster}")
            print(f"    File size: {file_size} bytes")
            break

    # Если файл не найден — выходим
    if file_cluster is None:
        print("[-] File HELLO.TXT not found")
        sys.exit(1)

    # === Read file data ===
    # Вычисляем LBA кластера с данными файла
    cluster_lba = data_start + (file_cluster - 2) * sectors_per_cluster

    # Сколько секторов нужно прочитать
    sectors_to_read = (file_size + bytes_per_sector - 1) // bytes_per_sector

    # Читаем данные файла
    data = read_sector(f, cluster_lba, sectors_to_read)

    print("\n=== HEX DUMP OF FILE DATA ===\n")

    # Выводим hex-дамп содержимого файла
    hexdump(data[:file_size], cluster_lba * SECTOR_SIZE)



