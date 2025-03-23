"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getSystemPrompt = exports.parseProofreaderPrompt = void 0;
const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const fast_xml_parser_1 = require("fast-xml-parser");
/**
 * 从XML文件中解析提示词配置
 */
function parseProofreaderPrompt(xmlContent) {
    const parser = new fast_xml_parser_1.XMLParser({
        ignoreAttributes: false,
        parseTagValue: true,
        trimValues: true
    });
    const result = parser.parse(xmlContent);
    const setting = result['proofreader-system-setting'];
    return {
        role: setting['role-setting'],
        task: setting['task'],
        outputFormat: setting['output-format']
    };
}
exports.parseProofreaderPrompt = parseProofreaderPrompt;
/**
 * 获取完整的系统提示词
 */
function getSystemPrompt() {
    // 首先尝试从扩展资源目录读取
    const extensionPath = vscode.extensions.getExtension('ai-proofread')?.extensionPath;
    if (extensionPath) {
        const promptPath = path.join(extensionPath, 'resources', 'prompt-proofreader-system.xml');
        if (fs.existsSync(promptPath)) {
            const xmlContent = fs.readFileSync(promptPath, 'utf8');
            const prompt = parseProofreaderPrompt(xmlContent);
            return `${prompt.role}\n\n${prompt.task}\n\n${prompt.outputFormat}`;
        }
    }
    // 如果扩展资源目录中没有，则使用内置的默认提示词
    return `你是一位精通中文的校对专家、语言文字专家，像杜永道等专家那样，能准确地发现文章的语言文字问题。

你的语感也非常好，通过朗读就能感受到句子是否自然，是否潜藏问题。

你知识渊博，能发现文中的事实错误。

你工作细致、严谨，当你发现潜在的问题时，你会通过维基百科、《现代汉语词典》《辞海》等各种权威工具书来核对；如果涉及古代汉语和古代文化，你会专门查阅中华书局、上海古籍出版社等权威出版社出版的古籍，以及《王力古汉语字典》《汉语大词典》《辞源》《辞海》等工具书。

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

输出要求：

1. 用户提供的文本的格式可能是markdown、纯文本、TEX、ConTeXt，请保持文本原有的格式和标记；
2. 原文的空行、换行、分段等格式保持不变；
3. 不回答原文中的任何提问；
4. 不给出任何说明或解释；`;
}
exports.getSystemPrompt = getSystemPrompt;
//# sourceMappingURL=prompts.js.map