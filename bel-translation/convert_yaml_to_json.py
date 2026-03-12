import os
import re
import json
import sys
from pathlib import Path
from collections import defaultdict

def parse_ck3_yml(filepath):
    data = {}
    if not os.path.exists(filepath):
        return data
    
    try:
        # Читаем файл с учетом возможного BOM (Byte Order Mark), который часто бывает в файлах от Paradox
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  [Ошибка чтения] {filepath}: {e}")
        return data

    for line in lines:
        line = line.strip()
        # Игнорируем пустые строки, комментарии и объявление языка
        if not line or line.startswith('#') or line.startswith('l_'):
            continue
        
        # Регулярное выражение для поиска ключа: "название_ключа:0 " (цифра может отсутствовать)
        match = re.match(r'^([\w\.\-]+)(?::\d+)?\s*:\s*', line)
        if match:
            k = match.group(1)
            # Ищем первую кавычку после двоеточия
            start_idx = line.find('"', match.end() - 1)
            if start_idx != -1:
                # Ищем закрывающую кавычку, игнорируя экранированные \" внутри
                end_idx = start_idx + 1
                while end_idx < len(line):
                    if line[end_idx] == '"' and line[end_idx-1] != '\\':
                        break
                    end_idx += 1
                
                # Если нашли и открывающую, и закрывающую
                if end_idx < len(line):
                    v = line[start_idx+1:end_idx]
                    data[k] = v
    return data

def get_corresponding_file(eng_file, target_lang, base_path, rel_path):
    target_dir = base_path / target_lang / rel_path.parent
    filename = eng_file.name.replace('l_english', f'l_{target_lang}')
    return target_dir / filename

def main():
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        # Если путь не передан, запрашиваем его. По умолчанию можем предложить текущую директорию.
        default_dir = os.path.abspath(os.path.dirname(__file__))
        req = input(f"Введите путь к папке localization \n(по умолчанию {default_dir}): ").strip()
        base_dir = req if req else default_dir
        
    if not base_dir:
        print("Путь не может быть пустым.")
        return

    base_path = Path(base_dir)
    eng_dir = base_path / 'english'
    
    if not eng_dir.exists():
        print(f"Папка 'english' не найдена по пути: {eng_dir}")
        print("Убедитесь, что вы указали правильный путь к папке 'localization'.")
        return

    # Ищем все .yml файлы в папке english и её подпапках
    eng_files = list(eng_dir.rglob('*.yml'))
    total_files = len(eng_files)
    
    if total_files == 0:
        print("YAML файлы не найдены в папке english.")
        return
        
    print(f"\nНайдено {total_files} английских YAML файлов. Начинаем конвертацию...\n")
    
    # Группируем файлы по папкам для красивого вывода прогресса
    files_by_folder = defaultdict(list)
    for eng_file in eng_files:
        files_by_folder[eng_file.parent].append(eng_file)
        
    total_folders = len(files_by_folder)
    current_folder_idx = 0
    processed_count = 0
    
    for folder, files in sorted(files_by_folder.items()):
        current_folder_idx += 1
        # Относительный путь папки (например, activities или events/court)
        folder_rel = folder.relative_to(eng_dir) if folder != eng_dir else "."
        print(f"\n=== Папка: {folder_rel} ({current_folder_idx}/{total_folders}) - файлов: {len(files)} ===")
        
        for idx, eng_file in enumerate(files, 1):
            rel_path = eng_file.relative_to(eng_dir)
            
            # Пути к файлам других языков
            rus_file = get_corresponding_file(eng_file, 'russian', base_path, rel_path)
            pol_file = get_corresponding_file(eng_file, 'polish', base_path, rel_path)
            
            # Формируем название белорусского файла 
            bel_filename = eng_file.name.replace('l_english.yml', 'l_belarusian.json')
            if bel_filename == eng_file.name:
                bel_filename = eng_file.name.replace('.yml', '.json')
                
            # Формируем путь для атрибута FILE_PATH (как в примере)
            parent_posix = rel_path.parent.as_posix()
            if parent_posix == '.':
                bel_file_path_str = f"localization/belarusian/{bel_filename}"
            else:
                bel_file_path_str = f"localization/belarusian/{parent_posix}/{bel_filename}"
                
            # Путь для сохранения итогового JSON
            bel_out_file = base_path / 'belarusian' / rel_path.parent / bel_filename
            bel_out_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Парсим все 3 файла
            eng_data = parse_ck3_yml(eng_file)
            rus_data = parse_ck3_yml(rus_file)
            pol_data = parse_ck3_yml(pol_file)
            
            # Формируем итоговый список
            out_list = []
            for key, eng_val in eng_data.items():
                entry = {
                    "KEY": key,
                    "FILE_PATH": bel_file_path_str,
                    "ENG": eng_val,
                    "RUS": rus_data.get(key, ""),
                    "POL": pol_data.get(key, ""),
                    "BEL": ""
                }
                out_list.append(entry)
                
            # Сохраняем в JSON с отступами и без экранирования кириллицы
            with open(bel_out_file, 'w', encoding='utf-8') as f:
                json.dump(out_list, f, ensure_ascii=False, indent=2)
                
            processed_count += 1
            # Выводим прогресс внутри папки
            percent = (processed_count / total_files) * 100
            print(f"  [{idx}/{len(files)}] {eng_file.name} -> {len(out_list)} строк | Общий: {processed_count}/{total_files} ({percent:.1f}%)")

    print(f"\nГотово! Успешно конвертировано {processed_count} файлов.")
    print(f"Все JSON файлы сохранены в папке: {base_path / 'belarusian'}")

if __name__ == '__main__':
    main()
