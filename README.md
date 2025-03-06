校对中文书稿的工具集，主要使用Deepseek和Gemini

A toolkit for proofreading Chinese book manuscripts, mainly using Deepseek and Gemini

## 安装

```shell
pip install openai,google-genai,dotenv
```

*不再用google-generativeai*

## 使用

在src中新建一个`.env`文件，存放你的api key

```txt
# src/.env
DEEPSEEK_API_KEY=your_key
GOOGLE_API_KEY=your_key
ALIYPUN_API_KEY=your_key
```

**请自行保证api key的安全！！！**

## deepseek参考资料

[文档](https://api-docs.deepseek.com/zh-cn/)

temperature 参数默认为 1.0。
我们建议您根据如下表格，按使用场景设置 temperature。

| 场景                | 温度 |
| ------------------- | ---- |
| 代码生成/数学解题   | 0.0  |
| 数据抽取/分析       | 1.0  |
| 通用对话            | 1.3  |
| 翻译                | 1.3  |
| 创意类写作/诗歌创作 | 1.5  |

1 个英文字符 ≈ 0.3 个 token。
1 个中文字符 ≈ 0.6 个 token。

## pandoc转docx为markdown_strict

```shell
set myfilename="myfilename"
pandoc -t markdown_strict --extract-media="./attachments/%myfilename%" %myfilename%.docx -o %myfilename%.md
```