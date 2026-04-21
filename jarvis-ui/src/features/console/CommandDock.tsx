import type { WorkspaceId } from '../workspace/WorkspaceRouter';

interface CommandDockProps {
  activeWorkspace: WorkspaceId;
  onSelectWorkspace: (workspace: WorkspaceId) => void;
  onSearch: () => void;
  onSummarize: () => void;
  onCreateTask: () => void;
  onOpenSearch: () => void;
}

export function CommandDock({
  activeWorkspace,
  onSelectWorkspace,
  onSearch,
  onSummarize,
  onCreateTask,
  onOpenSearch,
}: CommandDockProps) {
  return (
    <footer className="command-dock">
      <button type="button" onClick={onSearch}>搜索资料</button>
      <button type="button" onClick={onOpenSearch}>搜索/上传台</button>
      <button type="button" onClick={onSummarize}>生成总结</button>
      <button type="button" onClick={() => onSelectWorkspace('records')}>查看记录</button>
      <button type="button" onClick={() => onSelectWorkspace('tasks')}>查看任务</button>
      <button type="button" onClick={onCreateTask}>
        {activeWorkspace === 'tasks' ? '保存任务' : '快速建任务'}
      </button>
    </footer>
  );
}
