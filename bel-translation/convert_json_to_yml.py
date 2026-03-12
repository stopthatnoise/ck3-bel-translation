import os
import re
import json
import sys
from pathlib import Path
from collections import defaultdict

def escape_for_yml(value: str) -> str:
    """
    Падрыхтоўвае значэнне для запісу ў YML файл.
    У JSON файлах перакладу пераносы радкоў захоўваюцца як '\\n' (два сімвалы).
    У YML файлах CK3 яны таксама захоўваюцца як '\\n' у радку (два сімвалы).
    Такім чынам, тут нічога мяняць не трэба — значэнне перапісваецца як ёсць.
    """
    return value

def get_version_number(key: str, eng_value: str, eng_data: dict) -> str:
    """
    Вяртае нумар версіі для ключа (напрыклад ':0', ':1' і г.д.).
    Калі ключ ёсць у англійскіх даных з нумарам — выкарыстоўваем яго.
    Інакш выкарыстоўваем ':0' па змаўчанні.
    """
    return eng_data.get(key, ':0')

def parse_ck3_yml_with_versions(filepath):
    """
    Парсіць YML файл CK3 і вяртае слоўнік {ключ: нумар_версіі}.
    Нумар версіі — гэта лічба пасля двукроп'я ў ключы (напрыклад ':0', ':1').
    Калі лічбы няма — вяртае '' (пусты радок).
    """
    versions = {}
    if not os.path.exists(filepath):
        return versions

    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  [Памылка чытання] {filepath}: {e}")
        return versions

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('l_'):
            continue

        # Шукаем: KEY:N або KEY: (без лічбы)
        match = re.match(r'^([\w\.\-]+)(:\d+|:)?\s*"', stripped)
        if match:
            key = match.group(1)
            ver_part = match.group(2) if match.group(2) else ''
            versions[key] = ver_part

    return versions

