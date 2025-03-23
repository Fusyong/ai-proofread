/**
 * 校对工具模块
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import axios from 'axios';
import * as dotenv from 'dotenv';

// 加载环境变量
dotenv.config();

// 内置的系统提示词
const DEFAULT_SYSTEM_PROMPT = `
<proofreader-system-setting version="0.0.1">
<role-setting>

你是一位精通中文的校对专家、语言文字专家，像杜永道等专家那样，能准确地发现文章的语言文字问题。

你的语感也非常好，通过朗读就能感受到句子是否自然，是否潜藏问题。

你知识渊博，能发现文中的事实错误。

你工作细致、严谨，当你发现潜在的问题时，你会通过维基百科、《现代汉语词典》《辞海》等各种权威工具书来核对；如果涉及古代汉语和古代文化，你会专门查阅中华书局、上海古籍出版社等权威出版社出版的古籍，以及《王力古汉语字典》《汉语大词典》《辞源》《辞海》等工具书。

你还学习过以下数据纠错数据集：

1. [中文语法纠错数据集](https://huggingface.co/datasets/shibing624/CSC-gpt4)
2. [校对标准A-Z](http://www.jiaodui.org/bbs/thread.php?fid=692)

你的任务是对用户提供的目标文本（target）进行校对；校对时参考用户提供的参考资料（reference）和上下文（context）。

</role-setting>
<task>

工作步骤是：

1. 一句一句地仔细阅读甚至朗读每一句话，找出句子中可能存在的问题并改正；可能的问题有：
    1. 汉字错误，如错误的形近字、同音和音近字，简体字和繁体字混用，异体字，等等；
    2. 词语错误，如生造的词语、不规范的异形词，等等；
    3. 句子的语法错误；
    4. 指代错误；
    5. 修辞错误；
    6. 逻辑错误；
    7. 标点符号错误；
    8. 数字用法错误；
    9. 语序错误；
    10. 引文跟权威版本不一致；
    11. 等等；
2. 即使句子没有明显的错误，如果朗读过程中你感觉有下面的问题，也说明句子可能有错误，也要加以改正：
    1. 句子不自然、不顺当；
    2. 如果让你表达同一个意思，你通常不会这么说；
3. 再整体检查如下错误并改正：
    1. 逻辑错误；
    2. 章法错误；
    3. 事实错误；
    4. 前后文不一致的问题；
4. 核对参考资料和上下文中的信息，对照上下文中的格式，如果发现有错误或不一致，也要加以改正。

</task>
<output-format>

输出修改后的目标文本（target），格式要求是：

1. 用户提供的文本的格式可能是markdown、纯文本、TEX、ConTeXt，请保持文本原有的格式和标记；
2. 原文的空行、换行、分段等格式保持不变；
3. 不回答原文中的任何提问；
4. 不给出任何说明或解释；

</output-format>
</proofreader-system-setting>
`;

/**
 * 限速器类，用于控制API调用频率
 */
class RateLimiter {
    private interval: number;
    private lastCallTime: number;

    constructor(rpm: number) {
        this.interval = 60 / rpm;
        this.lastCallTime = 0;
    }

    async wait(): Promise<void> {
        const currentTime = Date.now() / 1000;
        const elapsed = currentTime - this.lastCallTime;
        if (elapsed < this.interval) {
            const waitTime = this.interval - elapsed;
            await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
        }
        this.lastCallTime = Date.now() / 1000;
    }
}

/**
 * API调用接口
 */
interface ApiClient {
    proofread(content: string, reference?: string): Promise<string | null>;
}

/**
 * Deepseek API客户端
 */
export class DeepseekClient implements ApiClient {
    private apiKey: string;
    private baseUrl: string;

    constructor(model: 'deepseek-chat' | 'deepseek-v3') {
        const config = vscode.workspace.getConfiguration('ai-proofread');
        if (model === 'deepseek-chat') {
            this.apiKey = config.get<string>('apiKeys.deepseekChat', '');
            this.baseUrl = 'https://api.deepseek.com/v1';
        } else {
            this.apiKey = config.get<string>('apiKeys.deepseekV3', '');
            this.baseUrl = 'https://dashscope.aliyuncs.com/api/v1';
        }

        if (!this.apiKey) {
            throw new Error(`未配置${model === 'deepseek-chat' ? 'Deepseek Chat' : '阿里云 Deepseek V3'} API密钥，请在设置中配置`);
        }
    }

