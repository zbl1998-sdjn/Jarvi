import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

import { type HealthStatus } from '../../app/api/assistant-client';
import { MainConsole } from './MainConsole';

const mockState = vi.hoisted(() => ({
  hotkeyCallback: undefined as (() => void) | undefined,
  streamChat: vi.fn(
    async (
      _query: string,
      onEvent: (event: string, data: Record<string, unknown>) => void,
    ) => {
      onEvent('session', { session_id: 'abc123' });
      onEvent('text', { text: 'Jarvis M1 已收到：open console' });
      onEvent('done', { session_id: 'abc123' });
    },
  ),
  connect: vi.fn(async () => undefined),
  startMicrophoneCapture: vi.fn(async () => undefined),
  stopMicrophoneCapture: vi.fn(async () => undefined),
  sendText: vi.fn(async (_text: string) => undefined),
  interrupt: vi.fn(),
  disconnect: vi.fn(),
  interpretVoice: vi.fn(async (text: string): Promise<any> => ({
    heard_wakeword: true,
    normalized_text: text,
    workspace: null,
    clarification: null,
    action_proposal: null,
  })),
  loadHome: vi.fn(async () => ({
    tasks: [{ id: 1, title: 'Review M6 timeline', detail: '', status: 'pending' }],
    memories: [
      {
        id: 1,
        kind: 'summary',
        content: 'Remember the last summary.',
        source: 'session',
      },
    ],
    reminders: [{ id: 1, message: 'Pending task: Review M6 timeline', task_id: 1 }],
    recent_actions: [],
    timeline: [{ type: 'chat', content: 'Earlier Jarvis exchange' }],
    preferences: {
      teacher_style: '幽默风趣型',
      voice_name: 'longxiaochun',
    },
    resume: {
      workspace: 'console',
      session_id: 'resume-session',
    },
    stage_progress: {
      current_stage: 'M6',
      completed_tasks: 1,
      total_tasks: 3,
      uploaded_contexts: 1,
    },
    uploaded_contexts: [
      {
        id: 1,
        title: '阶段复盘截图',
        source_type: 'image',
        preview: 'data:image/png;base64,ZmFrZQ==',
      },
    ],
  })),
  loadHealth: vi.fn(async (): Promise<HealthStatus> => ({
    ok: true,
    service: 'jarvis-server',
    mode: 'm1',
    degraded: false,
    dependencies: { database: 'ready' },
  })),
  searchWorkspace: vi.fn(async (query: string) => [
    {
      scope: 'local',
      path: '/README.md',
      title: 'README.md',
      snippet: `Found ${query}`,
    },
  ]),
  summarizeContent: vi.fn(async () => ({
    summary: 'Jarvis summary result',
    bullets: ['source=workspace', 'lines=1'],
  })),
  createTask: vi.fn(async (title: string) => ({
    id: 2,
    title,
    detail: '来自 Jarvis 命令坞。',
    status: 'pending',
  })),
  savePreferences: vi.fn(async (teacherStyle: string, voiceName: string) => ({
    teacher_style: teacherStyle,
    voice_name: voiceName,
  })),
  loadRuntimeConfig: vi.fn(async () => ({
    database_url: 'postgresql+psycopg://postgres:postgres@127.0.0.1:5432/jarvis',
    providers: [
      {
        id: 'kimi-default',
        label: 'Kimi 默认',
        base_url: 'https://api.moonshot.ai/v1',
        api_key: 'kimi-key',
        model: 'kimi-k2.5',
        enabled: true,
      },
      {
        id: 'custom-openai',
        label: '自定义 OpenAI',
        base_url: 'https://example.com/v1',
        api_key: 'custom-key',
        model: 'gpt-4.1',
        enabled: true,
      },
    ],
    active_provider_id: 'custom-openai',
    speech: {
      api_key: 'dashscope-key',
      asr_model: 'paraformer-realtime-v2',
      tts_model: 'cosyvoice-v1',
      voice_name: 'longxiaochun',
      language: 'zh-CN',
    },
  })),
  saveRuntimeConfig: vi.fn(async (payload: unknown) => payload),
  checkRuntimeConfig: vi.fn(async () => ({
    dependencies: {
      database: 'ready',
      llm: 'configured',
      speech: 'configured',
      config: 'ready',
    },
  })),
  uploadContext: vi.fn(async (title: string, sourceType: string) => ({
    id: 2,
    title,
    source_type: sourceType,
    preview: 'uploaded preview',
  })),
  saveWorkspaceState: vi.fn(async (workspace: string, sessionId?: string) => ({
    workspace,
    session_id: sessionId ?? null,
  })),
  executeAction: vi.fn(async () => ({
    id: 9,
    action_type: 'delete_file',
    target: 'danger.txt',
    risk_level: 'dangerous',
    status: 'completed',
    detail: '动作已批准并执行。',
  })),
  realtimeHandlers: undefined as
    | {
        onEvent: (event: {
          type: string;
          state?: string;
          role?: string;
          text?: string;
          final?: boolean;
        }) => void;
        onError?: (error: Error) => void;
      }
    | undefined,
}));

