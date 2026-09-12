'''角色装配扫描结果：存档 round-trip、非法项、只读摘要。不启动 Qt。'''

import importlib.util
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_ROOT, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


er = _load('effective_rolls', 'effective_rolls.py')
eq = _load('equipped', 'equipped.py')

ATK_CRIT = dict(er.FALLBACK_CONFIG)
SANDONE = {
    '生命值': 0,
    '攻击力': 0.75,
    '防御力': 0,
    '暴击率': 1,
    '暴击伤害': 1,
    '元素精通': 0.75,
    '元素充能效率': 0.3,
}

CIRCLET = [
    ['止于阔步跌坠的灵摆', '理之冠', '暴击伤害', '62.2%', '+20'],
    {
        '暴击率': 10.5,
        '元素精通': 47.0,
        '防御力': 21.0,
        '元素充能效率': 11.0,
    },
]

SANDS = [
    ['雷云之笼', '时之沙', '攻击力', '46.6%', '+20'],
    {'暴击伤害': 15.5, '攻击力百分比': 9.3},
]


class NormalizeTests(unittest.TestCase):
    def test_empty_is_five_nones(self):
        slots = eq.normalize_slots(None)
        self.assertEqual(len(slots), 5)
        self.assertTrue(all(item is None for item in slots))

    def test_truncates_and_pads(self):
        slots = eq.normalize_slots([CIRCLET])
        self.assertEqual(len(slots), 5)
        self.assertEqual(slots[0][0][1], '理之冠')
        self.assertIsNone(slots[4])

    def test_invalid_slot_becomes_none(self):
        slots = eq.normalize_slots(['bad', {'x': 1}, None, CIRCLET, 3])
        self.assertIsNone(slots[0])
        self.assertIsNone(slots[1])
        self.assertIsNone(slots[2])
        self.assertIsNotNone(slots[3])
        self.assertIsNone(slots[4])

    def test_substat_values_are_float(self):
        slots = eq.normalize_slots([[['花', '生之花'], {'暴击率': '10.5'}]])
        self.assertEqual(slots[0][1]['暴击率'], 10.5)


class StoreRoundTripTests(unittest.TestCase):
    def test_missing_file_is_empty_store(self):
        self.assertEqual(eq.load_store('/tmp/keqing-no-such-equipped.json'), {})

    def test_corrupt_json_is_empty_store(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'equipped.json')
            with open(path, 'w', encoding='utf-8') as fp:
                fp.write('{not json')
            self.assertEqual(eq.load_store(path), {})

    def test_save_load_per_character(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'equipped.json')
            store = {}
            slots = eq.empty_slots()
            slots[4] = CIRCLET
            eq.set_character_slots(store, '桑多涅', slots)
            eq.save_store(path, store)

            loaded = eq.load_store(path)
            sandone = eq.get_character_slots(loaded, '桑多涅')
            self.assertEqual(sandone[4][0], CIRCLET[0])
            self.assertEqual(sandone[4][1]['暴击率'], 10.5)
            self.assertIsNone(sandone[0])
            self.assertEqual(eq.get_character_slots(loaded, '刻晴'), eq.empty_slots())

    def test_overwrite_one_character_keeps_others(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'equipped.json')
            store = {}
            a = eq.empty_slots()
            a[0] = CIRCLET
            b = eq.empty_slots()
            b[2] = SANDS
            eq.set_character_slots(store, '桑多涅', a)
            eq.set_character_slots(store, '刻晴', b)
            eq.save_store(path, store)

            store = eq.load_store(path)
            updated = eq.empty_slots()
            updated[2] = SANDS
            eq.set_character_slots(store, '桑多涅', updated)
            eq.save_store(path, store)

            loaded = eq.load_store(path)
            self.assertIsNone(eq.get_character_slots(loaded, '桑多涅')[0])
            self.assertEqual(eq.get_character_slots(loaded, '桑多涅')[2][0][1], '时之沙')
            self.assertEqual(eq.get_character_slots(loaded, '刻晴')[2][0][1], '时之沙')

    def test_dict_payload_slots_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'equipped.json')
            with open(path, 'w', encoding='utf-8') as fp:
                fp.write('{"桑多涅": {"slots": [null, null, null, null, null]}}')
            loaded = eq.load_store(path)
            self.assertEqual(eq.get_character_slots(loaded, '桑多涅'), eq.empty_slots())

    def test_never_scanned_character(self):
        self.assertFalse(eq.has_any_piece(eq.empty_slots()))
        self.assertTrue(eq.has_any_piece([None, None, SANDS, None, None]))
        self.assertEqual(eq.get_character_slots({}, '芙宁娜'), eq.empty_slots())

    def test_upsert_skips_empty_and_writes_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'equipped.json')
            first = eq.empty_slots()
            first[4] = CIRCLET
            eq.upsert_character(path, '桑多涅', first)

            eq.upsert_character(path, '桑多涅', eq.empty_slots())
            loaded = eq.get_character_slots(eq.load_store(path), '桑多涅')
            self.assertEqual(loaded[4][0][1], '理之冠')

            partial = eq.empty_slots()
            partial[2] = SANDS
            eq.upsert_character(path, '桑多涅', partial)
            loaded = eq.get_character_slots(eq.load_store(path), '桑多涅')
            self.assertIsNone(loaded[4])
            self.assertEqual(loaded[2][0][1], '时之沙')


class SummaryTests(unittest.TestCase):
    def test_empty_slot_label(self):
        self.assertEqual(eq.format_slot_summary(0, None, ATK_CRIT), '花  —  未扫描')
        self.assertEqual(eq.format_slot_summary(4, None, ATK_CRIT), '冠  —  未扫描')

    def test_circlet_matches_effective_rolls(self):
        text = eq.format_slot_summary(4, CIRCLET, SANDONE)
        self.assertIn('冠  6.4  ', text)
        self.assertIn('止于阔步跌坠的灵摆-理之冠-暴击伤害-62.2%-+20', text)
        self.assertIn('暴击率 10.5', text)
        self.assertIn('元素精通 47.0', text)
        self.assertIn('防御力 21.0', text)
        self.assertIn('元素充能效率 11.0', text)

    def test_old_score_optional(self):
        text = eq.format_slot_summary(4, CIRCLET, ATK_CRIT, old_score=12.3)
        self.assertIn('旧评分 12.3', text)


if __name__ == '__main__':
    unittest.main()
