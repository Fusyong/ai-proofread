# AI Proofreader VS Code Extension

这是一个基于AI的文档/图书校对VS Code插件，支持文档切分和AI校对功能；与Python脚本的功能大致相同。

以example/1.md为测试用例。

## 功能特点

1. 切分当前文档的多种方式（markdown和JSON结果在新文档中打开，缓存JSON结果）
    1. 按标题、长度带上下文切分（先按标题级别切分，然后将标题下的文字按长度切分为带上下文的片段），对应于splitting1.py
        * 可选择标题级别，如： 1, 2
        * 可选择切分长度，默认600字符
    2. 按标题加长度切分：按标题切分后，进一步处理过长和过短的片段，对应于splitting2.py
        *  levels: 切分标题级别，比如[1,2]表示按一级标题和二级标题切分
        *  threshold: 切分阈值，比如500表示当段落长度超过500时切分
        *  cut_by: 切分长度，比如300表示每段切分为300字符
        *  min_length: 最小长度，比如120表示长度小于120字符的段落会被合并到后一段
    3. 按标题切分，对应于splitting3.py
        * 可选择标题级别，如： 1, 2
    4. 按长度切分，对应于splitting4.py
        * 可选择切分长度
2. AI校对当前文档的方式
    1. 校对当前已经切分好的JSON文档，缓存JSON结果，对应proofreading1.py
    2. 一次性校对当前文档，对应于proofreading2.py
        1. 可选择上下文
        2. 可选择参考文档
    3. 校对当前文档中的选中文本
        1. 可设置选中文本所在的上下文级别
3. 设置
    1. API KEY
        1. DEEPSEEK_API_KEY
        2. GOOGLE_API_KEY
        3. ALIYPUN_API_KEY
    2. 4种各切分方式的默认值
    3. 3种校对方式的默认值

##

d vscode-extension && npm run dev
