'''图像识别、文字处理，考虑多种ocr方式'''

from PIL import ImageGrab, Image
import re
import sys
from rapidocr import RapidOCR
from paths import ocr_cache_path

# Frozen src/ is not a writable working directory; dump debug images to %TEMP%/keqing_ocr/.
_GRAB_PNG = ocr_cache_path('grab.png')
_OUT_PNG = ocr_cache_path('out.png')


def _init_ocr():
    '''跟随 rapidocr 默认版本（PP-OCRv6+）。优先 DirectML，失败则回退默认引擎。'''
    try:
        return RapidOCR(params={"EngineConfig.onnxruntime.use_dml": True})
    except Exception as e:
        print(f'RapidOCR DirectML 初始化失败（{e}），回退默认引擎')
        return RapidOCR()


ocr = _init_ocr()

# 与 location.is_invalid_grab_bbox 同口径；不 import location，避免独立跑 ocr.py 时等待游戏窗口。
_MINIMIZED_COORD_MAX = -16000
BLANK_GRAB_MSG = '截图空白，请确认原神窗口在最前且角色圣遗物详情已打开'


def is_invalid_grab_bbox(x, y, w, h):
    '''w/h<=0 或坐标接近最小化哨兵时不可送进 ImageGrab。'''
    try:
        x = float(x)
        y = float(y)
        w = float(w)
        h = float(h)
    except (TypeError, ValueError):
        return True
    if w <= 0 or h <= 0:
        return True
    if x + w <= x or y + h <= y:
        return True
    if min(x, y, x + w, y + h) <= _MINIMIZED_COORD_MAX:
        return True
    return False


def is_near_blank_image(img, near=16, min_ratio=0.96):
    '''几乎全白或全黑的截图（被其它窗口挡住时 ImageGrab 常见近白 ~252）。'''
    if img is None:
        return True
    try:
        gray = img.convert('L')
        hist = gray.histogram()
        n = gray.size[0] * gray.size[1]
    except Exception:
        return False
    if n <= 0:
        return True
    near_black = sum(hist[:near + 1])
    near_white = sum(hist[255 - near:])
    return (near_black / n) >= min_ratio or (near_white / n) >= min_ratio


def require_ocr_texts(txts):
    '''RapidOCR 无检测结果时 txts 为 None，不能直接 for 迭代。'''
    if txts is None:
        raise ValueError(BLANK_GRAB_MSG)
    try:
        empty = len(txts) == 0
    except TypeError:
        raise ValueError(BLANK_GRAB_MSG)
    if empty:
        raise ValueError(BLANK_GRAB_MSG)
    return txts


def _bring_game_foreground():
    '''复用已加载的 location.bring_game_to_foreground，避免此处 import 触发等窗口。'''
    loc = sys.modules.get('location')
    fn = getattr(loc, 'bring_game_to_foreground', None) if loc is not None else None
    if not callable(fn):
        return False
    try:
        return bool(fn())
    except Exception as exc:
        print(f'置顶游戏窗口失败: {exc}')
        return False


def rapid_ocr(x, y, w, h):
    '''返回使用paddle ocr引擎识别及处理结果
    参数：
        x：截图坐标x
        y：截图坐标y
        w：截图宽度w
        h：截图高度h
    返回：
        basic：主词条等基本信息list
            名称，部位，主属性，数值，等级
            ['雷云之笼', '时之沙', '攻击力', '46.6%', '+20']
        result：副词条属性dict
            key：词条属性（含百分比差异说明）
            value：词条数值
            如：{'防御力': 23.0, '元素充能效率': 5.8, '暴击伤害': 5.4}
    '''

    if is_invalid_grab_bbox(x, y, w, h):
        raise ValueError(
            f'截图区域无效 x,y,w,h=({x}, {y}, {w}, {h})。'
            '游戏窗口可能已最小化或尚未还原，请还原「原神」窗口后重试。'
        )

    _bring_game_foreground()

    # 截屏与ocr识别
    img = ImageGrab.grab(bbox = (x, y, x + w, y + h))
    img.save(_GRAB_PNG)
    if is_near_blank_image(img):
        raise ValueError(BLANK_GRAB_MSG)
    result = ocr(_GRAB_PNG, use_det=True, use_cls=False, use_rec=True)
    txts = None if result is None else getattr(result, 'txts', None)
    txts = require_ocr_texts(txts)
    try:
        result.vis(_OUT_PNG)
    except Exception as e:
        print(f'OCR 调试图写出失败（{_OUT_PNG}）：{e}')

    # 千位符（含误识别的.）兼容并转化为list
    pattern_thou = r'\d\.\d{3}|\d\,\d{3}'
    txt = [re.sub(pattern_thou, item.replace(',', '').replace('.', ''), item) for item in txts]
    print(txt)

    # ocr错误修正，并构建基础信息
    name = txt[0]
    ocr_correct = [['灵髓的根脈', '灵髓的根脉'],
                   ['角斗士的酬醉', '角斗士的酣醉'],
                   ['雷灾的子遗', '雷灾的孑遗'],
                   ['傑作的序曲', '杰作的序曲'],
                   ['康慨的墨水瓶', '慷慨的墨水瓶'],
                   ['命途轮转的谐滤', '命途轮转的谐谑']]
    for item in ocr_correct:
        if name == item[0]:
            name = name.replace(item[0], item[1])
            break
    parts = txt[1]
    main_name = txt[2]
    main_digit = txt[3]
    # 有时候「星星」会作为特殊符号被识别出来，需要兼容下
    for i in range(5):
        if '+' not in txt[i+4]:
            continue
        else:
            lvl = txt[i+4]
            break
    basic = [name, parts, main_name, main_digit, lvl]

    # 副词条构建，中文和数字正则
    pattern_chinese = r'[\u4e00-\u9fa5]+'
    pattern_digit = r'\d+(\.\d+)?'

    result = {}
    normal_name = ['攻击力', '生命值', '防御力', '元素精通', '元素充能效率', '暴击率', '暴击伤害']
    for item in txt[-5:]:
        try:
            # 词条名称
            name = re.findall(pattern_chinese, item)
            name = name[0] # 末尾可能识别出奇怪的中文字符，所以以第一个搜索到的中文字符串为准
            if name not in normal_name:
                continue
            # 数值
            digit = float(re.search(pattern_digit, item).group())
            # 兼容千位符
            if digit < 2:
                digit *= 1000
            if name in '暴击率':
                result['暴击率'] = digit
            elif name in '暴击伤害':
                result['暴击伤害'] = digit
            elif name in '元素精通':
                result['元素精通'] = digit
            elif name in '攻击力' and '%' in item:
                result['攻击力百分比'] = digit
            elif name in '攻击力':
                result['攻击力'] = digit
            elif name in '生命值' and '%' in item:
                result['生命值百分比'] = digit
            elif name in '生命值':
                result['生命值'] = digit
            elif name in '防御力' and '%' in item:
                result['防御力百分比'] = digit
            elif name in '防御力':
                result['防御力'] = digit
            elif name in '元素充能效率':
                result['元素充能效率'] = digit
            else:
                result[item] = 0
        except:
            pass
    
    print(basic, result)
    return basic, result

if __name__ == '__main__':
    # 截图坐标
    x, y, w, h = (1808, 277, 377, 714) # 副词条
    # x, y, w, h = (1948, 200, 360, 70) # 圣遗物名称

    # ocr测试
    import time
    start = time.time()
    rapid_ocr(x, y, w, h)
    end = time.time()
    print(end - start)
    
    # import score
    # print(score.cal_score(tesseract_ocr(x, y, w, h), '雷电将军'))