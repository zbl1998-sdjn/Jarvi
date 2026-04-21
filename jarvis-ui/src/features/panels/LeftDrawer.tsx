import type {
  MemoryEntry,
  PreferenceState,
  ReminderEntry,
  ResumeState,
  StageProgress,
  TaskItem,
} from '../../app/api/assistant-client';

interface LeftDrawerProps {
  tasks: TaskItem[];
  memories: MemoryEntry[];
  reminders: ReminderEntry[];
  preferences: PreferenceState;
  resume: ResumeState;
  stageProgress: StageProgress;
}

export function LeftDrawer({
  tasks,
  memories,
  reminders,
  preferences,
  resume,
  stageProgress,
}: LeftDrawerProps) {
  return (
    <aside className="drawer">
      <section className="drawer-section">
        <h2>学习进度</h2>
        <p>当前阶段：{stageProgress.current_stage}</p>
        <p>
          完成任务：{stageProgress.completed_tasks} / {stageProgress.total_tasks}
        </p>
        <p>资料上下文：{stageProgress.uploaded_contexts}</p>
      </section>
      <section className="drawer-section">
        <h2>恢复信息</h2>
        <p>最近工作台：{resume.workspace}</p>
        <p>{resume.session_id ? `最近会话：${resume.session_id}` : '还没有历史会话。'}</p>
      </section>
      <section className="drawer-section">
        <h2>偏好</h2>
        <p>{preferences.teacher_style}</p>
        <p>{preferences.voice_name}</p>
      </section>
      <section className="drawer-section">
        <h2>任务</h2>
        {tasks.length === 0 ? (
          <p>还没有任务。</p>
        ) : (
          tasks.map((task) => <p key={task.id}>{task.title} · {task.stage ?? 'M6'}</p>)
        )}
      </section>
      <section className="drawer-section">
        <h2>记忆</h2>
        {memories.length === 0 ? (
          <p>还没有记忆条目。</p>
        ) : (
          memories.map((memory) => <p key={memory.id}>{memory.content}</p>)
        )}
      </section>
      <section className="drawer-section">
        <h2>提醒</h2>
        {reminders.length === 0 ? (
          <p>还没有提醒。</p>
        ) : (
          reminders.map((reminder) => <p key={reminder.id}>{reminder.message}</p>)
        )}
      </section>
    </aside>
  );
}
