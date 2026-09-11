'''有效词条（社区口径）：副词条数值 / 五星单词条最大值，系数只做过滤。'''

FALLBACK_NAME = '常规主C-攻暴'

FALLBACK_CONFIG = {
    '生命值': 0,
    '攻击力': 0.75,
    '防御力': 0,
    '暴击率': 1,
    '暴击伤害': 1,
    '元素精通': 0,
    '元素充能效率': 0,
}

# 五星副词条单次强化最大值（社区有效词条分母）
MAX_SINGLE_ROLL = {
    '暴击率': 3.89,
    '暴击伤害': 7.77,
    '攻击力百分比': 5.83,
    '生命值百分比': 5.83,
    '防御力百分比': 7.29,
    '元素充能效率': 6.48,
    '元素精通': 23.31,
}

# character.json 里的 攻击力/生命值/防御力 只对应百分比副词条
PERCENT_GATED_BY = {
    '攻击力百分比': '攻击力',
    '生命值百分比': '生命值',
    '防御力百分比': '防御力',
}

# 小攻击/小生命/小防御默认不计入有效词条
FLAT_STATS = frozenset({'攻击力', '生命值', '防御力'})

SLOT_ORDER = ('flower', 'plume', 'sands', 'goblet', 'circlet')
SLOT_LABELS = ('花', '羽', '沙', '杯', '冠')


def is_effective_substat(stat_key, config):
    '''系数 > 0 才算有效；小词条默认无效；攻击力等名称只放行百分比。'''
    if not stat_key or stat_key in FLAT_STATS:
        return False
    if stat_key not in MAX_SINGLE_ROLL:
        return False
    gate_key = PERCENT_GATED_BY.get(stat_key, stat_key)
    try:
        return float(config.get(gate_key, 0) or 0) > 0
    except (TypeError, ValueError):
        return False


def substat_rolls(stat_key, value):
    '''单条词条的有效词条数（未按角色过滤），保留一位小数。'''
    divisor = MAX_SINGLE_ROLL.get(stat_key)
    if not divisor:
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(number / divisor, 1)


def cal_effective_rolls(ocr_result_sub, config):
    '''计算一件圣遗物的有效词条。

    参数：
        ocr_result_sub: {'暴击伤害': 14.0, '攻击力百分比': 15.7, '防御力': 21.0, ...}
        config: character.json 中该角色的词条系数
    返回：
        per_substat: 与输入顺序一致的每条有效词条数 list
        piece_total: 该件合计（一位小数）
    '''
    config = config or {}
    per_substat = []
    piece_total = 0.0
    for key, value in (ocr_result_sub or {}).items():
        if is_effective_substat(key, config):
            rolls = substat_rolls(key, value)
        else:
            rolls = 0.0
        per_substat.append(rolls)
        piece_total += rolls
    return per_substat, round(piece_total, 1)


def sum_set_rolls(piece_totals):
    '''五件合计。None 表示该部位尚未识别。'''
    counted = [item for item in piece_totals if item is not None]
    total = round(sum(counted), 1) if counted else 0.0
    return total, len(counted)


def format_set_total(total, counted, expected=5):
    '''套装合计展示：扫完五件为「有效词条 28.4」，扫描中带（3/5）。'''
    if counted >= expected:
        return f'有效词条 {total:.1f}'
    if counted <= 0:
        return '有效词条 0.0（0/5）'
    return f'有效词条 {total:.1f}（{counted}/{expected}）'


def resolve_character_config(name, characters):
    '''未选角色或配置为空 → 常规主C-攻暴；json 中找不到角色则同样回退并给出提示。'''
    characters = characters or {}
    fallback = dict(FALLBACK_CONFIG)
    if not name:
        return fallback, None
    if name not in characters:
        if str(name).startswith('----'):
            return fallback, None
        notice = f'角色「{name}」不在 character.json，暂按「{FALLBACK_NAME}」计算'
        return fallback, notice
    config = characters.get(name) or {}
    if not config:
        return fallback, None
    return config, None
