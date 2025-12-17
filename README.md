Руководство по использованию python-скрипта analyzer_dump для анализа дампа диска на Linux. Требования: Python 3.7+
1. Запустить терминал
2. Создать виртуальный диск с помощью команды dd if=/dev/zero of=vdisk.img bs=1M count=32
3. Создать разметку MBR с одним разделом с помощью данных команд:
   fdisk vdisk.img
   o # создать новую таблицу разделов (MBR)
   n # новый раздел
   p # primary
   1 # номер раздела
   <Enter> # начало по умолчанию
   <Enter> # конец по умолчанию
   t # сменить тип
   6 # FAT16
   w # записать изменения
4. Определить смещения раздела с помощью команды fdisk -l vdisk.img (например 2048)
5. Форматировать FAT16 с помощью команды mkfs.vfat -F 16 --offset=2048 vdisk.img 
6. Смонтировать и записать текстовый файл hello.txt с содержимый "Hello world" в ASCII-кодировке с помощью команд:
      mkdir mnt
      sudo mount -o loop,offset=$((2048*512)) vdisk.img mnt
      echo -n "Hello world" | iconv -f UTF-8 -t ASCII > mnt/hello.txt (нужны права root)
      sudo umount mnt
7. Снять дамп виртуального диска с помощью команды dd if=vdisk.img of=vdisk_dump.img bs=512
