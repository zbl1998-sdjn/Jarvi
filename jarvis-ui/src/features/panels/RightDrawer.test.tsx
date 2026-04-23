import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { ActionProposal, ActionRecord } from '../../app/api/assistant-client';
import { RightDrawer } from './RightDrawer';

const noop = vi.fn();

describe('RightDrawer – 审批卡片', () => {
  it('shows the resolved target path with explicit label', () => {
    const proposal: ActionProposal = {
      action_type: 'write_file',
      target: '/workspace/output.txt',
      risk_level: 'high',
      requires_confirmation: true,
    };
    render(
      <RightDrawer
        pendingConfirmations={[proposal]}
        recentActions={[]}
        onApproveAction={noop}
      />,
    );
    expect(screen.getByText('目标路径：/workspace/output.txt')).toBeInTheDocument();
  });

  it('shows the human-readable reason when provided', () => {
    const proposal: ActionProposal = {
      action_type: 'write_file',
      target: '/workspace/output.txt',
      risk_level: 'high',
      requires_confirmation: true,
      reason: '目标路径超出工作区',
    };
    render(
      <RightDrawer
        pendingConfirmations={[proposal]}
        recentActions={[]}
        onApproveAction={noop}
      />,
    );
    expect(screen.getByText('目标路径超出工作区')).toBeInTheDocument();
  });

  it('shows default reason text when reason is absent', () => {
    const proposal: ActionProposal = {
      action_type: 'run_command',
      target: 'ls -la',
      risk_level: 'medium',
      requires_confirmation: true,
    };
    render(
      <RightDrawer
        pendingConfirmations={[proposal]}
        recentActions={[]}
        onApproveAction={noop}
      />,
    );
    expect(screen.getByText('需要确认后才会执行。')).toBeInTheDocument();
  });

  it('shows default reason text when reason is an empty string', () => {
    const proposal: ActionProposal = {
      action_type: 'run_command',
      target: 'ls -la',
      risk_level: 'medium',
      requires_confirmation: true,
      reason: '',
    };
    render(
      <RightDrawer
        pendingConfirmations={[proposal]}
        recentActions={[]}
        onApproveAction={noop}
      />,
    );
    expect(screen.getByText('需要确认后才会执行。')).toBeInTheDocument();
  });

  it('renders empty state when no pending confirmations', () => {
    render(
      <RightDrawer
        pendingConfirmations={[]}
        recentActions={[]}
        onApproveAction={noop}
      />,
    );
    expect(screen.getByText('当前没有待确认动作。')).toBeInTheDocument();
  });

  it('renders recent actions correctly', () => {
    const action: ActionRecord = {
      id: 1,
      action_type: 'read_file',
      target: '/workspace/notes.md',
      risk_level: 'low',
      status: 'completed',
      detail: '成功读取',
    };
    render(
      <RightDrawer
        pendingConfirmations={[]}
        recentActions={[action]}
        onApproveAction={noop}
      />,
    );
    expect(screen.getByText('目标：/workspace/notes.md')).toBeInTheDocument();
  });
});
