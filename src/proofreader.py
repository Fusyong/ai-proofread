"""
api_processor.py
用于调用API处理文本的工具模块
"""

import os
import json
import time
import asyncio
from typing import List, Callable
from concurrent.futures import ThreadPoolExecutor

from google import genai
from google.genai import types
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 读取上一层文件夹中的提示文件
# parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# prompt_file_path = os.path.join(parent_dir, "prompt-proofreader.md")
PROMPT_FILE_PATH = "src/prompt-proofreader-system.xml"
SYSTEM_PROMPT = ""
with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as file:
    SYSTEM_PROMPT = file.read()

class RateLimiter:
    """
    限速器类，用于控制API调用频率
    """
    def __init__(self, rpm: int):
        self.interval = 60 / rpm
        self.last_call_time = 0
        self.lock = asyncio.Lock()

    async def wait(self):
        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time
            if elapsed < self.interval:
                wait_time = self.interval - elapsed
                await asyncio.sleep(wait_time)
            self.last_call_time = time.time()


def deepseek(content: str, reference: str="", model:str="deepseek-chat") -> str|None:
    """
    调用各家deepseek校对模型，返回校对后的文本

    model: deepseek-chat
           deepseek-v3
    context: 上下文(其中可能包含需要校对的文本)
    """

    client: OpenAI|None = None
    if model == "deepseek-chat" or model == "deepseek-reasoner":
        # 初始化deepseek客户端
        client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
    elif model == "deepseek-v3":
        # 初始化阿里云deepseek v3
        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            # 如何获取API Key：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
            api_key=os.getenv("ALIYPUN_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
    else:
        print(f"模型名称错误：{model}")
        return None

    retry_count = 0
    result = ""

    message= [{"role": "system", "content": SYSTEM_PROMPT}]
    # 单独提交一轮reference可节省token但效果有待验证 TODO
    if reference:
        message.extend([{"role": "assistant", "content": ""},
                        {"role": "user", "content": reference}])
    message.extend([{"role": "assistant", "content": ""},# 回答示例，避免模型应答
                    {"role": "user", "content": content},])
    # print(message)

    while retry_count < 3:
        try:
            print(f"正在调用 {model} API (尝试 {retry_count+1}/3)...")
            response = client.chat.completions.create(
                model=model,
                messages=message, # type: ignore
                temperature=1,
                stream=False,
            )
            result = response.choices[0].message.content
            if result:
                break
        except Exception as e:
            print(f"API调用出错: {str(e)}")
            # 优化等待时间策略
            wait_time = 5 + retry_count * 3
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
            retry_count += 1
            continue

    result = result.replace("\n</target>", "").replace("<target>\n", "")

    return result


async def deepseek_async(content: str, reference: str, model:str, rate_limiter: RateLimiter) -> str|None:
    """
    异步调用deepseek校对模型，返回校对后的文本
    """
    await rate_limiter.wait()

    # 使用线程池执行同步API调用
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            lambda: deepseek(content, reference, model)
        )
    return result

# 配置Google API
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"),)

def chat_google(text: str) -> str|None:
    """
    调用google校对模型，返回校对后的文本
    """
    retry_count = 0
    result = ""
    while retry_count < 3:
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                # max_output_tokens=3,
                temperature=1,
            ),
        )
        result = response.text
        if result:
            break
        retry_count += 1
        time.sleep(3)  # 减少等待时间
    return result


async def chat_google_async(text: str, rate_limiter: RateLimiter) -> str|None:
    """
    异步调用google校对模型，返回校对后的文本
    """
    await rate_limiter.wait()

    # 使用线程池执行同步API调用
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            lambda: chat_google(text)
        )
    return result


