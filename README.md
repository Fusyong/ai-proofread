
# 校对中文书稿的Python工具集（相应的vscode插件见后）

[一个校对中文书稿的工具集](https://github.com/Fusyong/ai-proofread)，主要使用Deepseek和Gemini（后者测试不充分）。主要功能已经做成vscode插件： [ai-proofread-vscode-extension](https://github.com/Fusyong/ai-proofread-vscode-extension)。

A toolkit for proofreading Chinese book manuscripts, mainly using Deepseek and Gemini, the latter is not adequately tested. The main functions have been made into a vscode extension, [ai-proofread-vscode-extension](https://github.com/Fusyong/ai-proofread-vscode-extension).

!!!
    鉴于身边编辑同仁的一般情况, 以下说明均假设: 你使用Windows x64操作系统, 完全不懂编程, 但有一定的学习意愿. 我尽可能详尽而简洁地说明, 以便你自学上手. 尽管如此, 我还是建议你从身边找一位稍懂程序的人, 比如公司的网管, 请他对照这篇说明，帮助你把一个真实的校对例子跑起来, 这个小小的门槛有可能吓退很多人.

## 安装

1. [下载Python安装程序](https://www.python.org/downloads/windows/)(其中有运行Python脚本的解释器), 较新的电脑可先尝试Stable Releases中的Windows installer (64-bit)版本; 安装下载的安装程序, 务必勾选"Add python.exe to PATH"(让你的操作系统记住它的安装位置), 然后点击Install Now安装
2. [下载VS Code编辑器安装程序](https://code.visualstudio.com/Download)(用来处理和比较文件的编辑器), 通常选择User Installer x64; 使用默认选项安装下载的安装程序; 运行时会提醒你安装中文语言包"Chinese (Simplified) (简体中文) Language Pack for Visual Studio Code", 以及其他插件, 可以根据需要确定是否安装
3. [下载本代码库](https://github.com/Fusyong/ai-proofread/archive/refs/heads/main.zip), 解压到D盘根目录, 也就是说, 代码库中的内容在`D:\ai-proofread-main\`路径下; 在这个目录下, 使用鼠标右键菜单"通过 Code 打开". **以后, 大多数操作都在此环境中进行**
4. 获取Deepseek API服务: (1)在[Deepseek开放平台](https://platform.deepseek.com/)上注册, (2)[充值](https://platform.deepseek.com/top_up), (3)[创建API key](https://platform.deepseek.com/api_keys)
5. 准备API kye文件：在src路径下新建一个名为`.env`的文件, 用你的API kye替换"DEEPSEEK_API_KEY=your_key"中的"your_key"
    ```txt
    # src/.env
    DEEPSEEK_API_KEY=your_key
    GOOGLE_API_KEY=your_key
    ALIYPUN_API_KEY=your_key
    ```
    !!! WARNING
        **请自行保证API key的安全!**
6. 安装依赖库: 用``Ctrl+` ``打开终端(字母终端模拟程序, 我们跟计算机内核交互的基础界面), 复制下面的命令, 粘贴到终端中, 回车
    ```shell
    pip install openai
    pip install google-genai
    pip install dotenv
    ```

## 校对一段文字

如果仅仅是体验，或者是一边AI校对一边核实、誊改，请使用example2中的例子：

1. your_markdown.md 要校对的文档（比如一段文字）
2. your_markdown_context.md 要校对文档所在的上下文，可选
3. your_markdown_reference.md 参考文档，可选
4. your_markdown_proofread.md 校对后的结果

准备好必要的文档，打开校对脚本proofreading2.py，使用编辑器右上角的三角形图标（Run Python File）运行这个脚本（或在终端输入`py splitting1.py`，下同），等待校对结束。

校对后，参考后文提到的比较校对前后变动的diff方法，即看到清晰的结果。

##  校对一本书或多本书的通用流程

1. 准备要校对的文件: 我建议使用markdown格式整理你需要校对的文件，在此假设你的文件是example中的your_markdown.md（包含对格式的必要说明）
2. 切分要校对的文件：打开文件切分脚本splitting1.py（或其他splitting*.py，脚本自身的文档有说明），运行；这时会生成两个文件，your_markdown.json（供下一步处理），your_markdown.json.md(由前者生成，用来观察处理是否导致错误)，同时你将看到终端输出了切分信息（如由过长的问题，可以通过加空行来处理）：
    >```text
    >片段号  字符数  起始文字
    >----------------------------------------
    >No.1    316     Markdown是一种简单的标
    >No.2    247     # 一级标题1
    >No.3    137     ## 二级标题3
    >No.4    360     # 一级标题2
    >No.5    301     ## 二级标题2
    >```
3.  校对准备好的文件：打开校对脚本proofreading.py, 其中有详细说明，可以根据需要调整；同上运行脚本，你会在终端看到正在调用API校对文本的进度信息。最后，如果有未成功的片段，可以重复运行（已经完成的部分会自动忽略）。最终得到三个文件：
    1. your_markdown.proofread.json.md 校对后的markdown文件
    2. your_markdown.proofread.json 供脚本使用的结果文件，你通常不用在意
    3. your_markdown.proofread.json.log 日志，保留了统计信息、错误信息等
4.  比较校对前后的变动：在vscode终，选择最初的your_markdown.md，打开右键菜单选择"选择以校对"；然后选择最终的your_markdown.proofread.json.md，打开右键菜单选择"与已选文件比较"。这样你就能清楚地看到改动细节了。

以上省略了很多细节，你可能碰到各种小问题，需要慢慢摸索。这是我建议你从身边找一位稍懂程序的人帮忙的原因。

## 比较原稿与校对后的差异（diff）

其一是上面说到的，直接使用vscode提供的比较工具，视觉清晰，操作方法。唯一的缺陷是无法保存为文档，作为审稿记录。

其二，通过vscode使用强大的git管理版本的工具，视觉效果与上面一致。此方法加上vscode的协作工具、github仓库，可实现写、编、校、排全流程无纸化协作，但较为复杂，需要专门学习。

其三，使用diff_tools.py文件中的jsdiff_md_text函数比较，结果保存为HTML，用浏览器查看，或可进一步转换为PDF文档。如需改变显示效果，可以修改模版文件jsdiff.html。

## TODO

* [x] 四种常见的文本切分方法
* [x] 支持参考资料
    * [ ] 切分并添加语境
* [x] 支持语境(上下文)
* [ ] 介绍其他工具和文档
    * [x] diff_tools.py
    * [ ] jsdiff.html
* [ ] 专项校对
    1. [ ] 地名、行政区划
    2. [ ] 引文
    3. [ ] 术语，专名
    4. [ ] 人名
    5. [ ] 低频度词汇
    6. [ ] 年代
    7. [ ] 注释
    8. [ ] 通用规范汉字表查询
* [ ] 智能体(远景，对本地环境的感知和操控, 如查字典和参考文档)

## deepseek参考资料

[文档](https://api-docs.deepseek.com/zh-cn/)

temperature 参数默认为 1.0（此时极少错误改动 TODO 需要尝试不同的值）。

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

Markdown是一种简单的标记文本格式，用来了整理书稿，可以保留标题级别、图表、公式、脚注等绝大多数Word书稿的格式。建议书稿从一开始就用markdown格式处理。进一步学习可以参考[markdownguide.org](https://www.markdownguide.org/)。

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

