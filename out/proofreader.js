"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.proofreadDocument = proofreadDocument;
const util_1 = require("util");
const path = __importStar(require("path"));
const exec = (0, util_1.promisify)(require('child_process').exec);
async function proofreadDocument(text, referenceText, useReference) {
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
    }
    catch (error) {
        // 确保清理临时文件
        try {
            await fs.unlink(targetFile);
            await fs.unlink(contextFile);
            await fs.unlink(referenceFile);
            await fs.unlink(resultFile);
        }
        catch (e) {
            // 忽略清理错误
        }
        throw error;
    }
}
//# sourceMappingURL=proofreader.js.map