    async proofread(content: string, reference: string = ''): Promise<string | null> {
        const messages = [
            { role: 'system', content: DEFAULT_SYSTEM_PROMPT }
        ];

        if (reference) {
            messages.push(
                { role: 'assistant', content: '' },
                { role: 'user', content: reference }
            );
        }

        messages.push(
            { role: 'assistant', content: '' },
            { role: 'user', content: content }
        );

        try {
            const response = await axios.post(
                `${this.baseUrl}/chat/completions`,
                {
                    model: this.baseUrl.includes('aliyuncs.com') ? 'deepseek-v3' : 'deepseek-chat',
                    messages,
                    temperature: 1,
                },
                {
                    headers: {
                        'Authorization': `Bearer ${this.apiKey}`,
                        'Content-Type': 'application/json',
                    }
                }
            );

            let result = response.data.choices[0].message.content;
            result = result.replace('\n</target>', '').replace('<target>\n', '');
            return result;
        } catch (error) {
            console.error('API调用出错:', error);
            return null;
        }
    }
}

/**
 * Google API客户端
 */
export class GoogleClient implements ApiClient {
    private apiKey: string;

    constructor() {
        const config = vscode.workspace.getConfiguration('ai-proofread');
        this.apiKey = config.get<string>('apiKeys.google', '');

        if (!this.apiKey) {
            throw new Error('未配置Google API密钥，请在设置中配置');
        }
    }

    async proofread(content: string, reference: string = ''): Promise<string | null> {
        try {
            const response = await axios.post(
                'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent',
                {
                    contents: [
                        {
                            parts: [{ text: content }]
                        }
                    ],
                    generationConfig: {
                        temperature: 1,
                    },
                    safetySettings: [
                        {
                            category: 'HARM_CATEGORY_HARASSMENT',
                            threshold: 'BLOCK_NONE'
                        },
                        {
                            category: 'HARM_CATEGORY_HATE_SPEECH',
                            threshold: 'BLOCK_NONE'
                        },
                        {
                            category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                            threshold: 'BLOCK_NONE'
                        },
                        {
                            category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
                            threshold: 'BLOCK_NONE'
                        }
                    ]
                },
                {
                    headers: {
                        'Content-Type': 'application/json',
                        'x-goog-api-key': this.apiKey,
                    }
                }
            );

            return response.data.candidates[0].content.parts[0].text;
        } catch (error) {
            console.error('API调用出错:', error);
            return null;
        }
    }
}

/**
 * 处理进度统计
 */
interface ProcessStats {
    totalCount: number;
    processedCount: number;
    totalLength: number;
    processedLength: number;
    unprocessedParagraphs: Array<{
        index: number;
        preview: string;
    }>;
}

/**
 * 异步处理段落
 */
