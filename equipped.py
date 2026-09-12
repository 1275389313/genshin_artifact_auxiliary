'''角色装配页扫描结果：本地存取与只读摘要（~/Documents/keqing/equipped.json）。'''

import json
import os

from effective_rolls import SLOT_LABELS, cal_effective_rolls

SLOT_COUNT = 5


def empty_slots():
    return [None] * SLOT_COUNT


def is_piece(value):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return False
    header, subs = value[0], value[1]
    return isinstance(header, (list, tuple)) and isinstance(subs, dict)


def _clean_piece(value):
    if not is_piece(value):
        return None
    header = [str(part) for part in value[0]]
    subs = {}
    for key, val in value[1].items():
        try:
            subs[str(key)] = float(val)
        except (TypeError, ValueError):
            continue
    return [header, subs]


def normalize_slots(slots):
    '''固定 5 个部位；非法项视为未扫描。'''
    out = empty_slots()
    if not isinstance(slots, (list, tuple)):
        return out
    for i, item in enumerate(slots[:SLOT_COUNT]):
        if item is None:
            continue
        out[i] = _clean_piece(item)
    return out


def _slots_from_payload(payload):
    if isinstance(payload, dict):
        payload = payload.get('slots', payload.get('pieces'))
    return normalize_slots(payload)


def load_store(path):
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    store = {}
    for name, payload in data.items():
        if not isinstance(name, str) or not name:
            continue
        store[name] = _slots_from_payload(payload)
    return store


def _slots_to_json(slots):
    dumped = []
    for item in normalize_slots(slots):
        if item is None:
            dumped.append(None)
        else:
            dumped.append([list(item[0]), dict(item[1])])
    return dumped


def save_store(path, store):
    out = {}
    for name, slots in (store or {}).items():
        if not isinstance(name, str) or not name:
            continue
        out[name] = _slots_to_json(slots)
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fp:
        json.dump(out, fp, ensure_ascii=False)
    return out


def get_character_slots(store, name):
    if not store or not name:
        return empty_slots()
    if name not in store:
        return empty_slots()
    return _slots_from_payload(store.get(name))


def set_character_slots(store, name, slots):
    if store is None:
        store = {}
    if not name:
        return store
    store[name] = normalize_slots(slots)
    return store


def has_any_piece(slots):
    return any(item is not None for item in (slots or []))


def upsert_character(path, name, slots):
    '''有至少一件结果才写入；空扫描不覆盖已有存档。'''
    store = load_store(path)
    if not name or not has_any_piece(slots):
        return store
    set_character_slots(store, name, slots)
    save_store(path, store)
    return store


def format_header(header):
    if not header:
        return '未扫描'
    return '-'.join(str(part) for part in header)


def format_substats(subs):
    if not subs:
        return ''
    parts = []
    for key, value in subs.items():
        try:
            parts.append(f'{key} {float(value):.1f}')
        except (TypeError, ValueError):
            parts.append(f'{key} {value}')
    return '  '.join(parts)


def format_slot_summary(index, piece, config, old_score=None):
    label = SLOT_LABELS[index] if 0 <= index < len(SLOT_LABELS) else str(index + 1)
    if piece is None or not is_piece(piece):
        return f'{label}  —  未扫描'
    header, subs = piece[0], piece[1]
    rolls = cal_effective_rolls(subs, config)[1]
    line = f'{label}  {rolls:.1f}  {format_header(header)}'
    if old_score is not None:
        line += f'  旧评分 {old_score}'
    detail = format_substats(subs)
    if detail:
        return line + '\n' + detail
    return line