vi.mock('../../app/api/chat-client', () => ({
  streamChat: mockState.streamChat,
}));

vi.mock('../../app/api/realtime-client', () => ({
  createRealtimeVoiceClient: (handlers: typeof mockState.realtimeHandlers) => {
    mockState.realtimeHandlers = handlers;
    return {
      connect: mockState.connect,
      startMicrophoneCapture: mockState.startMicrophoneCapture,
      stopMicrophoneCapture: mockState.stopMicrophoneCapture,
      sendText: mockState.sendText,
      interrupt: mockState.interrupt,
      disconnect: mockState.disconnect,
    };
  },
}));

vi.mock('../../app/api/assistant-client', () => ({
  interpretVoice: mockState.interpretVoice,
  loadHealth: mockState.loadHealth,
  loadHome: mockState.loadHome,
  loadRuntimeConfig: mockState.loadRuntimeConfig,
  savePreferences: mockState.savePreferences,
  saveRuntimeConfig: mockState.saveRuntimeConfig,
  saveWorkspaceState: mockState.saveWorkspaceState,
  checkRuntimeConfig: mockState.checkRuntimeConfig,
  searchWorkspace: mockState.searchWorkspace,
  summarizeContent: mockState.summarizeContent,
  createTask: mockState.createTask,
  uploadContext: mockState.uploadContext,
  executeAction: mockState.executeAction,
}));

window.jarvisDesktop = {
  getServerBaseUrl: () => 'http://127.0.0.1:8001',
  getShellInfo: () => ({ app: 'Jarvis', mode: 'desktop-shell', resident: true }),
  onHotkeyTriggered: (callback) => {
    mockState.hotkeyCallback = callback;
    return () => {
      mockState.hotkeyCallback = undefined;
    };
  },
};

afterEach(() => {
  vi.clearAllMocks();
  mockState.realtimeHandlers = undefined;
  mockState.hotkeyCallback = undefined;
});

// ── Test 1: send button uses streamChat ────────────────────────────────────────
it('submits text and renders the streamed answer', async () => {
  render(<MainConsole />);

  fireEvent.change(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), {
    target: { value: 'open console' },
  });
  fireEvent.click(screen.getByText('发送'));

  expect(
    await screen.findByText('Jarvis M1 已收到：open console'),
  ).toBeInTheDocument();
});

// ── Test A: send button must use streamChat and NEVER call realtimeClient.sendText ──
it('send button uses streamChat and never calls realtime sendText', async () => {
  render(<MainConsole />);

  fireEvent.change(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), {
    target: { value: 'test message' },
  });
  fireEvent.click(screen.getByText('发送'));

  await waitFor(() => {
    expect(mockState.streamChat).toHaveBeenCalled();
  });
  expect(mockState.streamChat.mock.calls[0][0]).toBe('test message');
  expect(mockState.sendText).not.toHaveBeenCalled();
});

