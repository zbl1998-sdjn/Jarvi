import { useEffect, useMemo, useRef, useState } from 'react';

import {
  checkRuntimeConfig,
  createTask,
  executeAction,
  interpretVoice,
  loadHealth,
  loadHome,
  loadRuntimeConfig,
  type RuntimeConfig,
  savePreferences,
  saveRuntimeConfig,
  saveWorkspaceState,
  searchWorkspace,
  summarizeContent,
  uploadContext,
  type ActionProposal,
  type HealthStatus,
  type HomeSnapshot,
  type SearchResult,
  type SummaryResult,
} from '../../app/api/assistant-client';
import { streamChat } from '../../app/api/chat-client';
import { createRealtimeVoiceClient } from '../../app/api/realtime-client';
import { RuntimeConfigPanel } from '../config/RuntimeConfigPanel';
import { OverlayDrawer } from '../layout/OverlayDrawer';
import { LeftDrawer } from '../panels/LeftDrawer';
import { RightDrawer } from '../panels/RightDrawer';
import { ContextUpload } from '../uploads/ContextUpload';
import { VoiceOrb, type VoiceState } from '../voice/VoiceOrb';
import { VoiceSettings } from '../voice/VoiceSettings';
import { getShellModeLabel, getVoiceModeLabel } from '../voice/voice-utils';
import { WorkspaceRouter, type WorkspaceId } from '../workspace/WorkspaceRouter';
import { CommandDock } from './CommandDock';
import { TopStatusBar } from './TopStatusBar';

const EMPTY_HOME: HomeSnapshot = {
  tasks: [],
  memories: [],
  reminders: [],
  recent_actions: [],
  timeline: [],
  preferences: {
    teacher_style: '幽默风趣型',
    voice_name: 'zh-CN-XiaoxiaoNeural',
  },
  resume: {
    workspace: 'console',
    session_id: null,
  },
  stage_progress: {
    current_stage: 'M6',
    completed_tasks: 0,
    total_tasks: 0,
    uploaded_contexts: 0,
  },
  uploaded_contexts: [],
};

