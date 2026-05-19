"""
使用Deepseek的API调用函数，为专有名词查词典
"""

import os
import re
from typing import Dict, Any, List, Union
from src.special_checker.mdict import query_mdx
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolParam
)
from dotenv import load_dotenv

# 加载环境变量，用于安全地管理API密钥
load_dotenv()

# 定义函数规范，使用JSON Schema格式描述函数的参数和返回值
# 这里定义了一个查词典的函数规范
tools: List[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_dictionary",
            "description": "查询专有名词（人名、地名、机构名、作品名等）的词典解释",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "要查询的专有名词"
                    },
                    "term_type": {
                        "type": "string",
                        "enum": ["person", "location", "organization", "work", "other"],
                        "description": "专有名词的类型"
                    }
                },
                "required": ["term", "term_type"]
            }
        }
    }
]

def extract_text_from_html(html_content: str) -> str:
    """
    从HTML内容中提取纯文本

    Args:
        html_content (str): 包含HTML标签的内容

    Returns:
        str: 提取出的纯文本
    """
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', html_content)
    # 移除XML标签
    text = re.sub(r'<\?xml[^>]+\?>', '', text)
    # 移除多余的空格和换行
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 模拟词典查询函数
# 实际应用中应该替换为真实的词典API调用
def lookup_dictionary(term: str, term_type: str) -> Dict[str, Any]:
    """
    模拟查询专有名词词典的函数

    Args:
        term (str): 要查询的专有名词
        term_type (str): 专有名词的类型

    Returns:
        Dict[str, Any]: 包含词典解释的字典
    """
    mdx_path = 'D:/通用资料/工具书/通用电子词典/1古汉语/cihai7/离线版/cihai7.mdx'
    content = query_mdx(mdx_path, term) or ""

    # 提取纯文本内容
    clean_content = extract_text_from_html(content)

    return {
        "term": term,
        "term_type": term_type,
        "explanation": clean_content
    }

def send_messages(
    messages: List[Union[ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam, ChatCompletionToolMessageParam, ChatCompletionSystemMessageParam]],
    tools: List[ChatCompletionToolParam]
) -> ChatCompletionMessage:
    """
    发送消息到DeepSeek API并获取响应

    Args:
        messages: 消息历史列表
        tools: 可用的函数定义列表

    Returns:
        ChatCompletionMessage: API的响应消息
    """
    # 初始化OpenAI客户端
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

    # 调用API
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    return response.choices[0].message

def deepseek(input: str) -> str:
    """
    调用deepseek模型，识别文本中的专有名词并查询词典

    Args:
        input (str): 用户输入的文本

    Returns:
        str: 模型处理后的文本，包含专有名词的解释
    """
    # 初始化消息列表，添加用户输入
    messages: List[Union[ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam, ChatCompletionToolMessageParam, ChatCompletionSystemMessageParam]] = [
        {"role": "user", "content": f"请分析用户输入中的专有名词（人名、地名、机构名、作品名等）的信息，如果它们的信息可能存在错误，那么请查询它们的词典解释；如果没有错误，则输出`is_correct`：\n\n{input}"}
    ]

    # 第一次调用获取函数调用请求
    message = send_messages(messages, tools)

    # 检查是否有函数调用
    if message.tool_calls:
        # 获取第一个函数调用
        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        function_args = eval(tool_call.function.arguments)

        # 执行函数调用
        if function_name == "lookup_dictionary":
            print(function_args)
            function_response = lookup_dictionary(**function_args)
            print(function_response)

            # 添加助手消息到消息历史
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": tool_call.function.arguments
                    }
                }]
            })

            # 添加函数调用结果到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(function_response)
            })

            # 添加系统提示，指导模型如何格式化输出
            messages.append({
                "role": "system",
                "content": "请根据词典查询结果来校对用户输入的文本，修正其中的错误，输出修正后的文本。"
            })

            # 第二次调用获取最终回答
            message = send_messages(messages, tools)
            return message.content or "No response from model"

    return message.content or "No response from model"


if __name__ == "__main__":
    # 测试程序
    TEST_TEXT = "我是一个爱写诗的人。"
    # TEST_TEXT = "李白是清代将军，字大白，号清涟居士。"
    # TEST_TEXT = "李白是唐代诗人，字太白，号青莲居士。"
    # TEST_TEXT = "李白是清代将军，湖南浏阳人，曾名花初。"
    # TEST_TEXT = "李白（1910—1949）是中国共产党党员和革命烈士，湖南浏阳人，曾名华初。"
    # TEST_TEXT = "李白是清代将军，湖南浏阳人，曾名花初，字大白，号清涟居士。"
    result = deepseek(TEST_TEXT)
    print(result)
