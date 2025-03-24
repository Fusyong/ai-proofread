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

## TODO

* 校对过程中允许用户终止校对

## 使用说明

### 1. 初始配置

1. 在 VS Code 设置中配置 API 密钥（必需）：
   * `ai-proofread.apiKeys.deepseekChat`: deepseek API 密钥
   * `ai-proofread.apiKeys.aliyun`: 阿里云 aliyun API 密钥(为充分测试)
   * `ai-proofread.apiKeys.google`: Google API 密钥(为充分测试)

2. 可选配置项：
   * `ai-proofread.proofread.model`: 选择默认校对模型（deepseek/aliyun/google）
   * `ai-proofread.proofread.rpm`: 设置每分钟最大请求数（默认15）
   * `ai-proofread.proofread.maxConcurrent`: 设置最大并发请求数（默认3）
   * `ai-proofread.defaultSplitLength`: 设置默认切分长度（默认600字符）
   * `ai-proofread.defaultTitleLevels`: 设置默认标题切分级别（默认[2]）

### 2. 文档切分功能

右键点击编辑器，可以看到以下切分选项：

1. **按长度切分** (Split File by Length)
   * 输入目标切分长度
   * 生成 `.json` 和 `.json.md` 两个结果文件

2. **按标题切分** (Split File by Title)
   * 输入标题级别（如：1,2）
   * 生成 `.json` 和 `.json.md` 两个结果文件

3. **带上下文切分** (Split File with Context)
   * 输入标题级别和切分长度
   * 生成带上下文的切分结果

4. **高级切分** (Split File by Title and Length)
   * 自动处理过长和过短的段落
   * 可配置阈值、切分长度和最小长度

所有切分操作都会生成日志文件（`.log`），记录切分统计信息。

### 3. AI 校对功能

1. **校对 JSON 文件** (Proofread File)
   * 打开已切分的 JSON 文件
   * 右键选择 "Proofread File"
   * 自动使用配置的默认模型进行校对
   * 支持进度显示和取消操作
   * 结果保存为 `.proofread.json` 文件

2. **校对选中文本** (Proofread Selection)
   * 仅支持 Markdown 或 ConTeXt 文件
   * 选中要校对的文本
   * 右键选择 "Proofread Selection"
   * 可选择是否使用上下文和参考文件
   * 结果在新窗口中显示

### 4. 日志和统计

* 所有操作都会生成详细的日志文件
* 日志包含：
  * 操作时间戳
  * 处理字数统计
  * 切分/校对详情
  * 错误信息（如果有）

### 5. 注意事项

1. 确保在使用前已正确配置 API 密钥
2. 长文本建议先切分后校对
3. 校对过程可以随时取消，已处理的内容会被保存
4. 注意 API 调用频率限制，可通过配置调整

## 开发

```bash
# 切换到插件路径
cd vscode-extension

# 开发模式
cd vscode-extension && npm run dev

# 编译
cd vscode-extension && npm run compile

# 打包
cd vscode-extension && vsce package
```
