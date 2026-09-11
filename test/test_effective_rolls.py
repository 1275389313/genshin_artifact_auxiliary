'''纯公式单测：分母、百分比/小词条、系数过滤、一位小数、五件合计。'''

import importlib.util
import os
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    'effective_rolls', os.path.join(_ROOT, 'effective_rolls.py'))
er = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(er)


ATK_CRIT = {
    '生命值': 0,
    '攻击力': 0.75,
    '防御力': 0,
    '暴击率': 1,
    '暴击伤害': 1,
    '元素精通': 0,
    '元素充能效率': 0,
}

HP_ER = {
    '生命值': 1,
    '攻击力': 0,
    '防御力': 0,
    '暴击率': 0,
    '暴击伤害': 0,
    '元素精通': 0,
    '元素充能效率': 0.55,
}


class DivisorTests(unittest.TestCase):
    def test_one_max_roll_is_1_0(self):
        self.assertEqual(er.substat_rolls('暴击率', 3.89), 1.0)
        self.assertEqual(er.substat_rolls('暴击伤害', 7.77), 1.0)
        self.assertEqual(er.substat_rolls('攻击力百分比', 5.83), 1.0)
        self.assertEqual(er.substat_rolls('生命值百分比', 5.83), 1.0)
        self.assertEqual(er.substat_rolls('防御力百分比', 7.29), 1.0)
        self.assertEqual(er.substat_rolls('元素充能效率', 6.48), 1.0)
        self.assertEqual(er.substat_rolls('元素精通', 23.31), 1.0)

    def test_one_decimal(self):
        # 7.8 / 3.89 = 2.00514 → 2.0
        self.assertEqual(er.substat_rolls('暴击率', 7.8), 2.0)
        # 15.5 / 7.77 = 1.99485 → 2.0
        self.assertEqual(er.substat_rolls('暴击伤害', 15.5), 2.0)
        # 9.3 / 5.83 = 1.5952 → 1.6
        self.assertEqual(er.substat_rolls('攻击力百分比', 9.3), 1.6)


class FilterTests(unittest.TestCase):
    def test_flat_stats_never_count(self):
        subs = {
            '攻击力': 311.0,
            '生命值': 4780.0,
            '防御力': 123.0,
            '暴击率': 3.89,
        }
        per, total = er.cal_effective_rolls(subs, ATK_CRIT)
        self.assertEqual(per, [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(total, 1.0)

    def test_json_atk_gates_percent_only(self):
        subs = {'攻击力百分比': 5.83, '攻击力': 19.0}
        per, total = er.cal_effective_rolls(subs, ATK_CRIT)
        self.assertEqual(per, [1.0, 0.0])
        self.assertEqual(total, 1.0)
        per, total = er.cal_effective_rolls(subs, HP_ER)
        self.assertEqual(per, [0.0, 0.0])
        self.assertEqual(total, 0.0)

    def test_coeff_zero_ignored_even_if_high(self):
        subs = {
            '防御力百分比': 21.87,  # 3 词条，但主 C 防御系数 0
            '暴击伤害': 7.77,
        }
        per, total = er.cal_effective_rolls(subs, ATK_CRIT)
        self.assertEqual(per, [0.0, 1.0])
        self.assertEqual(total, 1.0)

    def test_coeff_is_filter_not_weight(self):
        # 0.55 与 1 都应整段计入，不得乘旧版 2.0/1.33 权重
        subs = {'元素充能效率': 6.48, '生命值百分比': 5.83}
        per_low, total_low = er.cal_effective_rolls(subs, HP_ER)
        full = dict(HP_ER)
        full['元素充能效率'] = 1
        full['生命值'] = 1
        per_high, total_high = er.cal_effective_rolls(subs, full)
        self.assertEqual(per_low, per_high)
        self.assertEqual(total_low, total_high)
        self.assertEqual(total_low, 2.0)


class PieceAndSetTests(unittest.TestCase):
    def test_piece_sum_one_decimal(self):
        subs = {
            '暴击率': 6.2,          # 1.6
            '暴击伤害': 14.0,       # 1.8
            '攻击力百分比': 15.7,   # 2.7
            '防御力': 21.0,         # 0
        }
        per, total = er.cal_effective_rolls(subs, ATK_CRIT)
        self.assertEqual(per, [1.6, 1.8, 2.7, 0.0])
        self.assertEqual(total, 6.1)

    def test_five_piece_sum_and_partial_label(self):
        pieces = [4.2, 5.1, 3.0, None, None]
        total, counted = er.sum_set_rolls(pieces)
        self.assertEqual(counted, 3)
        self.assertEqual(total, 12.3)
        self.assertEqual(er.format_set_total(total, counted), '有效词条 12.3（3/5）')

        pieces = [4.2, 5.1, 3.0, 8.0, 8.1]
        total, counted = er.sum_set_rolls(pieces)
        self.assertEqual(counted, 5)
        self.assertEqual(total, 28.4)
        self.assertEqual(er.format_set_total(total, counted), '有效词条 28.4')

    def test_unknown_stat_is_zero(self):
        per, total = er.cal_effective_rolls({'治疗加成': 9.0, '暴击率': 3.89}, ATK_CRIT)
        self.assertEqual(per, [0.0, 1.0])
        self.assertEqual(total, 1.0)


class CharacterFallbackTests(unittest.TestCase):
    def test_empty_selection_uses_atk_crit(self):
        characters = {
            '----请选择角色----': {},
            '常规主C-攻暴': ATK_CRIT,
        }
        config, notice = er.resolve_character_config('----请选择角色----', characters)
        self.assertEqual(config, er.FALLBACK_CONFIG)
        self.assertIsNone(notice)

    def test_missing_character_notice(self):
        config, notice = er.resolve_character_config('不存在的角色', {'常规主C-攻暴': ATK_CRIT})
        self.assertEqual(config, er.FALLBACK_CONFIG)
        self.assertIn('不存在的角色', notice)
        self.assertIn(er.FALLBACK_NAME, notice)


if __name__ == '__main__':
    unittest.main()
