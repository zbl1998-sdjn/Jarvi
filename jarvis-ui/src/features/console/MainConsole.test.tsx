import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

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
    workspace: 'search',
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
      voice_name: 'zh-CN-XiaoxiaoNeural',
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
  loadHealth: vi.fn(async () => ({
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
      key: 'azure-key',
      region: 'eastasia',
      voice_name: 'zh-CN-XiaoxiaoNeural',
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

it('shows speaking state, search workspace results, and voice reply', async () => {
  render(<MainConsole />);

  fireEvent.click(screen.getByText('启动语音'));
  expect(await screen.findByText('语音已就绪')).toBeInTheDocument();
  fireEvent.change(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), {
    target: { value: 'open lesson' },
  });
  fireEvent.click(screen.getByText('按住说话'));

  expect(mockState.connect).toHaveBeenCalledTimes(1);
  expect(mockState.sendText).toHaveBeenCalledWith('open lesson', '幽默风趣型');
  await waitFor(() => {
    expect(mockState.searchWorkspace).toHaveBeenCalledWith('open lesson', 'auto');
  });

  await act(async () => {
    mockState.realtimeHandlers?.onEvent({
      type: 'voice_state',
      state: 'speaking',
    });
    mockState.realtimeHandlers?.onEvent({
      type: 'audio_chunk',
      text: 'Jarvis M2 已收到语音：open lesson',
      final: true,
    });
  });

  expect(await screen.findByText('播报中')).toBeInTheDocument();
  expect(
    await screen.findByText('Jarvis M2 已收到语音：open lesson'),
  ).toBeInTheDocument();
  expect(await screen.findByText('搜索中心')).toBeInTheDocument();
  expect(await screen.findByText('Found open lesson')).toBeInTheDocument();
});

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

it('queues dangerous action confirmations and executes them when approved', async () => {
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

  fireEvent.click(screen.getByText('启动语音'));
  expect(await screen.findByText('语音已就绪')).toBeInTheDocument();
  fireEvent.change(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), {
    target: { value: 'Jarvis delete danger.txt' },
  });
  fireEvent.click(screen.getByText('按住说话'));
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

it('saves style preferences and uploads snippet context', async () => {
  render(<MainConsole />);

  const comboboxes = await screen.findAllByRole('combobox');
  fireEvent.change(comboboxes[0], { target: { value: '面试高压陪练型' } });
  fireEvent.change(comboboxes[1], { target: { value: 'zh-CN-YunxiNeural' } });
  fireEvent.click(screen.getByText('保存风格'));

  expect(mockState.savePreferences).toHaveBeenCalledWith(
    '面试高压陪练型',
    'zh-CN-YunxiNeural',
  );

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

it('renders configuration center with provider controls and action buttons', async () => {
  render(<MainConsole />);

  expect(await screen.findByText('服务与模型配置')).toBeInTheDocument();
  expect(await screen.findByText('模型 Provider')).toBeInTheDocument();
  expect(await screen.findByText('新增 Provider')).toBeInTheDocument();
  expect(await screen.findByText('检测数据库')).toBeInTheDocument();
  expect(await screen.findByText('检测模型连接')).toBeInTheDocument();
  expect(await screen.findByText('检测语音配置')).toBeInTheDocument();
  expect(await screen.findByText('重新加载配置')).toBeInTheDocument();
  expect(await screen.findByText('恢复上次会话')).toBeInTheDocument();
  expect(await screen.findByText('刷新首页状态')).toBeInTheDocument();
});
