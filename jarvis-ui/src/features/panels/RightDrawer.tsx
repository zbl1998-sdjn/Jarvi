import type { ActionProposal, ActionRecord } from '../../app/api/assistant-client';

const DEFAULT_REASON = '需要确认后才会执行。';

interface RightDrawerProps {
  pendingConfirmations: ActionProposal[];
  recentActions: ActionRecord[];
  onApproveAction: (proposal: ActionProposal) => void;
}

export function RightDrawer({
  pendingConfirmations,
  recentActions,
  onApproveAction,
}: RightDrawerProps) {
  return (
    <aside className="drawer">
      <section className="drawer-section">
        <h2>确认队列</h2>
        {pendingConfirmations.length === 0 ? (
          <p>当前没有待确认动作。</p>
        ) : (
          pendingConfirmations.map((proposal) => (
            <article className="action-card" key={`${proposal.action_type}-${proposal.target}`}>
              <strong>{proposal.action_type}</strong>
              <p>风险等级：{proposal.risk_level}</p>
              <p>目标路径：{proposal.target}</p>
              <p>{proposal.reason || DEFAULT_REASON}</p>
              <button type="button" onClick={() => onApproveAction(proposal)}>
                批准执行
              </button>
            </article>
          ))
        )}
      </section>
      <section className="drawer-section">
        <h2>最近动作</h2>
        {recentActions.length === 0 ? (
          <p>还没有动作记录。</p>
        ) : (
          recentActions.map((action) => (
            <article className="action-card" key={action.id}>
              <strong>{action.action_type}</strong>
              <p>状态：{action.status}</p>
              <p>风险：{action.risk_level}</p>
              <p>目标：{action.target}</p>
              <p>{action.detail}</p>
            </article>
          ))
        )}
      </section>
    </aside>
  );
}
