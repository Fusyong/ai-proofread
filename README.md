[一个校对中文书稿的工具集](https://github.com/Fusyong/ai-proofread)。

主要功能是使用Deepseek、阿里云百炼和Google Gemini（后者测试不充分）平台的大语言模型服务，对文本进行一般语言文字和知识性校对。**该主要功能、更新的功能已经做成vscode插件： [ai-proofread-vscode-extension](https://github.com/Fusyong/ai-proofread-vscode-extension)**

另包含一下跟校对相关的实验性的工具。

A toolkit for proofreading Chinese book manuscripts, mainly using the LLM services of Deepseek, Aliyun, and Google Gemini, the latter is not adequately tested. The main functions have been made into a vscode extension, [ai-proofread-vscode-extension](https://github.com/Fusyong/ai-proofread-vscode-extension).

Also includes some experimental tools related to proofreading.

## 安装

1. 访问[本代码库](https://github.com/Fusyong/ai-proofread)并下载
2. 安装依赖
    ```bash
    pip install .

    # 作为开发环境安装
    pip install -e .
    ```
3. 获取LLM API服务。如Deepseek API: (1)在[Deepseek开放平台](https://platform.deepseek.com/)上注册并实名认证, (2)[充值](https://platform.deepseek.com/top_up), (3)[创建API key](https://platform.deepseek.com/api_keys)
4. 准备API kye文件：在src路径下新建一个名为`.env`的文件, 用你的API kye替换"DEEPSEEK_API_KEY=your_key"中的"your_key"
    ```txt
    # src/.env
    DEEPSEEK_API_KEY=your_key
    GOOGLE_API_KEY=your_key
    ALIYPUN_API_KEY=your_key
    ```
    !!! warning 提示
        **请自行保证API key的安全!**

<!--词典解析 https://github.com/liuyug/mdict-utils -->

## 校对一段文字

如果仅仅是体验，或者是一边AI校对一边核实、誊改，请使用demo/example/example2中的例子：

1. your_markdown.md 要校对的文档（比如一段文字）
2. your_markdown_context.md 要校对文档所在的上下文，可选
3. your_markdown_reference.md 参考文档，可选
4. your_markdown_proofread.md 校对后的结果

准备好必要的文档，打开校对脚本demo/proofreading2.py，使用编辑器右上角的三角形图标（Run Python File）运行这个脚本（或在终端输入`py proofreading2.py`，下同），等待校对结束。

校对后，参考后文提到的比较校对前后变动的diff方法，即看到清晰的结果。

##  校对一本书或多本书的通用流程

1. 准备要校对的文件: 我建议使用markdown格式整理你需要校对的文件，在此假设你的文件是example中的your_markdown.md（包含对格式的必要说明）
2. 切分要校对的文件：打开文件切分脚本`demo/splitting1.py`（或其他`demo/splitting*.py`，脚本自身的文档有说明），运行；这时会生成两个文件，your_markdown.json（供下一步处理），your_markdown.json.md(由前者生成，用来观察处理是否导致错误)，同时你将看到终端输出了切分信息（如由过长的问题，可以通过加空行来处理）：
    >```text
    >片段号  字符数  起始文字
    >----------------------------------------
    >No.1    316     Markdown是一种简单的标
    >No.2    247     # 一级标题1
    >No.3    137     ## 二级标题3
    >No.4    360     # 一级标题2
    >No.5    301     ## 二级标题2
    >```
3. 校对准备好的文件：打开校对脚本`demo/proofreading1.py`, 其中有详细说明，可以根据需要调整；同上运行脚本，你会在终端看到正在调用API校对文本的进度信息。最后，如果有未成功的片段，可以重复运行（已经完成的部分会自动忽略）。最终得到三个文件：
    1. your_markdown.proofread.json.md 校对后的markdown文件
    2. your_markdown.proofread.json 供脚本使用的结果文件，你通常不用在意
    3. your_markdown.proofread.json.log 日志，保留了统计信息、错误信息等
4.  比较校对前后的变动：在vscode终，选择最初的your_markdown.md，打开右键菜单选择"选择以校对"；然后选择最终的your_markdown.proofread.json.md，打开右键菜单选择"与已选文件比较"。这样你就能清楚地看到改动细节了。

以上省略了很多细节，你可能碰到各种小问题，需要慢慢摸索。这是我建议你从身边找一位稍懂程序的人帮忙的原因。

## 比较原稿与校对后的差异（diff）

其一是上面说到的，直接使用vscode提供的比较工具，视觉清晰，操作方法。唯一的缺陷是无法保存为文档，作为审稿记录。

其二，通过vscode使用强大的git管理版本的工具，视觉效果与上面一致。此方法加上vscode的协作工具、github仓库，可实现写、编、校、排全流程无纸化协作，但较为复杂，需要专门学习。

其三，使用`src/diff_tools.py`文件中的`jsdiff_md_text`函数比较，结果保存为HTML，用浏览器查看，或可进一步转换为PDF文档。如需改变显示效果，可以修改模版文件`src/resource/jsdiff.html`。

## 核心功能模块

### 文本切分 (src/splitter.py)
- **按长度切分**: `cut_text_by_length()` - 在指定长度前后最近空行处切分
- **按标题切分**: `split_markdown_by_title()` - 按指定标题级别切分
- **按标题、长度切分，带语境**: `split_markdown_by_title_and_length_with_context()` - 结合标题和长度，提供上下文信息
- **中文句子切分**: `split_chinese_sentences()` - 按中文句子边界切分，支持：
  - 基本句末标点：`[。！？…]+['"）]*`
  - 段落标记（空行）
  - 特殊处理：列表项、标题（末尾可能无标点）、引号内句号、小数点识别等
- **简化版句子切分**: `split_chinese_sentences_simple()` - 仅按句末标点切分，不考虑格式

### 校对引擎 (src/proofreader.py)
- **多模型支持**: Deepseek (deepseek-chat, deepseek-reasoner), 阿里云百炼 (deepseek-v3), Google Gemini
- **异步处理**: 支持并发校对，提高效率
- **限速控制**: 内置API调用频率限制器
- **错误重试**: 自动重试失败的API调用

### 专项检查器 (src/special_checker/)
- **汉字检查**: `tgscc.py` - 通用规范汉字表查询，提示表外字和附录中的繁体字、异体字
- **智能检查**: `checker.py` - 基于N-gram模型和机器学习的文本错误检测（未完成）
- **中文处理**: `chinese.py` - 中文文本处理常用工具
- **相似文本匹配**: `match_similar_text.py` - 基于rapidfuzz的相似文本匹配

### 结构检查器 (src/structure_checker/)（未完成）
- **规则驱动检查**: 基于JSON规则文件检查文本的层级结构
- **标题和编号检查**: 检查标题层级、编号连续性等
- **树形结构构建**: 构建文本的树形结构并验证
- **HTML/JSON报告**: 生成可视化的检查报告

### 句子对齐工具
- **对齐算法**: `sentence_aligner.py` - 基于锚点机制和Jaccard相似度的快速对齐算法，适用于改动不大的文本
- **对齐两个文件的句子**： `align_sentences_in_two_files.py` - 生成可视化的HTML差异对比结果（逐条比较差异消耗资源因而有些卡顿），以及JSON数据

### 词典查询 (src/lookup_mdict.py)
- **MDict支持**: 查询MDict格式词典
- **专有名词识别**: 自动识别并查询人名、地名、机构名等

### 差异比较 (src/diff_tools.py)
- **HTML差异**: 生成可视化的HTML差异对比
- **标题一致性**: 检查校对前后标题结构的一致性

### PDF转Markdown格式清理
- `clear_pdf_book_txt_to_md.py` - 将PDF文本转换为结构化的Markdown格式，支持目录解析

## TODO

* [x] 句子切分器
* [x] 校对前后的句子对齐，生成类似勘误表的结果
* [x] 四种常见的文本切分方法
* [x] 支持参考资料
    * [x] 切分并添加语境
* [x] 支持语境(上下文)
* [x] 专项校对 special_checker.py
    1. [x] 通用规范汉字表查询，提示表外字和附录中的繁体字、异体字
    2. [x] 基于N-gram模型和机器学习的智能错误检测
    3. [ ] 地名、行政区划
    4. [ ] 引文
    5. [ ] 术语，专名
    6. [ ] 人名
    7. [ ] 低频度词汇
    8. [ ] 年代
    9. [ ] 注释
* [ ] 字词典数据、字表词表数据萃取
* [x] 智能体功能
    * [x] 遇到专有名词查字典 lookup_mdict.py，示例，未集成到校对工作流中
    * [x] 基于机器学习的文本错误检测
* [ ] 移入[ai-proofread-vscode-extension](https://github.com/Fusyong/ai-proofread-vscode-extension)中的新功能

## deepseek参考资料

[文档](https://api-docs.deepseek.com/zh-cn/)

temperature 参数默认为 1.3（1.0时极少错误改动，但召回率较低 TODO 需要尝试不同的值）。

官方建议您根据如下表格，按使用场景设置 temperature。

| 场景                | 温度 |
| ------------------- | ---- |
| 代码生成/数学解题   | 0.0  |
| 数据抽取/分析       | 1.0  |
| 通用对话            | 1.3  |
| 翻译                | 1.3  |
| 创意类写作/诗歌创作 | 1.5  |

1 个英文字符 ≈ 0.3 个 token。
1 个中文字符 ≈ 0.6 个 token。

## 处理文件

模型只适合处理文本文件，如纯文本、markdown等。

Markdown是一种简单的标记文本格式，用来了整理书稿，可以保留标题级别、图表、公式、脚注等绝大多数Word书稿的格式。建议书稿从一开始就用markdown格式处理。进一步学习可以参考[markdownguide.org](https://markdownguide.org/)。

目前你只需要了解，本库的文本分切工具需要依赖两种标记：
（1）标题级别（若干`#`后加一个空格）；
（2）空行。
在markdown格式中，一个或连续多个空行（效果不变）表示分段，而连续的非空行被看作一段。

为了尽可能使大模型看到意义连贯的文本，又避免一次生成太长的文本（有可能失去注意力，忽略细节），建议标出标题级别和段间空行。没有标题时程序将随机选择切分位置；段间没有空行可能导致切分结果过长，效果变差。


### 处理PDF文件

PDF文件，建议用Acrobat转换成HTML或docx后整理，再转换成markdown。

建议转换后与简单复制黏贴的纯文本（通常能保留所有字符）进行比较。

### pandoc转docx为markdown_strict

```bash
set myfilename="myfilename"

pandoc -f docx -t markdown-smart+pipe_tables+footnotes --wrap=none --toc --extract-media="./attachments/%myfilename%" %myfilename%.docx -o %myfilename%.md
```

或：

```shell
set myfilename="myfilename"
pandoc -t markdown_strict --extract-media="./attachments/%myfilename%" %myfilename%.docx -o %myfilename%.md
```

建议转换后与简单复制黏贴的纯文本（通常能保留所有字符）进行比较。

## 感谢

项目使用了以下数据资源，特此致谢：

* [RIME-LMDG-dicts](https://github.com/amzxyz/RIME-LMDG/tree/wanxiang/dicts)
* [jieba_dict.txt.big](https://github.com/fxsjy/jieba/tree/master/extra_dict)

## 许可 license（不含上述两种数据资源）

两个部分分别许可：

1. 提示词（the prompts）：Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)
2. 其余部分(the others)：MIT License