// ── Test 2 (rewritten): voice buttons control mic capture only ─────────────────
it('voice buttons connect and control microphone capture only', async () => {
  render(<MainConsole />);

  // Connect voice
  fireEvent.click(screen.getByText('启动语音'));
  expect(await screen.findByText('语音已就绪')).toBeInTheDocument();

  // Start capture (no text in query)
  fireEvent.click(screen.getByText('开始收音'));
  await waitFor(() => {
    expect(mockState.startMicrophoneCapture).toHaveBeenCalledTimes(1);
  });

  // sendText must never be triggered by voice buttons
  expect(mockState.sendText).not.toHaveBeenCalled();

  // Voice state and audio events still update the UI
  await act(async () => {
    mockState.realtimeHandlers?.onEvent({
      type: 'voice_state',
      state: 'speaking',
    });
    mockState.realtimeHandlers?.onEvent({
      type: 'audio_chunk',
      text: 'Jarvis 语音回复',
      final: true,
    });
  });

  expect(await screen.findByText('播报中')).toBeInTheDocument();
  expect(await screen.findByText('Jarvis 语音回复')).toBeInTheDocument();

  // Stop capture
  fireEvent.click(screen.getByText('结束收音'));
  await waitFor(() => {
    expect(mockState.stopMicrophoneCapture).toHaveBeenCalledTimes(1);
  });

  // No workspace routing triggered by voice buttons
  expect(mockState.searchWorkspace).not.toHaveBeenCalled();
  expect(mockState.interpretVoice).not.toHaveBeenCalled();
});

// ── Test 3: home snapshot, hotkey wake ────────────────────────────────────────
it('loads reminders and tasks from home and reacts to hotkey wake', async () => {
  render(<MainConsole />);

  expect(await screen.findByText('后台常驻已开启')).toBeInTheDocument();
  expect((await screen.findAllByText(/Review M6 timeline/)).length).toBeGreaterThan(0);
  expect(await screen.findByText('Pending task: Review M6 timeline')).toBeInTheDocument();
  expect(await screen.findByText(/当前阶段：\s*M6/)).toBeInTheDocument();
  expect(await screen.findByText(/最近会话：resume-session/)).toBeInTheDocument();

  await act(async () => {
    mockState.hotkeyCallback?.();
  });

  expect(
    await screen.findByText('已收到热键唤醒，请继续下达指令。'),
  ).toBeInTheDocument();
  expect(await screen.findByText('语音模式 / 聆听中')).toBeInTheDocument();
});

// ── Test B: degraded health renders diagnostics strip ─────────────────────────
it('degraded health renders diagnostics strip with actionable status', async () => {
  mockState.loadHealth.mockResolvedValueOnce({
    ok: false,
    service: 'jarvis-server',
    mode: 'm1',
    degraded: true,
    dependencies: { database: 'offline', llm: 'missing', speech: 'missing' },
  });

  render(<MainConsole />);

  expect(await screen.findByText('数据库未连接')).toBeInTheDocument();
  expect(await screen.findByText('模型未配置')).toBeInTheDocument();
  expect(await screen.findByText('语音未配置')).toBeInTheDocument();
});

// ── Test 4 (rewritten): action proposals queued via send button ───────────────
it('queues dangerous action confirmations via send button and executes when approved', async () => {
  mockState.interpretVoice.mockResolvedValueOnce({
    heard_wakeword: true,
    normalized_text: 'Jarvis delete danger.txt',
    workspace: null,
    clarification: null,
    action_proposal: {
      action_type: 'delete_file',
      target: 'danger.txt',
      risk_level: 'dangerous',
      requires_confirmation: true,
    },
  });

  render(<MainConsole />);

  fireEvent.change(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), {
    target: { value: 'Jarvis delete danger.txt' },
  });
  fireEvent.click(screen.getByText('发送'));
  fireEvent.click(await screen.findByText('批准执行'));

  expect(mockState.executeAction).toHaveBeenCalledWith(
    'delete_file',
    'danger.txt',
    undefined,
    true,
  );
  expect(
    await screen.findByText('动作已批准并执行。'),
  ).toBeInTheDocument();
});