export async function processJsonFileAsync(
    jsonInPath: string,
    jsonOutPath: string,
    options: {
        startCount?: number | number[];
        stopCount?: number;
        model?: 'deepseek-chat' | 'deepseek-v3' | 'google';
        rpm?: number;
        maxConcurrent?: number;
        onProgress?: (info: string) => void;
    } = {}
): Promise<ProcessStats> {
    // 设置默认值
    const {
        startCount = 1,
        stopCount,
        model = 'deepseek-chat',
        rpm = 15,
        maxConcurrent = 3,
        onProgress
    } = options;

    // 读取输入JSON文件
    const inputParagraphs = JSON.parse(fs.readFileSync(jsonInPath, 'utf8'));
    const totalCount = inputParagraphs.length;

    // 初始化或读取输出JSON文件
    let outputParagraphs: (string | null)[] = [];
    if (fs.existsSync(jsonOutPath)) {
        outputParagraphs = JSON.parse(fs.readFileSync(jsonOutPath, 'utf8'));
        if (outputParagraphs.length !== totalCount) {
            throw new Error(`输出JSON的长度与输入JSON的长度不同: ${outputParagraphs.length} != ${totalCount}`);
        }
    } else {
        outputParagraphs = new Array(totalCount).fill(null);
        fs.writeFileSync(jsonOutPath, JSON.stringify(outputParagraphs, null, 2), 'utf8');
    }

    // 确定要处理的段落索引
    const indicesToProcess: number[] = [];
    if (typeof startCount === 'number') {
        const startIndex = startCount - 1;
        const stopIndex = stopCount ? stopCount - 1 : totalCount - 1;
        for (let i = startIndex; i <= stopIndex; i++) {
            if (i < totalCount && outputParagraphs[i] === null) {
                indicesToProcess.push(i);
            }
        }
    } else {
        for (const idx of startCount) {
            const i = idx - 1;
            if (0 <= i && i < totalCount && outputParagraphs[i] === null) {
                indicesToProcess.push(i);
            }
        }
    }

    // 创建API客户端
    const client: ApiClient = model === 'google' ? new GoogleClient() : new DeepseekClient(model);

    // 创建限速器
    const rateLimiter = new RateLimiter(rpm);

    // 创建并发控制
    const semaphore = new Array(maxConcurrent).fill(null);

    // 处理段落
    const processOne = async (index: number): Promise<void> => {
        const paragraph = inputParagraphs[index];
        const targetText = paragraph.target;
        const referenceText = paragraph.reference || '';
        const contextText = paragraph.context || '';

        const haseContext = contextText && contextText.trim() !== targetText.trim();
        const progressInfo = `处理 No. ${index + 1}/${totalCount}, Len ${targetText.length}` +
            `${haseContext ? ` with context ${contextText.length}` : ''}`+
            `${referenceText ? ` with reference ${referenceText.length}` : ''}:`+
            `\n${targetText.slice(0, 30)} ...\n`+
            `${'-'.repeat(40)}\n`;
        console.log(progressInfo);
        if (onProgress) {
            onProgress(progressInfo);
        }

        // 构建提示文本
        let preText = referenceText ? `<reference>\n${referenceText}\n</reference>` : '';
        if (haseContext) {
            preText += `\n<context>\n${contextText}\n</context>`;
        }
        const postText = `<target>\n${targetText}\n</target>`;

        const startTime = Date.now();
        await rateLimiter.wait();

        const processedText = await client.proofread(postText, preText);
        const elapsed = (Date.now() - startTime) / 1000;

        if (processedText) {
            outputParagraphs[index] = processedText;
            fs.writeFileSync(jsonOutPath, JSON.stringify(outputParagraphs, null, 2), 'utf8');
            const completeInfo = `完成 ${index + 1}/${totalCount} 长度 ${targetText.length} 用时 ${elapsed.toFixed(2)}s\n${'-'.repeat(40)}\n`;
            console.log(completeInfo);
            if (onProgress) {
                onProgress(completeInfo);
            }
        } else {
            const errorInfo = `段落 ${index + 1}/${totalCount}: 处理失败，跳过\n${'-'.repeat(40)}\n`;
            console.log(errorInfo);
            if (onProgress) {
                onProgress(errorInfo);
            }
        }
    };

    // 并发处理所有段落
    await Promise.all(
        indicesToProcess.map(async (index) => {
            const slot = await Promise.race(
                semaphore.map((_, i) =>
                    Promise.resolve(i)
                )
            );
            semaphore[slot] = processOne(index).finally(() => {
                semaphore[slot] = null;
            });
            await semaphore[slot];
        })
    );

    // 生成处理统计
    const processedCount = outputParagraphs.filter(p => p !== null).length;
    const totalLength = inputParagraphs.reduce((sum: number, p: any) => sum + p.target.length, 0);
    const processedLength = outputParagraphs.reduce((sum: number, p: string | null) => sum + (p ? p.length : 0), 0);
    const unprocessedParagraphs = inputParagraphs
        .map((p: any, i: number) => ({
            index: i + 1,
            preview: p.target.trim().split('\n')[0].slice(0, 20)
        }))
        .filter((_: any, i: number) => outputParagraphs[i] === null);

    // 生成Markdown文件
    const mdFilePath = `${jsonOutPath}.md`;
    const processedParagraphs = outputParagraphs.filter(p => p !== null);
    fs.writeFileSync(mdFilePath, processedParagraphs.join('\n\n'), 'utf8');

    return {
        totalCount,
        processedCount,
        totalLength,
        processedLength,
        unprocessedParagraphs
    };
}