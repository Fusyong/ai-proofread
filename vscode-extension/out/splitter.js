"use strict";
/**
 * 文本切分工具模块
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.splitText = exports.mergeShortParagraphs = exports.cutTextInListByLength = exports.splitMarkdownByTitleAndLengthWithContext = exports.splitMarkdownByTitle = exports.cutTextByLength = void 0;
/**
 * 将文本大致按长度切分（在指定长度前后最近一个空行处）
 * @param text 要切分的文本
 * @param cutBy 切分长度
 * @returns 切分后的文本列表
 */
function cutTextByLength(text, cutBy = 600) {
    // 如果长度小于50，则按50字切分
    cutBy = Math.max(50, cutBy);
    // 按行分割文本
    const lines = text.split('\n');
    // 存储切分后的文本
    const result = [];
    let currentChunk = [];
    let currentLength = 0;
    for (const line of lines) {
        currentChunk.push(line);
        currentLength += line.length;
        // 如果当前块长度超过目标长度且遇到空行，则切分
        if (currentLength >= cutBy && !line.trim()) {
            result.push(currentChunk.join('\n'));
            currentChunk = [];
            currentLength = 0;
        }
    }
    // 添加最后一个块
    if (currentChunk.length > 0) {
        result.push(currentChunk.join('\n'));
    }
    return result;
}
exports.cutTextByLength = cutTextByLength;
/**
 * 将markdown文本按标题级别切分
 * @param text markdown文本
 * @param levels 要切分的标题级别列表
 * @returns 切分后的文本列表
 */
function splitMarkdownByTitle(text, levels = [2]) {
    // 按行分割文本
    const lines = text.split('\n');
    // 存储切分后的段落
    const rawParagraphs = [];
    let currentParagraph = [];
    for (const line of lines) {
        // 检查是否为要切分的标题
        let isTitleToCut = false;
        for (const level of levels) {
            if (line.startsWith('#'.repeat(level) + ' ')) {
                isTitleToCut = true;
                break;
            }
        }
        if (isTitleToCut) {
            // 如果当前段落不为空，添加到结果中
            if (currentParagraph.length > 0) {
                rawParagraphs.push(currentParagraph.join('\n'));
                currentParagraph = [];
            }
            // 将当前标题行添加到新段落
            currentParagraph.push(line);
        }
        else {
            // 将当前行添加到当前段落
            currentParagraph.push(line);
        }
    }
    // 添加最后一个段落（如果存在）
    if (currentParagraph.length > 0) {
        rawParagraphs.push(currentParagraph.join('\n'));
    }
    return rawParagraphs;
}
exports.splitMarkdownByTitle = splitMarkdownByTitle;
/**
 * 将markdown文本按标题级别切分，然后将每个段落按长度切分，保留完整上下文
 * @param text markdown文本
 * @param levels 要切分的标题级别列表
 * @param cutBy 切分长度
 * @returns 切分后的文本列表，每个元素包含完整上下文和目标文本
 */
function splitMarkdownByTitleAndLengthWithContext(text, levels = [2], cutBy = 600) {
    // 先按标题切分
    const sections = splitMarkdownByTitle(text, levels);
    // 存储结果
    const result = [];
    // 处理每个段落
    for (const section of sections) {
        // 将段落按长度切分
        const pieces = cutTextByLength(section, cutBy);
        // 为每个片段添加完整上下文
        pieces.forEach(piece => {
            result.push({
                context: section,
                target: piece // 切分后的片段作为目标文本
            });
        });
    }
    return result;
}
exports.splitMarkdownByTitleAndLengthWithContext = splitMarkdownByTitleAndLengthWithContext;
/**
 * 将列表中的超长段落切分为多个短段落
 * @param textList 段落列表
 * @param threshold 段落最大长度，超过此长度的段落将被拆分
 * @param cutBy 拆分长段落时的目标长度
 * @returns 处理后的段落列表
 */
function cutTextInListByLength(textList, threshold = 1500, cutBy = 800) {
    const textListShort = [];
    for (const text of textList) {
        if (text.length > threshold) {
            textListShort.push(...cutTextByLength(text, cutBy));
        }
        else {
            textListShort.push(text);
        }
    }
    return textListShort;
}
exports.cutTextInListByLength = cutTextInListByLength;
/**
 * 合并短段落到后一段
 * @param paragraphs 段落列表
 * @param minLength 段落最小长度，小于此长度的段落将被合并
 * @returns 合并短段落后的段落列表
 */
function mergeShortParagraphs(paragraphs, minLength = 100) {
    const result = [];
    let tempParagraphs = [];
    for (const para of paragraphs) {
        const paraLength = para.length;
        if (paraLength < minLength) {
            // 短段落暂存
            tempParagraphs.push(para);
        }
        else {
            // 正常长度段落
            if (tempParagraphs.length > 0) {
                // 如果有暂存段落，合并后添加
                tempParagraphs.push(para);
                result.push(tempParagraphs.join('\n'));
                tempParagraphs = [];
            }
            else {
                // 直接添加
                result.push(para);
            }
        }
    }
    // 处理剩余的暂存段落
    if (tempParagraphs.length > 0) {
        result.push(tempParagraphs.join('\n'));
    }
    return result;
}
exports.mergeShortParagraphs = mergeShortParagraphs;
/**
 * 将文本切分并生成JSON和Markdown格式的输出
 * @param text 要切分的文本
 * @param options 切分选项
 * @returns 包含JSON和Markdown格式输出的对象
 */
function splitText(text, options) {
    let segments;
    if (options.mode === 'length') {
        // 按长度切分
        const textList = cutTextByLength(text, options.cutBy);
        segments = textList.map(x => ({ target: x }));
    }
    else if (options.mode === 'title') {
        // 按标题切分
        const textList = splitMarkdownByTitle(text, options.levels);
        segments = textList.map(x => ({ target: x }));
    }
    else if (options.mode === 'context') {
        // 按标题和长度切分，带上下文
        segments = splitMarkdownByTitleAndLengthWithContext(text, options.levels, options.cutBy);
    }
    else {
        // 标题加长度切分：先按标题切分，然后处理长短段落
        let textList = splitMarkdownByTitle(text, options.levels);
        textList = cutTextInListByLength(textList, options.threshold, options.cutBy);
        textList = mergeShortParagraphs(textList, options.minLength);
        segments = textList.map(x => ({ target: x }));
    }
    // 生成JSON输出
    const jsonOutput = JSON.stringify(segments, null, 2);
    // 生成Markdown输出（用---分隔）
    const markdownOutput = segments.map(x => x.target).join('\n---\n');
    return {
        jsonOutput,
        markdownOutput,
        segments
    };
}
exports.splitText = splitText;
//# sourceMappingURL=splitter.js.map