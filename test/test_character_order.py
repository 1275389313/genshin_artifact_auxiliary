'''角色下拉：上线时间排序。分隔项 / 未知名 / 与 json 插入顺序无关。'''

import importlib.util
import json
import os
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    'character_order', os.path.join(_ROOT, 'character_order.py'))
co = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(co)


class SeparatorTests(unittest.TestCase):
    def test_placeholder_and_version_bar(self):
        self.assertTrue(co.is_placeholder('----请选择角色----'))
        self.assertTrue(co.is_separator('----请选择角色----'))
        self.assertTrue(co.is_separator('----5.8～7.0----'))
        self.assertTrue(co.is_separator('----风----'))
        self.assertFalse(co.is_placeholder('----风----'))
        self.assertFalse(co.is_separator('温迪'))
        self.assertFalse(co.is_separator('常规主C-攻暴'))


class SortHelperTests(unittest.TestCase):
    def test_newest_first_after_placeholder(self):
        names = [
            '温迪',
            '----请选择角色----',
            '奥黛塔',
            '玛薇卡',
            '可莉',
        ]
        ordered = co.sort_character_names(names)
        self.assertEqual(ordered[0], '----请选择角色----')
        self.assertEqual(ordered[1:], ['奥黛塔', '玛薇卡', '可莉', '温迪'])

    def test_known_release_order(self):
        # 7.0 > 6.0 下半 > 5.8 > 1.0 下半 > 1.0 首发
        names = ['温迪', '可莉', '伊涅芙', '菲林斯', '奥黛塔']
        ordered = co.sort_character_names(names)
        self.assertEqual(ordered, ['奥黛塔', '菲林斯', '伊涅芙', '可莉', '温迪'])

    def test_same_day_alphabetical(self):
        names = ['茜特菈莉', '玛薇卡']
        self.assertEqual(co.sort_character_names(names), ['玛薇卡', '茜特菈莉'])
        self.assertEqual(co.sort_character_names(reversed(names)), ['玛薇卡', '茜特菈莉'])

    def test_unknown_names_after_known(self):
        names = ['自定义C', '温迪', '奥黛塔', '自定义A']
        ordered = co.sort_character_names(names)
        self.assertEqual(ordered, ['奥黛塔', '温迪', '自定义A', '自定义C'])

    def test_separators_not_sorted_as_characters(self):
        names = [
            '----风----',
            '温迪',
            '----请选择角色----',
            '----5.8～7.0----',
            '奥黛塔',
            '----火----',
        ]
        ordered = co.sort_character_names(names)
        self.assertEqual(ordered[0], '----请选择角色----')
        self.assertEqual(ordered[1:3], ['奥黛塔', '温迪'])
        self.assertEqual(ordered[3:], ['----风----', '----5.8～7.0----', '----火----'])

    def test_presets_after_placeholder_before_characters(self):
        names = ['温迪', '种门-纯精通', '----请选择角色----', '常规主C-攻暴', '奥黛塔']
        ordered = co.sort_character_names(names)
        self.assertEqual(
            ordered,
            ['----请选择角色----', '种门-纯精通', '常规主C-攻暴', '奥黛塔', '温迪'],
        )

    def test_json_insertion_order_does_not_matter(self):
        appended = ['----请选择角色----', '温迪', '可莉', '奥黛塔']
        shuffled = ['奥黛塔', '----请选择角色----', '可莉', '温迪']
        self.assertEqual(
            co.sort_character_names(appended),
            co.sort_character_names(shuffled),
        )

    def test_oldest_first_opt_in(self):
        names = ['奥黛塔', '温迪', '可莉']
        self.assertEqual(
            co.sort_character_names(names, newest_first=False),
            ['温迪', '可莉', '奥黛塔'],
        )

    def test_duplicates_dropped(self):
        names = ['温迪', '温迪', '奥黛塔']
        self.assertEqual(co.sort_character_names(names), ['奥黛塔', '温迪'])


class SrcJsonCoverageTests(unittest.TestCase):
    def test_every_src_key_is_classified(self):
        path = os.path.join(_ROOT, 'src', 'character.json')
        with open(path, 'r', encoding='utf-8') as fp:
            keys = list(json.load(fp))
        leftover = []
        for name in keys:
            if co.is_separator(name) or name in co.GENERIC_PROFILE_SET:
                continue
            if name not in co.RELEASE_DATES:
                leftover.append(name)
        self.assertEqual(
            leftover, [],
            'src/character.json 有角色未写入 character_order.RELEASE_DATES',
        )

    def test_sorted_src_starts_with_placeholder_then_newest(self):
        path = os.path.join(_ROOT, 'src', 'character.json')
        with open(path, 'r', encoding='utf-8') as fp:
            keys = list(json.load(fp))
        ordered = co.sort_character_names(keys)
        self.assertEqual(ordered[0], '----请选择角色----')
        self.assertIn('常规主C-攻暴', ordered[1:10])
        playable = [
            n for n in ordered
            if n in co.RELEASE_DATES
        ]
        self.assertEqual(playable[0], '奥黛塔')
        self.assertEqual(playable[1], '旅行者-冰')
        self.assertEqual(playable[2], '阿罗夏')
        self.assertEqual(playable[-1], '香菱')  # 1.0 首发同日，名称升序最末
        self.assertLess(
            playable.index('伊涅芙'), playable.index('温迪'))
        self.assertTrue(co.is_separator(ordered[-1]))


if __name__ == '__main__':
    unittest.main()