// ── Test 5: preferences and snippet upload ────────────────────────────────────
it('saves style preferences and uploads snippet context', async () => {
  render(<MainConsole />);

  const allSelects = await screen.findAllByRole('combobox');
  const teacherSelect = allSelects.find((el) =>
    Array.from((el as HTMLSelectElement).options).some((o) => o.value === '面试高压陪练型'),
  ) as HTMLSelectElement;
  const voiceSelect = allSelects.find((el) =>
    Array.from((el as HTMLSelectElement).options).some((o) => o.value === 'longxiaobai'),
  ) as HTMLSelectElement;
  expect(teacherSelect).toBeTruthy();
  expect(voiceSelect).toBeTruthy();
  await act(async () => {
    teacherSelect.value = '面试高压陪练型';
    fireEvent.change(teacherSelect);
    voiceSelect.value = 'longxiaobai';
    fireEvent.change(voiceSelect);
  });
  fireEvent.click(screen.getByText('保存风格'));

  await waitFor(() => {
    expect(mockState.savePreferences).toHaveBeenCalled();
  });

  fireEvent.change(screen.getByPlaceholderText('片段标题'), {
    target: { value: '新的代码片段' },
  });
  fireEvent.change(screen.getByPlaceholderText('粘贴代码片段、网页摘录或学习笔记…'), {
    target: { value: 'console.log("jarvis");' },
  });
  fireEvent.click(screen.getByText('上传片段'));

  await waitFor(() => {
    expect(mockState.uploadContext).toHaveBeenCalledWith(
      '新的代码片段',
      'code',
      'console.log("jarvis");',
    );
  });
});

// ── Test WorkspaceRouter: structured summary display ────────────────────────
it('summary workspace renders 总结结论 section and 关键要点 list', async () => {
  render(<MainConsole />);

  // Trigger summarize via the CommandDock button
  fireEvent.click(await screen.findByText('生成总结'));

  await waitFor(() => {
    expect(mockState.summarizeContent).toHaveBeenCalled();
  });

  // Structured headings must be present
  expect(await screen.findByText('总结结论')).toBeInTheDocument();
  expect(await screen.findByText('关键要点')).toBeInTheDocument();

  // Actual summary content and bullets must be rendered
  expect(await screen.findByText('Jarvis summary result')).toBeInTheDocument();
  expect(await screen.findByText('source=workspace')).toBeInTheDocument();
});

// ── Test 6: config panel ──────────────────────────────────────────────────────
it('renders configuration center with provider controls and action buttons', async () => {
  render(<MainConsole />);

  expect(await screen.findByText('服务与模型配置')).toBeInTheDocument();
  expect(await screen.findByText('模型 Provider')).toBeInTheDocument();
  expect(await screen.findByText('新增 Provider')).toBeInTheDocument();
  expect(await screen.findByText('检测数据库')).toBeInTheDocument();
  expect((await screen.findAllByText('检测模型连接')).length).toBeGreaterThan(0);
  expect(await screen.findByText('检测语音配置')).toBeInTheDocument();
  expect(await screen.findByText('重新加载配置')).toBeInTheDocument();
  expect(await screen.findByText('恢复上次会话')).toBeInTheDocument();
  expect(await screen.findByText('刷新首页状态')).toBeInTheDocument();
});

// ── Test 7: drawers ───────────────────────────────────────────────────────────
it('collapses side drawers by default and opens the left overlay on handle click', async () => {
  render(<MainConsole />);

  await screen.findByLabelText('展开左侧学习面板');
  expect(document.querySelector('.console-layout--collapsed')).toBeTruthy();
  expect(document.querySelector('.overlay-drawer--open')).toBeNull();

  fireEvent.click(screen.getByLabelText('展开左侧学习面板'));

  expect(document.querySelector('.overlay-drawer--left.overlay-drawer--open')).toBeTruthy();
});

