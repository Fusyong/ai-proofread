"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const splitter_1 = require("./splitter");
const proofreader_1 = require("./proofreader");
function activate(context) {
    console.log('AI Proofread extension is now active!');
    // 通用的文件切分处理函数
    async function handleFileSplit(mode, editor, document) {
        const text = document.getText();
        const config = vscode.workspace.getConfiguration('ai-proofread');
        try {
            let options = { mode };
            if (mode === 'length') {
                // 获取配置中的默认切分长度
                const defaultLength = config.get('defaultSplitLength', 600);
                // 让用户选择切分长度
                const inputLength = await vscode.window.showInputBox({
                    prompt: '请输入切分长度（字符数）',
                    value: defaultLength.toString(),
                    validateInput: (value) => {
                        const num = parseInt(value);
                        if (isNaN(num)) {
                            return '请输入有效的数字';
                        }
                        if (num < 50) {
                            return '切分长度不能小于50字符';
                        }
                        return null;
                    }
                });
                if (!inputLength) {
                    return;
                }
                options.cutBy = parseInt(inputLength);
            }
            else if (mode === 'title' || mode === 'title-length' || mode === 'context') {
                // 获取配置中的默认标题级别
                const defaultLevels = config.get('defaultTitleLevels', [2]);
                // 让用户选择标题级别
                const inputLevels = await vscode.window.showInputBox({
                    prompt: '请输入标题级别（用逗号分隔，如：1,2）',
                    value: defaultLevels.join(','),
                    validateInput: (value) => {
                        const levels = value.split(',').map(x => parseInt(x.trim()));
                        if (levels.some(isNaN)) {
                            return '请输入有效的数字，用逗号分隔';
                        }
                        if (levels.some(x => x < 1 || x > 6)) {
                            return '标题级别必须在1到6之间';
                        }
                        return null;
                    }
                });
                if (!inputLevels) {
                    return;
                }
                options.levels = inputLevels.split(',').map(x => parseInt(x.trim()));
                if (mode === 'context') {
                    // 获取带上下文切分的配置
                    const defaultCutBy = config.get('contextSplit.cutBy', 600);
                    // 让用户选择切分长度
                    const inputCutBy = await vscode.window.showInputBox({
                        prompt: '请输入切分长度（字符数）',
                        value: defaultCutBy.toString(),
                        validateInput: (value) => {
                            const num = parseInt(value);
                            if (isNaN(num)) {
                                return '请输入有效的数字';
                            }
                            if (num < 50) {
                                return '切分长度不能小于50字符';
                            }
                            return null;
                        }
                    });
                    if (!inputCutBy) {
                        return;
                    }
                    options.cutBy = parseInt(inputCutBy);
                }
                else if (mode === 'title-length') {
                    // 获取标题加长度切分的配置
                    options.threshold = config.get('titleAndLengthSplit.threshold', 1500);
                    options.cutBy = config.get('titleAndLengthSplit.cutBy', 800);
                    options.minLength = config.get('titleAndLengthSplit.minLength', 120);
                    // 让用户确认或修改参数
                    const message = `将使用以下参数进行标题加长度切分：\n\n` +
                        `- 标题级别: ${options.levels.join(',')}\n` +
                        `- 长度阈值: ${options.threshold} 字符\n` +
                        `- 切分长度: ${options.cutBy} 字符\n` +
                        `- 最小长度: ${options.minLength} 字符\n\n` +
                        `是否继续？`;
                    const confirm = await vscode.window.showInformationMessage(message, { modal: true }, '继续', '修改参数');
                    if (!confirm) {
                        return;
                    }
                    if (confirm === '修改参数') {
                        // 让用户修改阈值
                        const inputThreshold = await vscode.window.showInputBox({
                            prompt: '请输入长度阈值（超过此长度的段落将被切分）',
                            value: options.threshold.toString(),
                            validateInput: (value) => {
                                const num = parseInt(value);
                                return isNaN(num) ? '请输入有效的数字' : null;
                            }
                        });
                        if (!inputThreshold)
                            return;
                        options.threshold = parseInt(inputThreshold);
                        // 让用户修改切分长度
                        const inputCutBy = await vscode.window.showInputBox({
                            prompt: '请输入切分长度（切分长段落时的目标长度）',
                            value: options.cutBy.toString(),
                            validateInput: (value) => {
                                const num = parseInt(value);
                                return isNaN(num) ? '请输入有效的数字' : null;
                            }
                        });
                        if (!inputCutBy)
                            return;
                        options.cutBy = parseInt(inputCutBy);
                        // 让用户修改最小长度
                        const inputMinLength = await vscode.window.showInputBox({
                            prompt: '请输入最小长度（小于此长度的段落将被合并）',
                            value: options.minLength.toString(),
                            validateInput: (value) => {
                                const num = parseInt(value);
                                return isNaN(num) ? '请输入有效的数字' : null;
                            }
                        });
                        if (!inputMinLength)
                            return;
                        options.minLength = parseInt(inputMinLength);
                    }
                }
            }
            // 获取当前文件所在目录
            const currentFileDir = path.dirname(document.uri.fsPath);
            const baseFileName = path.basename(document.uri.fsPath, path.extname(document.uri.fsPath));
            // 生成输出文件路径
            const jsonFilePath = path.join(currentFileDir, `${baseFileName}.json`);
            const markdownFilePath = path.join(currentFileDir, `${baseFileName}.json.md`);
            const logFilePath = path.join(currentFileDir, `${baseFileName}.log`);
            // 执行文本切分
            const { jsonOutput, markdownOutput, segments } = (0, splitter_1.splitText)(text, options);
            // 写入JSON文件
            fs.writeFileSync(jsonFilePath, jsonOutput, 'utf8');
            // 写入Markdown文件
            fs.writeFileSync(markdownFilePath, markdownOutput, 'utf8');
            // 显示结果统计
            let statsMessage = '';
            if (mode === 'length') {
                statsMessage = `切分长度: ${options.cutBy}\n\n`;
            }
            else if (mode === 'title') {
                statsMessage = `切分标题级别: ${options.levels.join(',')}\n\n`;
            }
            else if (mode === 'context') {
                statsMessage = `切分模式: 带上下文切分\n` +
                    `标题级别: ${options.levels.join(',')}\n` +
                    `切分长度: ${options.cutBy}\n\n`;
            }
            else {
                statsMessage = `切分模式: 标题加长度切分\n` +
                    `标题级别: ${options.levels.join(',')}\n` +
                    `长度阈值: ${options.threshold}\n` +
                    `切分长度: ${options.cutBy}\n` +
                    `最小长度: ${options.minLength}\n\n`;
            }
            statsMessage += `片段号\t字符数\t上下文长度\t起始文字\n${'-'.repeat(50)}\n`;
            let totalTargetLength = 0;
            let totalContextLength = 0;
            segments.forEach((segment, index) => {
                const targetLength = segment.target.trim().length;
                const contextLength = segment.context ? segment.context.trim().length : 0;
                const firstLine = segment.target.trim().split('\n')[0].slice(0, 15);
                statsMessage += `No.${index + 1}\t${targetLength}\t${contextLength}\t${firstLine}\n`;
                totalTargetLength += targetLength;
                totalContextLength += contextLength;
            });
            if (mode === 'context') {
                statsMessage += `\n合计\t${totalTargetLength}\t${totalContextLength}\t总计${totalTargetLength + totalContextLength}`;
            }
            else {
                statsMessage += `\n合计\t${totalTargetLength}`;
            }
            // 显示成功消息
            vscode.window.showInformationMessage(`文件已成功切分！\nJSON文件：${jsonFilePath}\nMarkdown文件：${markdownFilePath}`);
            // 写入统计信息
            const timestamp = new Date().toLocaleString();
            statsMessage = `\n[${timestamp}]\n${statsMessage}\n${'='.repeat(50)}\n`;
            fs.appendFileSync(logFilePath, statsMessage, 'utf8');
        }
        catch (error) {
            vscode.window.showErrorMessage(`切分文件时出错：${error instanceof Error ? error.message : String(error)}`);
        }
    }
    // 注册所有命令
    const commands = [
        vscode.commands.registerCommand('ai-proofread.splitFileByLength', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showInformationMessage('No active editor!');
                return;
            }
            await handleFileSplit('length', editor, editor.document);
        }),
        vscode.commands.registerCommand('ai-proofread.splitFileByTitle', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showInformationMessage('No active editor!');
                return;
            }
            await handleFileSplit('title', editor, editor.document);
        }),
        vscode.commands.registerCommand('ai-proofread.splitFileWithContext', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showInformationMessage('No active editor!');
                return;
            }
            await handleFileSplit('context', editor, editor.document);
        }),
        vscode.commands.registerCommand('ai-proofread.splitFileByTitleAndLength', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showInformationMessage('No active editor!');
                return;
            }
            await handleFileSplit('title-length', editor, editor.document);
        }),
        vscode.commands.registerCommand('ai-proofread.proofreadFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showInformationMessage('No active editor!');
                return;
            }
            const document = editor.document;
            // 检查文件是否为JSON
            if (document.languageId !== 'json') {
                vscode.window.showErrorMessage('请选择JSON文件进行校对！');
                return;
            }
            try {
                // 解析JSON文件以验证格式
                const content = document.getText();
                const jsonContent = JSON.parse(content);
                // 验证JSON格式是否符合要求
                if (!Array.isArray(jsonContent) || !jsonContent.every(item => typeof item === 'object' && item !== null && 'target' in item)) {
                    vscode.window.showErrorMessage('JSON文件格式不正确！需要包含target字段的对象数组。');
                    return;
                }
                // 获取当前文件路径
                const currentFilePath = document.uri.fsPath;
                const outputFilePath = currentFilePath.replace('.json', '.proofread.json');
                const logFilePath = currentFilePath.replace('.json', '.proofread.log');
                // 获取配置
                const config = vscode.workspace.getConfiguration('ai-proofread');
                const selectedModel = config.get('proofread.model', 'deepseek-chat');
                const rpm = config.get('proofread.rpm', 15);
                const maxConcurrent = config.get('proofread.maxConcurrent', 3);
                // 写入开始日志
                const startTime = new Date().toLocaleString();
                let logMessage = `\n${'='.repeat(50)}\n`;
                logMessage += `校对开始时间: ${startTime}\n`;
                logMessage += `使用模型: ${selectedModel}\n`;
                logMessage += `每分钟请求数: ${rpm}\n`;
                logMessage += `最大并发数: ${maxConcurrent}\n`;
                logMessage += `${'='.repeat(50)}\n\n`;
                fs.appendFileSync(logFilePath, logMessage, 'utf8');
                // 检查API密钥是否已配置
                let apiKey = '';
                switch (selectedModel) {
                    case 'deepseek-chat':
                        apiKey = config.get('apiKeys.deepseekChat', '');
                        break;
                    case 'deepseek-v3':
                        apiKey = config.get('apiKeys.deepseekV3', '');
                        break;
                    case 'google':
                        apiKey = config.get('apiKeys.google', '');
                        break;
                }
                if (!apiKey) {
                    const result = await vscode.window.showErrorMessage(`未配置${selectedModel}的API密钥，是否现在配置？`, '是', '否');
                    if (result === '是') {
                        await vscode.commands.executeCommand('workbench.action.openSettings', 'ai-proofread.apiKeys');
                    }
                    return;
                }
                // 显示进度
                await vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: "正在校对文件...",
                    cancellable: false
                }, async (progress) => {
                    try {
                        const stats = await (0, proofreader_1.processJsonFileAsync)(currentFilePath, outputFilePath, {
                            model: selectedModel,
                            rpm,
                            maxConcurrent,
                            onProgress: (info) => {
                                // 将进度信息写入日志
                                fs.appendFileSync(logFilePath, info + '\n', 'utf8');
                                progress.report({ message: info });
                            }
                        });
                        // 写入完成日志
                        const endTime = new Date().toLocaleString();
                        logMessage = `\n${'='.repeat(50)}\n`;
                        logMessage += `校对结束时间: ${endTime}\n`;
                        logMessage += `总段落数: ${stats.totalCount}\n`;
                        logMessage += `已处理段落数、字数: ${stats.processedCount}/${stats.totalCount} (${(stats.processedCount / stats.totalCount * 100).toFixed(2)}%), `;
                        logMessage += `${stats.processedLength}/${stats.totalLength} (${(stats.processedLength / stats.totalLength * 100).toFixed(2)}%)\n`;
                        logMessage += `未处理段落数: ${stats.totalCount - stats.processedCount}/${stats.totalCount}\n`;
                        // 记录未处理的段落
                        if (stats.unprocessedParagraphs.length > 0) {
                            logMessage += '\n未处理的段落:\n';
                            stats.unprocessedParagraphs.forEach(p => {
                                logMessage += `No.${p.index} \n ${p.preview}...\n\n`;
                            });
                        }
                        logMessage += `${'='.repeat(50)}\n\n`;
                        fs.appendFileSync(logFilePath, logMessage, 'utf8');
                        // 显示处理结果
                        const message = `校对完成！\n` +
                            `总段落数: ${stats.totalCount}\n` +
                            `已处理段落数: ${stats.processedCount} (${(stats.processedCount / stats.totalCount * 100).toFixed(2)}%)\n` +
                            `已处理字数: ${stats.processedLength} (${(stats.processedLength / stats.totalLength * 100).toFixed(2)}%)\n` +
                            `未处理段落数: ${stats.totalCount - stats.processedCount}`;
                        const result = await vscode.window.showInformationMessage(message, '查看结果', '查看未处理段落');
                        if (result === '查看结果') {
                            // 打开校对后的文件
                            const outputUri = vscode.Uri.file(outputFilePath);
                            await vscode.workspace.openTextDocument(outputUri);
                            await vscode.window.showTextDocument(outputUri);
                        }
                        else if (result === '查看未处理段落') {
                            // 显示未处理的段落
                            if (stats.unprocessedParagraphs.length > 0) {
                                const items = stats.unprocessedParagraphs.map(p => ({
                                    label: `No.${p.index}`,
                                    description: p.preview + '...'
                                }));
                                await vscode.window.showQuickPick(items, {
                                    placeHolder: '未处理的段落'
                                });
                            }
                            else {
                                vscode.window.showInformationMessage('没有未处理的段落！');
                            }
                        }
                    }
                    catch (error) {
                        if (error instanceof Error && error.message.includes('未配置')) {
                            const result = await vscode.window.showErrorMessage(error.message + '，是否现在配置？', '是', '否');
                            if (result === '是') {
                                await vscode.commands.executeCommand('workbench.action.openSettings', 'ai-proofread.apiKeys');
                            }
                        }
                        else {
                            vscode.window.showErrorMessage(`校对过程中出错：${error instanceof Error ? error.message : String(error)}`);
                        }
                    }
                });
            }
            catch (error) {
                vscode.window.showErrorMessage(`解析JSON文件时出错：${error instanceof Error ? error.message : String(error)}`);
            }
        })
    ];
    // 将所有命令添加到订阅列表
    context.subscriptions.push(...commands);
}
exports.activate = activate;
function deactivate() { }
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map