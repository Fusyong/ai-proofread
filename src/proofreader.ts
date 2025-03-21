import * as vscode from 'vscode';
import { spawn } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';

const exec = promisify(require('child_process').exec);

export async function proofreadDocument(text: string, referenceText: string, useReference: boolean): Promise<string> {
    // 创建临时文件
    const tempDir = path.join(os.tmpdir(), 'ai-proofread');
    await fs.mkdir(tempDir, { recursive: true });

    const targetFile = path.join(tempDir, 'target.md');
    const contextFile = path.join(tempDir, 'context.md');
    const referenceFile = path.join(tempDir, 'reference.md');
    const resultFile = path.join(tempDir, 'result.md');

    // 写入文件
    await fs.writeFile(targetFile, text, 'utf8');
    await fs.writeFile(contextFile, '', 'utf8');
    await fs.writeFile(referenceFile, referenceText, 'utf8');

    try {
        // 调用Python脚本进行校对
        const scriptPath = path.join(__dirname, '..', 'src', 'proofreader.py');
        const command = `python "${scriptPath}" "${targetFile}" "${contextFile}" "${referenceFile}" "${resultFile}"`;

        const { stdout, stderr } = await exec(command);

        if (stderr) {
            throw new Error(`校对过程出错: ${stderr}`);
        }

        // 读取结果
        const result = await fs.readFile(resultFile, 'utf8');

        // 清理临时文件
        await fs.unlink(targetFile);
        await fs.unlink(contextFile);
        await fs.unlink(referenceFile);
        await fs.unlink(resultFile);

        return result;
    } catch (error) {
        // 确保清理临时文件
        try {
            await fs.unlink(targetFile);
            await fs.unlink(contextFile);
            await fs.unlink(referenceFile);
            await fs.unlink(resultFile);
        } catch (e) {
            // 忽略清理错误
        }
        throw error;
    }
}