// ── Issue 1: clarification must append to streamed reply, not overwrite it ────
it('text send with clarification appends to streamed reply instead of overwriting', async () => {
  mockState.streamChat.mockImplementationOnce(
    async (
      _query: string,
      onEvent: (event: string, data: Record<string, unknown>) => void,
    ) => {
      onEvent('session', { session_id: 'abc123' });
      onEvent('text', { text: 'Jarvis 正在分析您的问题…' });
      onEvent('done', { session_id: 'abc123' });
    },
  );
  mockState.interpretVoice.mockResolvedValueOnce({
    heard_wakeword: false,
    normalized_text: 'tell me',
    workspace: null,
    clarification: '请问您具体指的是哪个项目？',
    action_proposal: null,
  });

  render(<MainConsole />);

  fireEvent.change(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), {
    target: { value: 'tell me' },
  });
  fireEvent.click(screen.getByText('发送'));

  await waitFor(() => {
    const replyCard = document.querySelector('.reply-card');
    // Streamed text from this test's chat response must still be present
    expect(replyCard?.textContent).toContain('Jarvis 正在分析您的问题…');
    // Clarification must also be present (appended, not replacing)
    expect(replyCard?.textContent).toContain('请问您具体指的是哪个项目？');
  });
});

// ── Push-to-talk error: start failure surfaces error and does not enter capturing state ──
it('push to talk start error surfaces error message and does not enter capturing state', async () => {
  mockState.startMicrophoneCapture.mockRejectedValueOnce(new Error('麦克风权限被拒绝'));

  render(<MainConsole />);

  fireEvent.click(screen.getByText('启动语音'));
  await screen.findByText('语音已就绪');

  fireEvent.click(screen.getByText('开始收音'));

  await waitFor(() => {
    expect(screen.getByText('麦克风权限被拒绝')).toBeInTheDocument();
  });
  // Button must remain '开始收音' — UI must not be stuck in capturing state
  expect(screen.queryByText('结束收音')).not.toBeInTheDocument();
});

// ── Push-to-talk error: stop failure surfaces error and resets capturing state ──
it('push to talk stop error surfaces error message and resets capturing state', async () => {
  mockState.stopMicrophoneCapture.mockRejectedValueOnce(new Error('麦克风停止失败'));

  render(<MainConsole />);

  fireEvent.click(screen.getByText('启动语音'));
  await screen.findByText('语音已就绪');

  fireEvent.click(screen.getByText('开始收音'));
  await waitFor(() => expect(mockState.startMicrophoneCapture).toHaveBeenCalledTimes(1));

  fireEvent.click(screen.getByText('结束收音'));

  await waitFor(() => {
    expect(screen.getByText('麦克风停止失败')).toBeInTheDocument();
  });
  // Button must flip back to '开始收音' — UI must not be stuck in capturing state
  expect(screen.queryByText('结束收音')).not.toBeInTheDocument();
});

// ── Task 5 edge-case 1: hotkeyArmed must be cleared even when streamChat fails ──
it('hotkeyArmed is cleared after streamChat failure so subsequent submit does not pass stale armed flag', async () => {
  mockState.streamChat
    .mockRejectedValueOnce(new Error('stream error'))
    .mockImplementationOnce(
      async (
        _query: string,
        onEvent: (event: string, data: Record<string, unknown>) => void,
      ) => {
        onEvent('session', { session_id: 'abc' });
        onEvent('text', { text: 'second response' });
        onEvent('done', { session_id: 'abc' });
      },
    );

  render(<MainConsole />);

  // Arm the hotkey flag
  await act(async () => {
    mockState.hotkeyCallback?.();
  });

  fireEvent.change(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), {
    target: { value: 'test' },
  });

  // First submit — streamChat rejects, routing is skipped
  fireEvent.click(screen.getByText('发送'));
  await waitFor(() => expect(screen.getByText('stream error')).toBeInTheDocument());

  // Second submit — streamChat succeeds; interpretVoice should see hotkeyArmed=false
  fireEvent.click(screen.getByText('发送'));
  await waitFor(() => expect(mockState.interpretVoice).toHaveBeenCalledTimes(1));

  // If the flag leaked, the call would receive true; it must receive false
  expect(mockState.interpretVoice).toHaveBeenCalledWith('test', false);
});

