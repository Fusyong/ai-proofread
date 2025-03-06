

## 兼容OpenAI SDK

```shell
pip3 install openai,google-genai,dotenv
```

不再用google-generativeai

## 定价

https://api-docs.deepseek.com/zh-cn/quick_start/pricing


## Temperature 设置

temperature 参数默认为 1.0。
我们建议您根据如下表格，按使用场景设置 temperature。

| 场景                | 温度 |
| ------------------- | ---- |
| 代码生成/数学解题   | 0.0  |
| 数据抽取/分析       | 1.0  |
| 通用对话            | 1.3  |
| 翻译                | 1.3  |
| 创意类写作/诗歌创作 | 1.5  |

## token

https://api-docs.deepseek.com/zh-cn/quick_start/token_usage

1 个英文字符 ≈ 0.3 个 token。
1 个中文字符 ≈ 0.6 个 token。

## 查询余额

```py
import requests

url = "https://api.deepseek.com/user/balance"

payload={}
headers = {
  'Accept': 'application/json',
  'Authorization': 'Bearer <TOKEN>'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)
```

## 集成环境

https://github.com/deepseek-ai/awesome-deepseek-integration/tree/main

## 用量

https://platform.deepseek.com/usage

## docx to markdown

```shell
set myfilename="myfilename"
pandoc -t markdown_strict --extract-media="./attachments/%myfilename%" %myfilename%.docx -o %myfilename%.md
```

手动检查`\`
