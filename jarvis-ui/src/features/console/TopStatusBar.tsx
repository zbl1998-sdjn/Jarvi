interface TopStatusBarProps {
  modeLabel?: string;
  statusItems?: string[];
}

export function TopStatusBar({
  modeLabel = '文本模式 / M6',
  statusItems = [],
}: TopStatusBarProps) {
  return (
    <header className="top-status-bar">
      <div>
        <span className="label">Jarvis</span>
        <h1>学习副驾</h1>
      </div>
      <div className="top-status-bar__status-group">
        {statusItems.map((item) => (
          <div className="status-pill" key={item}>
            {item}
          </div>
        ))}
        <div className="status-pill">{modeLabel}</div>
      </div>
    </header>
  );
}
