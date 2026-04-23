import type {
  ActionRecord,
  SearchResult,
  SummaryResult,
  TimelineEntry,
  UploadedContext,
} from '../../app/api/assistant-client';

export type WorkspaceId =
  | 'console'
  | 'search'
  | 'summary'
  | 'records'
  | 'tasks';

interface WorkspaceRouterProps {
  activeWorkspace: WorkspaceId;
  searchResults: SearchResult[];
  summaryResult: SummaryResult | null;
  recentActions: ActionRecord[];
  timeline: TimelineEntry[];
  uploadedContexts: UploadedContext[];
}

export function WorkspaceRouter({
  activeWorkspace,
  searchResults,
  summaryResult,
  recentActions,
  timeline,
  uploadedContexts,
}: WorkspaceRouterProps) {
  if (activeWorkspace === 'search') {
    return (
      <section className="workspace-card">
        <h2>搜索中心</h2>
        {searchResults.length === 0 ? (
          <p>还没有搜索结果。</p>
        ) : (
          searchResults.map((result) => (
            <article className="workspace-result" key={result.path}>
              <strong>{result.title}</strong>
              <p>{result.snippet}</p>
            </article>
            ))
          )}
          {uploadedContexts.length > 0 ? (
            <>
              <h3>最近资料上下文</h3>
              {uploadedContexts.map((item) => (
                <article className="workspace-result" key={item.id}>
                  <strong>{item.title}</strong>
                  <p>
                    {item.source_type} · {item.preview}
                  </p>
                </article>
              ))}
            </>
          ) : null}
      </section>
    );
  }

  if (activeWorkspace === 'summary') {
    return (
      <section className="workspace-card">
        <h2>总结视图</h2>
        {summaryResult ? (
          <>
            <h3>总结结论</h3>
            <p>{summaryResult.summary}</p>
            <h3>关键要点</h3>
            <ul>
              {summaryResult.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          </>
        ) : (
          <p>还没有总结结果。</p>
        )}
      </section>
    );
  }

  if (activeWorkspace === 'records') {
    return (
      <section className="workspace-card">
        <h2>执行记录</h2>
        {(recentActions.length === 0 ? timeline : recentActions).map((item) => (
          <article
            className="workspace-result"
            key={'id' in item ? `${item.id}` : `${item.type}-${item.content}`}
          >
            <strong>{'action_type' in item ? item.action_type : item.type}</strong>
            <p>{'detail' in item ? item.detail : item.content}</p>
          </article>
        ))}
      </section>
    );
  }

  if (activeWorkspace === 'tasks') {
    return (
      <section className="workspace-card">
        <h2>任务时间线</h2>
        {timeline.length === 0 ? (
          <p>还没有时间线记录。</p>
        ) : (
          timeline.map((item) => (
            <article className="workspace-result" key={`${item.type}-${item.content}`}>
              <strong>{item.type}</strong>
              <p>{item.content}</p>
            </article>
          ))
        )}
      </section>
    );
  }

  return (
    <section className="workspace-card">
      <h2>主控台</h2>
      <p>语音、搜索、总结、动作、任务与提醒都会在这里汇总。</p>
      <p>可以直接切老师风格、切音色、上传学习资料，并从上次工作台继续。</p>
    </section>
  );
}
