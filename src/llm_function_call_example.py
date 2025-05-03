"""
使用OpenAI的API调用函数
这个示例展示了如何使用大语言模型进行函数调用，实现更复杂的功能
"""

import os
from typing import Dict, Any, List
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam
)
from dotenv import load_dotenv

# 加载环境变量，用于安全地管理API密钥
load_dotenv()

# 定义函数规范，使用JSON Schema格式描述函数的参数和返回值
# 这里定义了一个获取天气信息的函数规范
tools: List[ChatCompletionToolParam] = [
    {
        "type": "function",  # 指定这是一个函数调用
        "function": {
            "name": "get_weather",  # 函数名称
            "description": "获取指定城市的天气信息",  # 函数描述
            "parameters": {  # 参数定义
                "type": "object",
                "properties": {
                    "city": {  # 城市参数
                        "type": "string",
                        "description": "城市名称"
                    },
                    "unit": {  # 温度单位参数
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],  # 可选值
                        "description": "温度单位"
                    }
                },
                "required": ["city"]  # 必需参数
            }
        }
    }
]

# 模拟天气API函数
# 实际应用中应该替换为真实的天气API调用
def get_weather(city: str, unit: str = "celsius") -> Dict[str, Any]:
    """
    模拟获取天气信息的函数

    Args:
        city (str): 城市名称
        unit (str, optional): 温度单位，默认为摄氏度

    Returns:
        Dict[str, Any]: 包含天气信息的字典
    """
    # 这里应该是实际的API调用
    return {
        "city": city,
        "temperature": 25,
        "unit": unit,
        "condition": "sunny"
    }

def send_messages(
    messages: List[ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam | ChatCompletionToolMessageParam],
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
        model="deepseek-chat",  # 使用的模型
        messages=messages,  # 消息历史
        tools=tools,  # 可用的函数
        tool_choice="auto"  # 让模型自动决定是否需要调用函数
    )
    return response.choices[0].message

def deepseek(input: str) -> str:
    """
    调用deepseek校对模型，返回校对后的文本

    Args:
        input (str): 用户输入的文本

    Returns:
        str: 模型处理后的文本
    """
    # 初始化消息列表，添加用户输入
    messages: List[ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam | ChatCompletionToolMessageParam] = [
        {"role": "user", "content": input}
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
        if function_name == "get_weather":
            function_response = get_weather(**function_args)

            # 添加助手消息到消息历史
            # 包含函数调用的信息
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

            # 第二次调用获取最终回答
            # 将JSON数据转换为自然语言
            # 添加适当的语气和补充信息
            # 根据上下文提供更完整的回答
            message = send_messages(messages, tools)
            return message.content or "No response from model"

    return message.content or "No response from model"

if __name__ == "__main__":
    # 测试程序
    result = deepseek("北京今天天气怎么样？")
    print(result)
