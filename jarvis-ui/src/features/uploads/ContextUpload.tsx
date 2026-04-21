import { useState } from 'react';

interface ContextUploadProps {
  onUpload: (title: string, sourceType: string, content: string) => Promise<void>;
}

export function ContextUpload({ onUpload }: ContextUploadProps) {
  const [snippetTitle, setSnippetTitle] = useState('代码片段');
  const [snippetContent, setSnippetContent] = useState('');

  async function handleFileUpload(file: File | null) {
    if (!file) {
      return;
    }

    const content = await readFileContent(file);
    const sourceType = file.type.startsWith('image/') ? 'image' : 'file';
    await onUpload(file.name, sourceType, content);
  }

  async function handleSnippetUpload() {
    if (!snippetContent.trim()) {
      return;
    }
    await onUpload(snippetTitle.trim() || '代码片段', 'code', snippetContent.trim());
    setSnippetContent('');
  }

  return (
    <section className="workspace-card workspace-card--compact">
      <h2>资料上传</h2>
      <div className="upload-grid">
        <label className="secondary-button upload-button">
          上传图片或文件
          <input
            hidden
            onChange={(event) => void handleFileUpload(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>
        <input
          className="settings-input"
          onChange={(event) => setSnippetTitle(event.target.value)}
          placeholder="片段标题"
          value={snippetTitle}
        />
        <textarea
          className="command-prompt command-prompt--compact"
          onChange={(event) => setSnippetContent(event.target.value)}
          placeholder="粘贴代码片段、网页摘录或学习笔记…"
          value={snippetContent}
        />
        <button className="secondary-button" onClick={() => void handleSnippetUpload()} type="button">
          上传片段
        </button>
      </div>
    </section>
  );
}

function readFileContent(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('读取上传文件失败'));
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
    if (file.type.startsWith('image/')) {
      reader.readAsDataURL(file);
      return;
    }
    reader.readAsText(file);
  });
}