async def process_paragraphs_async(json_in: str, json_out: str, start_count: int|list[int]=1, stop_count: int|None=None, model: str="deepseek-chat", rpm: int=15, max_concurrent: int=3):
    """
    异步处理文本段落，直接将结果存储到 JSON 文件中

    Args:
        json_in (str): 输入 JSON 文件路径
        json_out (str): 输出 JSON 文件路径
        start_count (int|list[int]): 开始处理的段落索引（从1开始），默认为1
        stop_count (int|None): 结束处理的段落索引，默认为None（处理到最后）
        model (str): 使用的模型，默认为"deepseek-chat"
        rpm (int): 每分钟请求数，默认为30
        max_concurrent (int): 最大并发数，默认为3
    """
    # 读取输入 JSON 文件
    with open(json_in, "r", encoding="utf-8") as f:
        input_paragraphs: List[dict] = json.load(f)

    input_paragraphs_length = len(input_paragraphs)

    # 如果输出 JSON 文件已存在，读取它，继续处理；否则创建空列表
    output_paragraphs: List[str|None] = []
    if os.path.exists(json_out):
        try:
            with open(json_out, "r", encoding="utf-8") as f:
                output_paragraphs = json.load(f)

            # 确保输出 JSON 的长度与输入 JSON 相同
            if len(output_paragraphs) != input_paragraphs_length:
                # 如果长度不同，中断处理
                raise ValueError(f"输出 JSON 的长度与输入 JSON 的长度不同: {len(output_paragraphs)} != {input_paragraphs_length}")
        except (json.JSONDecodeError, FileNotFoundError):
            # 如果文件不存在或格式错误，创建新的输出列表
            output_paragraphs = [None] * input_paragraphs_length
    else:
        # 创建与输入 JSON 长度相同的空列表
        output_paragraphs = [None] * input_paragraphs_length

        # 确保输出目录存在
        os.makedirs(os.path.dirname(json_out), exist_ok=True)

        # 创建初始的输出 JSON 文件
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(output_paragraphs, f, ensure_ascii=False, indent=2)

    # 确定要处理的段落索引
    indices_to_process = []

    if isinstance(start_count, int):
        # 处理从 start_count 到 stop_count 的段落
        start_index = start_count - 1
        stop_index = input_paragraphs_length - 1 if stop_count is None else stop_count - 1

        for i in range(start_index, stop_index + 1):
            if i < input_paragraphs_length and output_paragraphs[i] is None:
                indices_to_process.append(i)
    elif isinstance(start_count, list):
        # 处理指定索引的段落
        for idx in start_count:
            i = idx - 1  # 转换为 0-indexed
            if 0 <= i < input_paragraphs_length and output_paragraphs[i] is None:
                indices_to_process.append(i)

    # 创建日志文件
    log_file_path = f"{json_out}.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"\n{'='*50}\n")
        log_file.write(f"异步处理开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"待处理段落数: {len(indices_to_process)}/{input_paragraphs_length}\n")
        log_file.write(f"最大并发数: {max_concurrent}\n")
        log_file.write(f"{'='*50}\n\n")

    # 创建限速器和信号量
    rate_limiter = RateLimiter(rpm)
    semaphore = asyncio.Semaphore(max_concurrent)

    # 创建文件锁，用于安全地更新 JSON 文件
    file_lock = asyncio.Lock()

    # 定义异步处理任务
    async def process_one(i):
        async with semaphore:
            target_text = input_paragraphs[i]["target"]
            reference_text = input_paragraphs[i]["reference"] if "reference" in input_paragraphs[i] else ""
            context_text = input_paragraphs[i]["context"] if "context" in input_paragraphs[i] else ""

            # 判断是否需要添加上下文
            is_with_context = context_text and context_text.strip() != target_text.strip()
            print(f"处理 {i+1}/{input_paragraphs_length}{' with context' if is_with_context else ''}{' with reference' if reference_text else ''}:\n{target_text[:30]} ...\n")

            # 加标签，合并
            pre_text = f"<reference>\n{reference_text}\n</reference>" if reference_text else ""
            # 合并位置的优劣有待测试  TODO
            if is_with_context:
                pre_text += f"\n<context>\n{context_text}\n</context>"
            post_text = f"<target>\n{target_text}\n</target>"

            start_time = time.time()

            # 等待限速器
            await rate_limiter.wait()

            # 调用相应的 API
            processed_text = None
            if model.startswith("deepseek"):
                processed_text = await deepseek_async(post_text, pre_text, model, rate_limiter)
            elif model == "google":
                processed_text = await chat_google_async(pre_text+'\n'+post_text, rate_limiter)
            else:
                print(f"不支持的模型: {model}")
                return

            end_time = time.time()
            elapsed = end_time - start_time

            if processed_text:
                # 如果成功获取结果，更新输出 JSON
                async with file_lock:
                    try:
                        # 重新读取 JSON 文件，以防其他任务已经更新了它
                        with open(json_out, "r", encoding="utf-8") as f:
                            current_output = json.load(f)

                        # 更新当前段落的处理结果
                        current_output[i] = processed_text

                        # 保存更新后的 JSON
                        with open(json_out, "w", encoding="utf-8") as f:
                            json.dump(current_output, f, ensure_ascii=False, indent=2)
                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        print(f"更新 JSON 文件时出错: {str(e)}")
                        # 如果文件不存在或格式错误，重新创建
                        current_output: List[str|None] = [None] * input_paragraphs_length
                        current_output[i] = processed_text
                        with open(json_out, "w", encoding="utf-8") as f:
                            json.dump(current_output, f, ensure_ascii=False, indent=2)

                print(f"完成 {i+1}/{input_paragraphs_length} 长度 {len(target_text)} 用时 {elapsed:.2f}s\n{'-'*40}\n")

                # 记录日志
                async with file_lock:
                    with open(log_file_path, "a", encoding="utf-8") as log_file:
                        log_file.write(f"完成 {i+1}/{input_paragraphs_length} 长度 {len(target_text)} 用时 {elapsed:.2f}s\n")
            else:
                print(f"段落 {i+1}/{input_paragraphs_length}: 处理失败，跳过\n{'-'*40}\n")

                # 记录日志
                async with file_lock:
                    with open(log_file_path, "a", encoding="utf-8") as log_file:
                        log_file.write(f"段落 {i+1}/{input_paragraphs_length}: 处理失败，跳过\n")
                        log_file.write(f"原文: {target_text.strip().splitlines()[0][:20]}...\n{'-'*40}\n")

    # 如果没有需要处理的段落，直接返回
    if not indices_to_process:
        print("没有需要处理的段落")
        return output_paragraphs

    # 创建所有任务
    tasks = [process_one(i) for i in indices_to_process]

    # 等待所有任务完成
    await asyncio.gather(*tasks)

    # 记录处理完成信息
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"\n{'='*50}\n")
        log_file.write(f"处理结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 重新读取输出 JSON 以获取最新状态
        with open(json_out, "r", encoding="utf-8") as f:
            final_output = json.load(f)

        # 统计已处理和未处理的段落数
        processed_count = sum(1 for p in final_output if p is not None)
        processed_length = sum(len(p) for p in final_output if p is not None)
        log_file.write(f"已处理段落数、字数: {processed_count}/{input_paragraphs_length}, {processed_length}/{sum(len(p) for p in input_paragraphs)}\n")
        log_file.write(f"未处理段落数: {input_paragraphs_length - processed_count}/{input_paragraphs_length}\n")
        log_file.write(f"{'='*50}\n\n")

    # 生成 Markdown 文件
    md_file_path = f"{json_out}.md"
    with open(md_file_path, "w", encoding="utf-8") as f:
        # 只包含已处理的段落
        processed_paragraphs = [p for p in final_output if p is not None]
        f.write("\n\n".join(processed_paragraphs))

    return final_output


def process_by_once(file_in: str, file_out: str, chat_func: Callable=deepseek, model: str="deepseek-chat"):
    """
    一次性处理整个文件
    """
    with open(file_in, encoding="utf8",mode="r") as f:
        with open(file_out,encoding="utf8", mode="w") as f_out:
            text = f.read()
            text = chat_func(text, model=model)
            if text:
                f_out.write(text)