export function MainConsole() {
  const shellInfo = useMemo(() => window.jarvisDesktop?.getShellInfo(), []);
  const [query, setQuery] = useState('');
  const [reply, setReply] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [voiceReady, setVoiceReady] = useState(false);
  const [isCapturingAudio, setIsCapturingAudio] = useState(false);
  const [hotkeyArmed, setHotkeyArmed] = useState(false);
  const [activeWorkspace, setActiveWorkspace] =
    useState<WorkspaceId>('console');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [summaryResult, setSummaryResult] = useState<SummaryResult | null>(
    null,
  );
  const [homeSnapshot, setHomeSnapshot] = useState<HomeSnapshot>(EMPTY_HOME);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig | null>(null);
  const [pendingConfirmations, setPendingConfirmations] = useState<
    ActionProposal[]
  >([]);
  const [leftDrawerOpen, setLeftDrawerOpen] = useState(false);
  const [rightDrawerOpen, setRightDrawerOpen] = useState(false);
  const initialHomeLoadedRef = useRef(false);
  const realtimeClientRef = useRef(
    createRealtimeVoiceClient({
      onEvent: (event) => {
        if (event.type === 'voice_state') {
          setVoiceState(event.state);
        }

        if (event.type === 'audio_chunk') {
          setReply((current) => current + event.text);
          if (event.audio_base64 && event.mime_type) {
            const audio = new Audio(
              `data:${event.mime_type};base64,${event.audio_base64}`,
            );
            void audio.play().catch(() => undefined);
          }
        }
      },
      onError: (error) => {
        setErrorMessage(error.message);
      },
    }),
  );

  async function loadHomeSnapshot() {
    try {
      const snapshot = await loadHome();
      setHomeSnapshot(snapshot);
      if (!initialHomeLoadedRef.current) {
        initialHomeLoadedRef.current = true;
        setActiveWorkspace((snapshot.resume.workspace as WorkspaceId) ?? 'console');
        setSessionId(snapshot.resume.session_id);
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '加载 Jarvis 首页失败',
      );
    }
  }

  async function loadHealthStatus() {
    try {
      setHealthStatus(await loadHealth());
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '读取服务状态失败',
      );
    }
  }

  async function loadRuntimeConfiguration() {
    try {
      setRuntimeConfig(await loadRuntimeConfig());
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '读取运行时配置失败',
      );
    }
  }

  useEffect(() => {
    void loadHomeSnapshot();
    void loadHealthStatus();
    void loadRuntimeConfiguration();
    const unsubscribe = window.jarvisDesktop?.onHotkeyTriggered?.(() => {
      setVoiceReady(true);
      setHotkeyArmed(true);
      setVoiceState('listening');
      setReply('已收到热键唤醒，请继续下达指令。');
    });

    return () => {
      unsubscribe?.();
      realtimeClientRef.current.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!initialHomeLoadedRef.current) {
      return;
    }
    void saveWorkspaceState(activeWorkspace, sessionId ?? undefined);
  }, [activeWorkspace, sessionId]);

  async function handleSubmit() {
    const trimmedQuery = query.trim();
    if (!trimmedQuery || isStreaming) {
      return;
    }

    setReply('');
    setErrorMessage('');
    setIsStreaming(true);

    try {
      await streamChat(
        trimmedQuery,
        (event, data) => {
          if (event === 'session' && typeof data.session_id === 'string') {
            setSessionId(data.session_id);
          }

          if (event === 'text' && typeof data.text === 'string') {
            setReply((current) => current + data.text);
          }

          if (event === 'done' && typeof data.session_id === 'string') {
            setSessionId(data.session_id);
          }
        },
        sessionId ?? undefined,
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Jarvis 文本流失败',
      );
    } finally {
      setIsStreaming(false);
      await loadHomeSnapshot();
    }
  }

  async function handleVoiceConnect() {
    setErrorMessage('');
    await realtimeClientRef.current.connect();
    setVoiceReady(true);
    setHotkeyArmed(true);
  }

  async function handlePushToTalk() {
    const trimmedQuery = query.trim();
    if (!voiceReady) {
      return;
    }

    setReply('');
    setErrorMessage('');
    if (!trimmedQuery) {
      if (!isCapturingAudio) {
        await realtimeClientRef.current.startMicrophoneCapture();
        setVoiceState('listening');
        setIsCapturingAudio(true);
        return;
      }

      await realtimeClientRef.current.stopMicrophoneCapture(
        homeSnapshot.preferences.voice_name,
        homeSnapshot.preferences.teacher_style,
      );
      setIsCapturingAudio(false);
      return;
    }

    await realtimeClientRef.current.sendText(
      trimmedQuery,
      homeSnapshot.preferences.teacher_style,
    );

    const interpretation = await interpretVoice(trimmedQuery, hotkeyArmed);

    if (interpretation.workspace === 'search') {
      setSearchResults(await searchWorkspace(trimmedQuery, 'auto'));
      setActiveWorkspace('search');
    }

    if (interpretation.workspace === 'summary') {
      setSummaryResult(await summarizeContent('voice', trimmedQuery));
      setActiveWorkspace('summary');
    }

    if (interpretation.workspace === 'records') {
      setActiveWorkspace('records');
    }

    if (interpretation.workspace === 'tasks') {
      setActiveWorkspace('tasks');
    }

    if (interpretation.action_proposal) {
      setPendingConfirmations((current) => [
        ...current,
        interpretation.action_proposal as ActionProposal,
      ]);
    }

    if (interpretation.clarification) {
      setReply(interpretation.clarification);
    }

    if (interpretation.teacher_style) {
      await handleSavePreferences(
        interpretation.teacher_style,
        homeSnapshot.preferences.voice_name,
      );
    }

    setHotkeyArmed(false);
    await loadHomeSnapshot();
  }

  function handleInterrupt() {
    if (isCapturingAudio) {
      void realtimeClientRef.current.stopMicrophoneCapture(
        homeSnapshot.preferences.voice_name,
        homeSnapshot.preferences.teacher_style,
      );
      setIsCapturingAudio(false);
    }
    realtimeClientRef.current.interrupt();
  }

  async function handleSearch() {
    const trimmedQuery = query.trim() || 'Jarvis';
    setSearchResults(await searchWorkspace(trimmedQuery, 'auto'));
    setActiveWorkspace('search');
  }

  async function handleWebSearch() {
    const trimmedQuery = query.trim() || 'Jarvis';
    setSearchResults(await searchWorkspace(trimmedQuery, 'web'));
    setActiveWorkspace('search');
  }

  async function handleSummarize() {
    const content = reply || query || 'Jarvis 工作台总结请求';
    setSummaryResult(await summarizeContent('workspace', content));
    setActiveWorkspace('summary');
    await loadHomeSnapshot();
  }

  async function handleCreateTask() {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }
    await createTask(trimmedQuery, '来自 Jarvis 命令坞。');
    setActiveWorkspace('tasks');
    await loadHomeSnapshot();
  }

  async function handleApproveAction(proposal: ActionProposal) {
    const result = await executeAction(
      proposal.action_type,
      proposal.target,
      undefined,
      true,
    );
    setReply(result.detail);
    setPendingConfirmations((current) =>
      current.filter(
        (item) =>
          !(
            item.action_type === proposal.action_type &&
            item.target === proposal.target
          ),
      ),
    );
    setActiveWorkspace('records');
    await loadHomeSnapshot();
  }

  async function handleSavePreferences(teacherStyle: string, voiceName: string) {
    const preferences = await savePreferences(teacherStyle, voiceName);
    setHomeSnapshot((current) => ({
      ...current,
      preferences,
    }));
  }

  async function handleUploadContext(title: string, sourceType: string, content: string) {
    await uploadContext(title, sourceType, content);
    setActiveWorkspace('search');
    await loadHomeSnapshot();
  }

  async function handleSaveRuntimeConfig(nextRuntimeConfig: RuntimeConfig) {
    const saved = await saveRuntimeConfig(nextRuntimeConfig);
    setRuntimeConfig(saved);
    await loadHealthStatus();
    setReply('运行时配置已保存。');
  }

  async function handleReloadRuntimeConfig() {
    await loadRuntimeConfiguration();
    await loadHealthStatus();
    setReply('运行时配置已重新加载。');
  }

  async function handleCheckRuntimeConfig() {
    const result = await checkRuntimeConfig();
    setReply(
      `数据库：${result.dependencies.database}；模型：${result.dependencies.llm}；语音：${result.dependencies.speech}`,
    );
    await loadHealthStatus();
    return result;
  }

  function handleResumeSession() {
    setSessionId(homeSnapshot.resume.session_id);
    setActiveWorkspace((homeSnapshot.resume.workspace as WorkspaceId) ?? 'console');
    setReply('已恢复到上次会话。');
  }

  const modeLabel = voiceReady ? getVoiceModeLabel(voiceState) : '文本模式 / M1';
  const statusItems = [
    shellInfo?.resident ? '后台常驻已开启' : '前台模式',
    `壳层：${getShellModeLabel(shellInfo?.mode)}`,
    healthStatus?.degraded ? '服务未就绪' : '服务就绪',
    `老师：${homeSnapshot.preferences.teacher_style}`,
    `音色：${homeSnapshot.preferences.voice_name}`,
  ];
  const degradedMessage = [
    healthStatus?.dependencies.database === 'offline' ? '数据库未连接' : null,
    healthStatus?.dependencies.llm === 'missing' ? '模型未配置' : null,
    healthStatus?.dependencies.speech === 'missing' ? '语音未配置' : null,
  ]
    .filter(Boolean)
    .join('；');

  return (
    <div className="console-shell console-shell--hud">
      <TopStatusBar modeLabel={modeLabel} statusItems={statusItems} />
      <div className="console-layout console-layout--collapsed">
        <button
          aria-expanded={leftDrawerOpen}
          aria-label="展开左侧学习面板"
          className="drawer-handle drawer-handle--left"
          onClick={() => setLeftDrawerOpen((value) => !value)}
          type="button"
        >
          学习面板
        </button>
        <OverlayDrawer
          onClose={() => setLeftDrawerOpen(false)}
          open={leftDrawerOpen}
          side="left"
          title="学习进度与记忆"
        >
          <LeftDrawer
            memories={homeSnapshot.memories}
            preferences={homeSnapshot.preferences}
            reminders={homeSnapshot.reminders}
            resume={homeSnapshot.resume}
            stageProgress={homeSnapshot.stage_progress}
            tasks={homeSnapshot.tasks}
          />
        </OverlayDrawer>
        <main className="console-center console-center--wide">
          <VoiceOrb state={voiceState} />
          <div className="shell-meta">
            <span>{shellInfo?.app ?? 'Jarvis'}</span>
            <span>{getShellModeLabel(shellInfo?.mode)}</span>
            <span>{sessionId ? `会话 ${sessionId}` : '当前没有活跃会话'}</span>
          </div>
          <RuntimeConfigPanel
            onCheck={handleCheckRuntimeConfig}
            onFocusUpload={() => {
              setActiveWorkspace('search');
              setReply('可在“资料上传”区域继续添加图片、文件或代码片段。');
            }}
            onOpenRecords={() => setActiveWorkspace('records')}
            onOpenTasks={() => setActiveWorkspace('tasks')}
            onOpenWebSearch={handleWebSearch}
            onRefreshHome={async () => {
              await loadHomeSnapshot();
              await loadHealthStatus();
              await loadRuntimeConfiguration();
            }}
            onReload={handleReloadRuntimeConfig}
            onResumeSession={handleResumeSession}
            onSave={handleSaveRuntimeConfig}
            runtimeConfig={runtimeConfig}
          />
          <VoiceSettings
            onSave={(teacherStyle, voiceName) =>
              handleSavePreferences(teacherStyle, voiceName)
            }
            preferences={homeSnapshot.preferences}
          />
          <ContextUpload onUpload={handleUploadContext} />
          <textarea
            className="command-prompt"
            placeholder="向 Jarvis 发送文本指令…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="control-row">
            <button
              className="secondary-button"
              onClick={() => void handleVoiceConnect()}
              type="button"
            >
              {voiceReady ? '语音已就绪' : '启动语音'}
            </button>
            <button
              className="secondary-button"
              disabled={!voiceReady}
              onClick={() => void handlePushToTalk()}
              type="button"
            >
              {isCapturingAudio ? '结束收音' : query.trim() ? '按住说话' : '开始收音'}
            </button>
            <button
              className="secondary-button"
              disabled={!voiceReady}
              onClick={handleInterrupt}
              type="button"
            >
              打断播报
            </button>
          </div>
          <button
            className="send-button"
            onClick={() => void handleSubmit()}
            type="button"
          >
            {isStreaming ? '发送中…' : '发送'}
          </button>
          <section
            className={`reply-card${healthStatus?.degraded ? ' reply-card--warning' : ''}`}
          >
            {healthStatus?.degraded
              ? `服务未就绪，当前处于受限模式。${degradedMessage || '请先检查运行时配置。'}`
              : reply || errorMessage || '等待文本或语音流…'}
          </section>
          <WorkspaceRouter
            activeWorkspace={activeWorkspace}
            recentActions={homeSnapshot.recent_actions}
            searchResults={searchResults}
            summaryResult={summaryResult}
            timeline={homeSnapshot.timeline}
            uploadedContexts={homeSnapshot.uploaded_contexts}
          />
        </main>
        <button
          aria-expanded={rightDrawerOpen}
          aria-label="展开右侧动作面板"
          className="drawer-handle drawer-handle--right"
          onClick={() => setRightDrawerOpen((value) => !value)}
          type="button"
        >
          动作面板
          {pendingConfirmations.length > 0 ? (
            <span className="drawer-handle__badge">{pendingConfirmations.length}</span>
          ) : null}
        </button>
        <OverlayDrawer
          onClose={() => setRightDrawerOpen(false)}
          open={rightDrawerOpen}
          side="right"
          title="动作确认与记录"
        >
          <RightDrawer
            onApproveAction={(proposal) => void handleApproveAction(proposal)}
            pendingConfirmations={pendingConfirmations}
            recentActions={homeSnapshot.recent_actions}
          />
        </OverlayDrawer>
      </div>
      <CommandDock
        activeWorkspace={activeWorkspace}
        onCreateTask={() => void handleCreateTask()}
        onOpenSearch={() => setActiveWorkspace('search')}
        onSearch={() => void handleSearch()}
        onSelectWorkspace={setActiveWorkspace}
        onSummarize={() => void handleSummarize()}
      />
    </div>
  );
}