// ── Task 5 edge-case 2: voiceState must not stay 'listening' after stop failure ──
it('push to talk stop failure resets voiceState so mode label is not stuck at listening', async () => {
  mockState.stopMicrophoneCapture.mockRejectedValueOnce(new Error('麦克风停止失败'));

  render(<MainConsole />);

  fireEvent.click(screen.getByText('启动语音'));
  await screen.findByText('语音已就绪');

  fireEvent.click(screen.getByText('开始收音'));
  await waitFor(() => expect(mockState.startMicrophoneCapture).toHaveBeenCalledTimes(1));

  // voiceState was set to 'listening' when capture started
  expect(screen.getByText('语音模式 / 聆听中')).toBeInTheDocument();

  fireEvent.click(screen.getByText('结束收音'));
  await waitFor(() => expect(screen.getByText('麦克风停止失败')).toBeInTheDocument());

  // voiceState must not remain 'listening' — UI signals must be coherent
  expect(screen.queryByText('语音模式 / 聆听中')).not.toBeInTheDocument();
});

// ── Issue 2a: no reconnect voice button when speech dependency is 'missing' ───
it('diagnostics strip does not offer reconnect voice when speech is missing/unconfigured', async () => {
  mockState.loadHealth.mockResolvedValueOnce({
    ok: false,
    service: 'jarvis-server',
    mode: 'm1',
    degraded: true,
    dependencies: { database: 'ready', speech: 'missing' },
  });

  render(<MainConsole />);

  // Wait for diagnostics to render
  expect(await screen.findByText('语音未配置')).toBeInTheDocument();

  // Reconnect button must NOT be shown for an unconfigured (missing) speech dependency
  expect(screen.queryByText('重连语音')).not.toBeInTheDocument();
});

// ── Task 5 final: executeAction failure surfaces error and keeps pending confirmation ──
it('executeAction failure surfaces error message and keeps pending confirmation intact', async () => {
  mockState.interpretVoice.mockResolvedValueOnce({
    heard_wakeword: true,
    normalized_text: 'Jarvis delete danger.txt',
    workspace: null,
    clarification: null,
    action_proposal: {
      action_type: 'delete_file',
      target: 'danger.txt',
      risk_level: 'dangerous',
      requires_confirmation: true,
    },
  });
  mockState.executeAction.mockRejectedValueOnce(new Error('服务器执行失败'));

  render(<MainConsole />);

  fireEvent.change(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), {
    target: { value: 'Jarvis delete danger.txt' },
  });
  fireEvent.click(screen.getByText('发送'));
  fireEvent.click(await screen.findByText('批准执行'));

  await waitFor(() => {
    expect(screen.getByText('服务器执行失败')).toBeInTheDocument();
  });

  // Pending confirmation must remain intact — not removed on failure
  expect(screen.getByText('批准执行')).toBeInTheDocument();
});

// ── Issue 2b: connect failure surfaces as error message ───────────────────────
it('voice connect failure surfaces via error message instead of disappearing', async () => {
  mockState.connect.mockRejectedValueOnce(new Error('WebSocket connection failed'));

  render(<MainConsole />);

  fireEvent.click(screen.getByText('启动语音'));

  await waitFor(() => {
    expect(screen.getByText('WebSocket connection failed')).toBeInTheDocument();
  });

  // Voice must NOT appear ready after a failed connect
  expect(screen.queryByText('语音已就绪')).not.toBeInTheDocument();
});
