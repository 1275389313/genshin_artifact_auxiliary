<div align='center'>

# 刻晴办公桌

[![GitHub downloads](https://img.shields.io/github/downloads/SkeathyTomas/genshin_artifact_auxiliary/total?style=flat-square)](https://github.com/SkeathyTomas/genshin_artifact_auxiliary/releases)
[![GitHub release (latest by date)](https://img.shields.io/github/downloads/SkeathyTomas/genshin_artifact_auxiliary/latest/total?style=flat-square)](https://github.com/SkeathyTomas/genshin_artifact_auxiliary/releases/latest)

</div>

## 简介

帮你在角色圣遗物装配页查看有效词条：选角色、F8 扫五件，合计贴在页签上，结果按角色自动保存在本地。多角色适配，帮你省去记各角色有效词条、口算/按计算器的时间。

相比于其他评分工具的优势：

1. 与游戏本身有更好的贴合性，每个圣遗物右下角标注评分结果，可以让玩家对于圣遗物好坏有更加方便直观的判断。
2. 省去了一些截图、角色装配调来调去、游戏内外来回对比的麻烦。
3. 识别结果按角色自动保存在本地，下次打开同一角色即可看到上次扫描。

[demo&教程视频](https://www.bilibili.com/video/BV14g411W79L/)

![背包面板圣遗物](https://raw.githubusercontent.com/SkeathyTomas/img/main/img/20220929234442.png)

![角色面板圣遗物](https://raw.githubusercontent.com/SkeathyTomas/img/main/img/20220810004718.png)

## 环境与准备

### ~~OCR 引擎~~

注：v0.7.0 版本开始更换 paddleocr 为 OCR 引擎，已不需要手动安装 OCR 环境。paddleocr 在识别率上有更好的效果，可以处理后续主词条、名称识别等需求。

1. ~~OCR引擎[tesserect](https://github.com/tesseract-ocr/tesseract)，安装过程详见原项目，或者参考[这篇文章](https://www.jianshu.com/p/f7cb0b3f337a)，安装链接[tesseract-ocr-w64-setup-v5.3.0.20221214.exe](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v5.3.0.20221214.exe)(64位)。如果你使用`scoop`，可以使用`scoop install tesseract`快速安装。安装完成后，可在命令行输入`tesseract`检验是否安装成功。~~
2. ~~[tesseract中文简体数据文件](https://github.com/tesseract-ocr/tessdata_fast/blob/main/chi_sim.traineddata)，下载完成后保存到tesseract数据目录`tessdata`中（如果是`scoop`安装的话，放在`./scoop/persist/tesseract/tessdata`文件夹中）。~~

### 如果你需要直接运行 python 程序

1. Python 3.7~3.13 (作者开发环境 Python 3.13.5)。
2. 必备的Python包：
   1. PySide6，GUI 框架
   2. pynput，监听游戏窗口内鼠标操作
   3. pywin32，获取设备分辨率、缩放信息，用于兼容不同分辨率
   4. pyqtdarktheme，GUI 样式，使用了 0.1.7 老版本，新版本有兼容性问题
   5. rapidocr（请用当前版本；默认 PP-OCRv6，不要再强制 Det/Rec 为 PP-OCRv4/v5 small，否则会报 Invalid OCR configuration）。paddleocr 使用 onnx 模型接口，需另外安装 onnxruntime-directml 使用 GPU 加速；无 DirectML 时会回退默认引擎，详见 rapidocr 文档
   6. requests，新版本提醒

### 使用打包好的 exe 程序

1. 在 release 中下载最新的压缩包。
2. 解压。

## 使用教程

1. 打开游戏，手动在设置-图像-显示模式中调整为窗口或无边框。现已支持 **16:9 / 16:10** 窗口与全屏无边框，**含 4K（3840×2160）**，不必再强制改成 1920×1080。**请确定游戏窗口化/无边框打开且不要最小化，在工具启动后也不要移动游戏窗口**，否则捕捉窗口定位错误会使识别出错。建议无边框或稳定窗口模式；系统缩放 150%/200% 已按 DPI 处理。须**管理员**运行。

2. 方式1：运行打包好的程序。解压压缩包完成后，找到并用**管理员**模式运行 keqing.exe（必须，否则程序运行中无法监听游戏中的鼠标操作）。

![keqing.exe](https://raw.githubusercontent.com/SkeathyTomas/img/main/img/20220805144258.png)

3. 方式2：下载源码，使用管理员模式打开命令行工具（必须，否则程序运行中无法监听游戏中的鼠标操作），并打开程序目录，使用命令`python app.py`运行程序。
4. 在主窗口中选择角色（不选的话，默认评估双爆+攻击词条，即「常规主C-攻暴」）。选过并扫描过的角色会立刻显示上次五件结果。
5. 打开游戏内 **角色 → 圣遗物装配**。**贴图主数字是有效词条**（一位小数）。按 **F8**（可改）或点「扫描五件」，依次点击花→羽→沙→杯→冠并识别，合计显示为 `有效词条 28.4`。工具窗口下方只读展示五件摘要。扫描完成后按角色写入 `文档/keqing/equipped.json`。**F8 时原神需在最前**；工具会尝试自动置顶。
6. 游戏内贴图可用主窗口 **「清除贴图」** 或全局快捷键`Ctrl+Shift+Z`去掉（不删除已保存的角色扫描）。焦点在贴图上时 `Ctrl+Z` 去掉当前这块。

角色装配页有效词条、F8 扫描与公式说明见 [文档/有效词条.md](文档/有效词条.md)。

![主程序示意](https://raw.githubusercontent.com/SkeathyTomas/img/main/img/20221212182324.png)

## 评分方法

**贴图主数字**为社区口径有效词条：副词条数值 ÷ 五星单词条最大值（暴击率 3.89 / 暴击伤害 7.77 / 攻击%·生命% 5.83 / 防御% 7.29 / 充能 6.48 / 精通 23.31），保留一位小数。`character.json` 里系数 > 0 才计入（只做过滤，不乘 `coefficient.json` 权重）；小攻击/小生命/小防御默认不计，`攻击力` 等名称只对应百分比词条。详见 [文档/有效词条.md](文档/有效词条.md)。

旧版刻晴加权分（大约 30 勉强、40 准毕业、50 极品）可在设置中打开，仅作次要显示。

具体每一个角色的有效词条可参考[character.json](src/character.json)和[doc.py](doc.py)、`文档/keqing/character.json`。旧评分系数在`文档/keqing/coefficient.json`，也可在设置页修改。

首次使用软件，角色评分系数配置文件`character.json`会复制一份到`文档/keqing/character.json`中，并优先使用此文件作为角色最终配置文件。如有需要修改角色配置，请修改以上文件，方便程序更新后保留用户个人配置。如果想要恢复至默认提供的参考配置，可以删除个人的配置文件，重启软件时会自动复制最新的默认配置。

## 已知问题

### 分辨率适配

已适配游戏窗口 16：10，16：9（含 4K 无边框/窗口），坐标按游戏窗口比例缩放，启动时会设 Per-Monitor DPI 感知，避免 150%/200% 缩放把 4K 窗口比例算错。若有分辨率适配问题，可查看程序目录中的`src/grab.png``src/out.png`识别截图是否准确，并提供一些不同分辨率的截图做坐标定位和测试了。

**4K 可用前提：** 游戏窗口本身是 16:9 或 16:10；启动后勿移动窗口；管理员运行；DPI 已由程序处理。仍建议无边框或稳定窗口模式。

如使用多屏设备（如笔记本外接显示器），请把游戏窗口置于第一屏。

目前已验证无问题的分辨率：

16:10：

- [x] 2560 * 1600
- [x] 3840 * 2400

16:9：

- [x] 2560 * 1440
- [x] 1920 * 1080
- [x] 3840 * 2160（原生 / 无边框，无需再改 1080p）

真正非 16:9/16:10 的比例（如 21:9）仍无法自动适配。

**Windows 冒烟（无法在 CI 开原神）：** 4K 无边框 16:9 启动后日志应出现 `物理桌面(3840, 2160)`、`ratio≈1.78 → 16:9`，而不是「请将游戏显示模式调至1920*1080」。角色装配页 F8 五件扫描，部位贴图应落在花/羽/沙/杯/冠，合计贴图在其下方且不互相遮挡；主窗口「清除贴图」应立刻去掉这些贴图。若系统为 200% 缩放，再确认一次点击与贴图仍对齐。

### 角色面板识别问题

背景飘过的白点和文字重叠可能会导致识别出错（感觉这个解决起来还是有点难度的，就算人眼去识别遮挡的文字可能也会出错，可能需要上下文，牵扯到数字可能就更没办法了）。

一般情况下再识别一次即可，可根据主程序面板的识别结果对比识别是否准确。

P.S. 更换 OCR 引擎后此问题已大幅改善。

### 关于GUI

暂未对滚动条进行适配，若下拉滚动条使第一行圣遗物显示不全，或者在角色面板点击靠下的圣遗物，因为游戏系统自动会移动滚动条，贴图结果可能会有垂直方向的偏移。

使用了默认的组件，某些高级整合/自改组件Bug一堆，问就是还在学，不过就问你能不能用吧。UI美化、Bug修复等1.0版本再考虑。

### 语言支持

- [x] 中文简体

## 声明与支持

- 本程序不收集任何用户信息，所有数据保留在本地。
- 理论上未对任何游戏数据进行非法获取和修改，仅通过截图和 OCR 技术实现相关分析，且没有使用自动化程序帮助玩家获取游戏内资源，应该不在官方打击范围。如若官方觉得不妥，我就删库跑路。
- 最近在 xx 软件园之类的网站看到了自己的软件，并看到了完全对不上的功能介绍。在此声明并非本人上传，不确定是否做过恶意修改，请谨慎在 release 以外渠道下载本软件/工具（除了本人 b 站视频贴的方便 GitHub 访问困难用户的度盘链接，以及本文档留下的 QQ 群）。

如果觉得有用/帮到了您的话，欢迎推荐给您的好友！

## 问题反馈

使用中有任何问题可以提 Issue，最好提供下命令行的输出（如识别错误、环境错误等）。

QQ群：119633609

## 需求来源

1. [如何做一个圣遗物管理系统：产品调研与分析](https://skeathytomas.github.io/post/%E5%A6%82%E4%BD%95%E5%81%9A%E4%B8%80%E4%B8%AA%E5%9C%A3%E9%81%97%E7%89%A9%E7%AE%A1%E7%90%86%E7%B3%BB%E7%BB%9F%EF%BC%9A%E4%BA%A7%E5%93%81%E8%B0%83%E7%A0%94%E4%B8%8E%E5%88%86%E6%9E%90/)
2. [如何做一个圣遗物管理系统：产品需求文档](https://skeathytomas.github.io/post/%E5%A6%82%E4%BD%95%E5%81%9A%E4%B8%80%E4%B8%AA%E5%9C%A3%E9%81%97%E7%89%A9%E7%AE%A1%E7%90%86%E7%B3%BB%E7%BB%9F%EF%BC%9A%E4%BA%A7%E5%93%81%E9%9C%80%E6%B1%82%E6%96%87%E6%A1%A3/)