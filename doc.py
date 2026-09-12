'''个人数据另外储存'''

import json, os, shutil

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

# 数据文件夹存在则更新、补充相关配置文件
if os.path.exists(folder):
    # 角色配置不存在就复制一份，存在进行对比，有新角色添加则增量更新
    if not os.path.exists(character_path):
        shutil.copy('src/character.json', character_path)
    else:
        with open('src/character.json', 'r', encoding = 'utf-8') as fp:
            default = json.load(fp)
        with open(character_path, 'r', encoding = 'utf-8') as fp:
            user = json.load(fp)
        diff = default.keys() - user.keys()
        if diff != set():
            for item in diff:
                user[item] = default[item]
            with open(character_path, 'w', encoding = 'utf-8') as fp:
                json.dump(user, fp, ensure_ascii = False)
    
    # 
    if not os.path.exists(archive_path):
        create_archieve()
    if not os.path.exists(equipped_path):
        create_equipped()
    # 
    if not os.path.exists(coefficient_path):
        create_coefficient()
    if not os.path.exists(settings_path):
        create_settings()

# 数据文件夹不存在则新建文件夹并复制、新建相关数据文件
else:
    os.makedirs(folder)
    shutil.copy('src/character.json', character_path)
    create_archieve()
    create_equipped()
    create_coefficient()
    create_settings()
