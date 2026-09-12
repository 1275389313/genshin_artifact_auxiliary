'''个人数据另外储存'''

import json, os, shutil

from paths import resource_path

folder = os.path.expanduser('~/Documents')
folder = folder + '/keqing'
character_path = folder + '/character.json'
archive_path = folder + '/archive.json'
equipped_path = folder + '/equipped.json'
mona_path = folder + '/mona.json'
coefficient_path = folder + '/coefficient.json'
settings_path = folder + '/settings.json'

DEFAULT_SETTINGS = {
    'scan_hotkey': 'f8',
    'show_old_score': False,
    'scan_delay_ms': 450,
}

# 创建存档文件
def create_archieve():
    with open(archive_path, 'w', encoding = 'utf-8') as fp:
            artifacts = {'背包':{}, '角色': {}}
            json.dump(artifacts, fp, ensure_ascii = False)

def create_equipped():
    with open(equipped_path, 'w', encoding = 'utf-8') as fp:
        json.dump({}, fp, ensure_ascii = False)

# 创建词条配置文件
def create_coefficient():
    with open(coefficient_path, 'w', encoding = 'utf-8') as fp:
        coefficient = {"暴击率": 2.0,
                       "暴击伤害": 1.0,
                       "攻击力百分比": 1.33,
                       "生命值百分比": 1.33,
                       "防御力百分比": 1.06,
                       "攻击力": 0.199,
                       "生命值": 0.01716,
                       "防御力": 0.2211,
                       "元素精通": 0.33,
                       "元素充能效率": 1.1979}
        json.dump(coefficient, fp, ensure_ascii = False)

def create_settings():
    with open(settings_path, 'w', encoding = 'utf-8') as fp:
        json.dump(DEFAULT_SETTINGS, fp, ensure_ascii = False)

def load_settings():
    '''读取用户设置；缺项用默认值补齐，不覆盖其它 keqing 文件。'''
    data = dict(DEFAULT_SETTINGS)
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding = 'utf-8') as fp:
                saved = json.load(fp)
            if isinstance(saved, dict):
                data.update(saved)
        except Exception:
            pass
    data['scan_hotkey'] = str(data.get('scan_hotkey') or 'f8').strip().lower()
    data['show_old_score'] = bool(data.get('show_old_score'))
    try:
        data['scan_delay_ms'] = max(200, int(data.get('scan_delay_ms') or 450))
    except (TypeError, ValueError):
        data['scan_delay_ms'] = 450
    return data

def save_settings(data):
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data or {})
    with open(settings_path, 'w', encoding = 'utf-8') as fp:
        json.dump(merged, fp, ensure_ascii = False)

def default_character_json():
    '''Packed default character.json (src/, or _MEIPASS/src when frozen).'''
    return resource_path('src', 'character.json')

def load_bundled_character_defaults(path=None):
    '''Read bundled default characters. Missing or unreadable → None, no throw.'''
    src = path if path is not None else default_character_json()
    if not os.path.isfile(src):
        print(f'未找到默认角色配置 {src}，跳过从打包文件复制/合并。个人数据仍使用 {character_path}')
        return None
    try:
        with open(src, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
    except Exception as e:
        print(f'读取默认角色配置失败（{src}）：{e}')
        return None
    if not isinstance(data, dict):
        print(f'默认角色配置格式无效：{src}')
        return None
    return data

def copy_default_character(dest, src=None):
    '''Copy bundled character.json to user data. Fail soft if the default is missing.'''
    default = load_bundled_character_defaults(src)
    if default is None:
        if not os.path.exists(dest):
            try:
                with open(dest, 'w', encoding='utf-8') as fp:
                    json.dump({}, fp, ensure_ascii=False)
            except Exception as e:
                print(f'无法写入空的角色配置 {dest}：{e}')
        return False
    try:
        shutil.copy(src if src is not None else default_character_json(), dest)
        return True
    except Exception as e:
        print(f'复制默认角色配置失败：{e}')
        if not os.path.exists(dest):
            try:
                with open(dest, 'w', encoding='utf-8') as fp:
                    json.dump({}, fp, ensure_ascii=False)
            except Exception as write_err:
                print(f'无法写入空的角色配置 {dest}：{write_err}')
        return False

def merge_new_characters(user_path, src=None):
    '''Add characters present only in the bundled default. Never overwrite user edits.'''
    default = load_bundled_character_defaults(src)
    if default is None:
        return
    try:
        with open(user_path, 'r', encoding='utf-8') as fp:
            user = json.load(fp)
        if not isinstance(user, dict):
            print(f'用户角色配置格式无效，跳过合并：{user_path}')
            return
        diff = default.keys() - user.keys()
        if diff:
            for item in diff:
                user[item] = default[item]
            with open(user_path, 'w', encoding='utf-8') as fp:
                json.dump(user, fp, ensure_ascii=False)
    except Exception as e:
        print(f'合并默认角色配置失败：{e}')

def ensure_user_data():
    '''Create ~/Documents/keqing and merge bundled defaults. Safe to call when frozen.'''
    if os.path.exists(folder):
        if not os.path.exists(character_path):
            copy_default_character(character_path)
        else:
            merge_new_characters(character_path)
        if not os.path.exists(archive_path):
            create_archieve()
        if not os.path.exists(equipped_path):
            create_equipped()
        if not os.path.exists(coefficient_path):
            create_coefficient()
        if not os.path.exists(settings_path):
            create_settings()
    else:
        os.makedirs(folder)
        copy_default_character(character_path)
        create_archieve()
        create_equipped()
        create_coefficient()
        create_settings()

# 数据文件夹存在则更新、补充相关配置文件；不存在则新建
ensure_user_data()
