import * as vscode from 'vscode';
import { splitDocument } from './splitter';
import { proofreadDocument } from './proofreader';

export function activate(context: vscode.ExtensionContext) {
    // 注册切分文档命令
    let splitCommand = vscode.commands.registerCommand('ai-proofread.splitDocument', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('没有打开的文档');
            return;
        }

        // 获取当前文档内容
        const document = editor.document;
        const text = document.getText();

        // 让用户选择切分方式
        const splitMethod = await vscode.window.showQuickPick([
            { label: '方式1：保持上下文', description: '切分时保留完整上下文' },
            { label: '方式2：合并短段落', description: '合并过短的段落' }
        ], {
            placeHolder: '选择切分方式'
        });

        if (!splitMethod) {
            return;
        }

        // 让用户选择标题级别
        const level = await vscode.window.showInputBox({
            prompt: '请输入要使用的标题级别（1-6）',
            value: '1',
            validateInput: (value) => {
                const num = parseInt(value);
                if (isNaN(num) || num < 1 || num > 6) {
                    return '请输入1-6之间的数字';
                }
                return null;
            }
        });

        if (!level) {
            return;
        }

        try {
            const result = await splitDocument(text, splitMethod.label === '方式1：保持上下文', parseInt(level));

            // 创建新文档显示结果
            const doc = await vscode.workspace.openTextDocument({
                content: result,
                language: 'markdown'
            });
            await vscode.window.showTextDocument(doc);
        } catch (error) {
            vscode.window.showErrorMessage(`切分文档失败: ${error}`);
        }
    });

    // 注册校对文档命令
    let proofreadCommand = vscode.commands.registerCommand('ai-proofread.proofreadDocument', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('没有打开的文档');
            return;
        }

        // 获取当前文档内容
        const document = editor.document;
        const text = document.getText();

        // 让用户选择参考文档
        const referenceFile = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            filters: {
                'Markdown': ['md']
            }
        });

        let referenceText = '';
        if (referenceFile && referenceFile[0]) {
            try {
                referenceText = await vscode.workspace.fs.readFile(referenceFile[0]);
            } catch (error) {
                vscode.window.showErrorMessage(`读取参考文档失败: ${error}`);
                return;
            }
        }

        // 让用户选择校对方式
        const proofreadMethod = await vscode.window.showQuickPick([
            { label: '方式1：单文件校对', description: '直接校对当前文件' },
            { label: '方式2：带参考校对', description: '使用参考文档进行校对' }
        ], {
            placeHolder: '选择校对方式'
        });

        if (!proofreadMethod) {
            return;
        }

        try {
            const result = await proofreadDocument(text, referenceText, proofreadMethod.label === '方式2：带参考校对');

            // 创建新文档显示结果
            const doc = await vscode.workspace.openTextDocument({
                content: result,
                language: 'markdown'
            });
            await vscode.window.showTextDocument(doc);
        } catch (error) {
            vscode.window.showErrorMessage(`校对文档失败: ${error}`);
        }
    });

    context.subscriptions.push(splitCommand, proofreadCommand);
}

export function deactivate() {}