interface DiagnosticsItem {
  key: string;
  label: string;
}

interface DiagnosticsStripProps {
  items: DiagnosticsItem[];
  onReconnectVoice?: () => void;
  onReloadRuntime?: () => void;
  onResumeSession?: () => void;
}

export function DiagnosticsStrip({
  items,
  onReconnectVoice,
  onReloadRuntime,
  onResumeSession,
}: DiagnosticsStripProps) {
  if (items.length === 0) {
    return (
      <div className="diagnostics-strip diagnostics-strip--healthy">
        <span className="diagnostics-strip__ok">✓ 服务就绪</span>
      </div>
    );
  }

  return (
    <div className="diagnostics-strip diagnostics-strip--degraded">
      {items.map((item) => (
        <span className="diagnostics-strip__item" key={item.key}>
          {item.label}
        </span>
      ))}
      {onReconnectVoice && (
        <button
          className="diagnostics-strip__action"
          onClick={onReconnectVoice}
          type="button"
        >
          重连语音
        </button>
      )}
      {onReloadRuntime && (
        <button
          className="diagnostics-strip__action"
          onClick={onReloadRuntime}
          type="button"
        >
          重载运行时
        </button>
      )}
      {onResumeSession && (
        <button
          className="diagnostics-strip__action"
          onClick={onResumeSession}
          type="button"
        >
          恢复会话
        </button>
      )}
    </div>
  );
}