def main():
    if len(sys.argv) > 1:
        bel_dir = sys.argv[1]
    else:
        default_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'belarusian')
        req = input(f"Увядзіце шлях да папкі з JSON файламі перакладу\n(па змаўчанні {default_dir}): ").strip()
        bel_dir = req if req else default_dir

    if not bel_dir:
        print("Шлях не можа быць пустым.")
        return

    bel_path = Path(bel_dir)
    if not bel_path.exists():
        print(f"Папка не знойдзена: {bel_path}")
        return

    # Папка для захавання вынікаў .yml файлаў
    if len(sys.argv) > 2:
        out_dir = sys.argv[2]
    else:
        default_out = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'output_yml')
        req2 = input(f"Увядзіце шлях для захавання YML файлаў\n(па змаўчанні {default_out}): ").strip()
        out_dir = req2 if req2 else default_out

    out_path = Path(out_dir)

    # Шлях да арыгінальных англійскіх YML файлаў (для захавання нумароў версій)
    script_dir = os.path.abspath(os.path.dirname(__file__))
    # Шукаем папку з арыгіналамі на адзін узровень вышэй
    parent_dir = Path(script_dir).parent
    eng_localization_dir = parent_dir / 'origin' / 'localization' / 'english'
    
    if not eng_localization_dir.exists():
        print(f"  [Увага] Папка з англійскімі арыгіналамі не знойдзена: {eng_localization_dir}")
        print("  Нумары версій (':0', ':1' і г.д.) будуць устаноўлены як ':0' па змаўчанні.")
        eng_localization_dir = None

    # Знаходзім усе JSON файлы ў папцы belarusian
    json_files = list(bel_path.rglob('*.json'))
    total_files = len(json_files)

    if total_files == 0:
        print("JSON файлы не знойдзены.")
        return

    print(f"\nЗнойдзена {total_files} JSON файлаў. Пачынаем канвертацыю...\n")

    # Групуем файлы па папках для вываду прагрэсу
    files_by_folder = defaultdict(list)
    for jf in json_files:
        files_by_folder[jf.parent].append(jf)

    total_folders = len(files_by_folder)
    current_folder_idx = 0
    processed_count = 0
    skipped_count = 0

    for folder, files in sorted(files_by_folder.items()):
        current_folder_idx += 1
        folder_rel = folder.relative_to(bel_path) if folder != bel_path else Path('.')
        print(f"\n=== Папка: {folder_rel} ({current_folder_idx}/{total_folders}) — файлаў: {len(files)} ===")

        for idx, json_file in enumerate(files, 1):
            # Чытаем JSON файл перакладу
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
            except Exception as e:
                print(f"  [{idx}/{len(files)}] ПАМЫЛКА чытання {json_file.name}: {e}")
                skipped_count += 1
                continue

            if not entries:
                skipped_count += 1
                continue

            # Праверяем фармат: павінен быць масіў аб'ектаў з палямі KEY і BEL
            if not isinstance(entries, list):
                skipped_count += 1
                continue
            first = entries[0]
            if not isinstance(first, dict) or 'KEY' not in first or 'BEL' not in first:
                skipped_count += 1
                continue

            # Вызначаем FILE_PATH з першага запісу
            file_path_str = first.get('FILE_PATH', '')
            # FILE_PATH выглядае як: "localization/belarusian/subfolder/filename_l_belarusian.json"
            # Нам трэба вызначыць імя выніковага YML файла

            # Атрымліваем адносны шлях JSON файла адносна bel_path
            rel_json = json_file.relative_to(bel_path)
            # Замяняем суффікс і мову ў назве файла
            yml_name = json_file.name
            yml_name = re.sub(r'_l_belarusian\.json$', '_l_belarusian.yml', yml_name)
            if yml_name == json_file.name:
                yml_name = json_file.stem + '.yml'

            # Шлях для захавання
            out_file = out_path / rel_json.parent / yml_name
            out_file.parent.mkdir(parents=True, exist_ok=True)

            # Шукаем адпаведны англійскі YML файл для нумароў версій
            eng_versions = {}
            if eng_localization_dir:
                eng_yml_name = yml_name.replace('_l_belarusian.yml', '_l_english.yml')
                # Шукаем у адпаведнай падпапцы
                eng_yml_path = eng_localization_dir / rel_json.parent / eng_yml_name
                if eng_yml_path.exists():
                    eng_versions = parse_ck3_yml_with_versions(eng_yml_path)
                else:
                    # Паспрабуем знайсці файл у каранёвай папцы
                    eng_yml_path2 = eng_localization_dir / eng_yml_name
                    if eng_yml_path2.exists():
                        eng_versions = parse_ck3_yml_with_versions(eng_yml_path2)

            # Запісваем YML файл
            # CK3 патрабуе BOM (UTF-8 з BOM) і кадоўка UTF-8
            try:
                with open(out_file, 'w', encoding='utf-8-sig', newline='\n') as f:
                    # Першы радок — аб'ява мовы
                    f.write('l_belarusian:\n')

                    for entry in entries:
                        key = entry.get('KEY', '')
                        bel_value = entry.get('BEL', '')

                        if not key:
                            continue

                        # Калі перакладу няма — выкарыстоўваем рускі тэкст як запасны варыянт
                        if not bel_value:
                            bel_value = entry.get('RUS', '')

                        # Нумар версіі з арыгінальнага файла або ':0' па змаўчанні
                        ver = eng_versions.get(key, ':0')

                        # Экранаванне: у CK3 унутры радка двукроп'е HUI не патрабуе экранавання,
                        # але двукоска (") патрабуе \\\" — аднак у арыгіналах Paradox яны не выкарыстоўваюцца
                        # Захоўваем значэнне як ёсць (\\n у json = \\n у yml)
                        line = f' {key}{ver} "{bel_value}"\n'
                        f.write(line)

            except Exception as e:
                print(f"  [{idx}/{len(files)}] ПАМЫЛКА запісу {out_file}: {e}")
                skipped_count += 1
                continue

            processed_count += 1
            percent = (processed_count / total_files) * 100
            print(f"  [{idx}/{len(files)}] {json_file.name} -> {yml_name} | {len(entries)} радкоў | Агулам: {processed_count}/{total_files} ({percent:.1f}%)")

    print(f"\nГатова! Паспяхова канвертавана: {processed_count} файлаў.")
    if skipped_count:
        print(f"Прапушчана з памылкамі: {skipped_count} файлаў.")
    print(f"YML файлы захаваны ў: {out_path}")

if __name__ == '__main__':
    main()
