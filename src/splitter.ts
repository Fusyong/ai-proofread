import * as vscode from 'vscode';

interface SplitOptions {
    keepContext: boolean;
    titleLevel: number;
    cutBy?: number;
    minLength?: number;
}

export async function splitDocument(text: string, keepContext: boolean, titleLevel: number): Promise<string> {
    const options: SplitOptions = {
        keepContext,
        titleLevel,
        cutBy: keepContext ? 200 : 600,
        minLength: keepContext ? undefined : 120
    };

    // 按标题切分
    const sections = splitByTitle(text, options.titleLevel);

    // 进一步切分每个部分
    const result: string[] = [];
    for (const section of sections) {
        const subSections = keepContext
            ? splitWithContext(section, options.cutBy!)
            : splitAndMerge(section, options.cutBy!, options.minLength!);
        result.push(...subSections);
    }

    return result.join('\n\n---\n\n');
}

function splitByTitle(text: string, level: number): string[] {
    const sections: string[] = [];
    const lines = text.split('\n');
    let currentSection: string[] = [];

    for (const line of lines) {
        if (line.startsWith('#'.repeat(level) + ' ')) {
            if (currentSection.length > 0) {
                sections.push(currentSection.join('\n'));
                currentSection = [];
            }
        }
        currentSection.push(line);
    }

    if (currentSection.length > 0) {
        sections.push(currentSection.join('\n'));
    }

    return sections;
}

function splitWithContext(text: string, cutBy: number): string[] {
    const sections: string[] = [];
    const lines = text.split('\n');
    let currentSection: string[] = [];
    let context: string[] = [];

    for (const line of lines) {
        currentSection.push(line);
        if (currentSection.join('\n').length >= cutBy) {
            sections.push([...context, ...currentSection].join('\n'));
            context = [...currentSection];
            currentSection = [];
        }
    }

    if (currentSection.length > 0) {
        sections.push([...context, ...currentSection].join('\n'));
    }

    return sections;
}

function splitAndMerge(text: string, cutBy: number, minLength: number): string[] {
    const sections: string[] = [];
    const lines = text.split('\n');
    let currentSection: string[] = [];

    for (const line of lines) {
        currentSection.push(line);
        if (currentSection.join('\n').length >= cutBy) {
            if (currentSection.join('\n').length < minLength && sections.length > 0) {
                // 合并到前一个部分
                sections[sections.length - 1] = sections[sections.length - 1] + '\n' + currentSection.join('\n');
            } else {
                sections.push(currentSection.join('\n'));
            }
            currentSection = [];
        }
    }

    if (currentSection.length > 0) {
        if (currentSection.join('\n').length < minLength && sections.length > 0) {
            sections[sections.length - 1] = sections[sections.length - 1] + '\n' + currentSection.join('\n');
        } else {
            sections.push(currentSection.join('\n'));
        }
    }

    return sections;
}