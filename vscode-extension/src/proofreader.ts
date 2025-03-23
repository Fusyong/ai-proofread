/**
 * 校对工具模块
 */

import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';
import * as dotenv from 'dotenv';

// 加载环境变量
dotenv.config();

// 读取系统提示词
const PROMPT_FILE_PATH = path.join(__dirname, 'resources/prompt-proofreader-system.xml');
const SYSTEM_PROMPT = fs.readFileSync(PROMPT_FILE_PATH, 'utf8');

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
class DeepseekClient implements ApiClient {
    private apiKey: string;
    private baseUrl: string;

    constructor(model: 'deepseek-chat' | 'deepseek-v3') {
        if (model === 'deepseek-chat') {
            this.apiKey = process.env.DEEPSEEK_API_KEY || '';
            this.baseUrl = 'https://api.deepseek.com';
        } else {
            this.apiKey = process.env.ALIYPUN_API_KEY || '';
            this.baseUrl = 'https://dashscope.aliyuncs.com/compatible-mode/v1';
        }
    }

    async proofread(content: string, reference: string = ''): Promise<string | null> {
        const messages = [
            { role: 'system', content: SYSTEM_PROMPT }
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
class GoogleClient implements ApiClient {
    private apiKey: string;

    constructor() {
        this.apiKey = process.env.GOOGLE_API_KEY || '';
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
    } = {}
): Promise<ProcessStats> {
    // 设置默认值
    const {
        startCount = 1,
        stopCount,
        model = 'deepseek-chat',
        rpm = 15,
        maxConcurrent = 3
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

        const isWithContext = contextText && contextText.trim() !== targetText.trim();
        console.log(`处理 ${index + 1}/${totalCount}${isWithContext ? ' with context' : ''}${referenceText ? ' with reference' : ''}:\n${targetText.slice(0, 30)} ...\n`);

        // 构建提示文本
        let preText = referenceText ? `<reference>\n${referenceText}\n</reference>` : '';
        if (isWithContext) {
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
            console.log(`完成 ${index + 1}/${totalCount} 长度 ${targetText.length} 用时 ${elapsed.toFixed(2)}s\n${'-'.repeat(40)}\n`);
        } else {
            console.log(`段落 ${index + 1}/${totalCount}: 处理失败，跳过\n${'-'.repeat(40)}\n`);
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