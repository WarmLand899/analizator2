import struct
import sys

SECTOR_SIZE = 512


def hexdump(data, base_offset=0):
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{base_offset+i:08x}  {hex_part:<47}  |{ascii_part}|")


def read_sector(f, lba, count=1):
    f.seek(lba * SECTOR_SIZE)
    return f.read(count * SECTOR_SIZE)


# ---------- main ----------

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} vdisk.img")
    sys.exit(1)

image = sys.argv[1]

with open(image, 'rb') as f:

    # === MBR ===
    mbr = read_sector(f, 0)

    part_entry = mbr[446:462]
    start_lba = struct.unpack('<I', part_entry[8:12])[0]

    print(f"[+] Partition start LBA: {start_lba}")

    # === Boot sector ===
    boot = read_sector(f, start_lba)

    bytes_per_sector = struct.unpack('<H', boot[11:13])[0]
    sectors_per_cluster = boot[13]
    reserved_sectors = struct.unpack('<H', boot[14:16])[0]
    fats = boot[16]
    root_entries = struct.unpack('<H', boot[17:19])[0]
    sectors_per_fat = struct.unpack('<H', boot[22:24])[0]

    root_dir_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector

    fat_start = start_lba + reserved_sectors
    root_start = fat_start + fats * sectors_per_fat
    data_start = root_start + root_dir_sectors

    print(f"[+] FAT16 detected")
    print(f"[+] Root dir LBA: {root_start}")
    print(f"[+] Data area LBA: {data_start}")

    # === Root directory ===
    root_dir = read_sector(f, root_start, root_dir_sectors)

    file_cluster = None
    file_size = None

    for i in range(0, len(root_dir), 32):
        entry = root_dir[i:i+32]
        name = entry[0:11]

        if name == b'HELLO   TXT':
            file_cluster = struct.unpack('<H', entry[26:28])[0]
            file_size = struct.unpack('<I', entry[28:32])[0]
            print(f"[+] Found HELLO.TXT")
            print(f"    Start cluster: {file_cluster}")
            print(f"    File size: {file_size} bytes")
            break

    if file_cluster is None:
        print("[-] File HELLO.TXT not found")
        sys.exit(1)

    # === Read file data ===
    cluster_lba = data_start + (file_cluster - 2) * sectors_per_cluster
    sectors_to_read = (file_size + bytes_per_sector - 1) // bytes_per_sector

    data = read_sector(f, cluster_lba, sectors_to_read)

    print("\n=== HEX DUMP OF FILE DATA ===\n")
    hexdump(data[:file_size], cluster_lba * SECTOR_SIZE)

