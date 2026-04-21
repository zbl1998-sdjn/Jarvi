function getServerBaseUrl(): string {
  return window.jarvisDesktop?.getServerBaseUrl() ?? 'http://127.0.0.1:8001';
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getServerBaseUrl()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Jarvis assistant request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export interface ActionProposal {
  action_type: string;
  target: string;
  risk_level: string;
  requires_confirmation: boolean;
}

export interface Interpretation {
  heard_wakeword: boolean;
  normalized_text: string;
  workspace?: string | null;
  clarification?: string | null;
  action_proposal?: ActionProposal | null;
  teacher_style?: string | null;
}

export interface SearchResult {
  scope: string;
  path: string;
  title: string;
  snippet: string;
}

export interface SummaryResult {
  summary: string;
  bullets: string[];
}

export interface TaskItem {
  id: number;
  title: string;
  detail: string;
  status: string;
  stage?: string;
}

export interface MemoryEntry {
  id: number;
  kind: string;
  content: string;
  source: string;
}

export interface ReminderEntry {
  id: number;
  message: string;
  task_id: number | null;
}

export interface ActionRecord {
  id: number;
  action_type: string;
  target: string;
  risk_level: string;
  status: string;
  detail: string;
}

export interface TimelineEntry {
  type: string;
  content: string;
}

export interface PreferenceState {
  teacher_style: string;
  voice_name: string;
}

export interface ResumeState {
  workspace: string;
  session_id: string | null;
}

export interface StageProgress {
  current_stage: string;
  completed_tasks: number;
  total_tasks: number;
  uploaded_contexts: number;
}

export interface UploadedContext {
  id: number;
  title: string;
  source_type: string;
  preview: string;
}

export interface HomeSnapshot {
  tasks: TaskItem[];
  memories: MemoryEntry[];
  reminders: ReminderEntry[];
  recent_actions: ActionRecord[];
  timeline: TimelineEntry[];
  preferences: PreferenceState;
  resume: ResumeState;
  stage_progress: StageProgress;
  uploaded_contexts: UploadedContext[];
}

export interface HealthStatus {
  ok: boolean;
  service: string;
  mode: string;
  degraded: boolean;
  dependencies: {
    database: string;
    llm?: string;
    speech?: string;
    config?: string;
  };
}

export interface RuntimeProviderConfig {
  id: string;
  label: string;
  base_url: string;
  api_key: string;
  model: string;
  enabled: boolean;
}

export interface RuntimeSpeechConfig {
  key: string;
  region: string;
  voice_name: string;
  language: string;
}

export interface RuntimeConfig {
  database_url: string;
  providers: RuntimeProviderConfig[];
  active_provider_id: string;
  speech: RuntimeSpeechConfig;
}

export interface RuntimeConfigCheck {
  active_provider_id: string;
  dependencies: {
    database: string;
    llm: string;
    speech: string;
    config: string;
  };
}

export async function interpretVoice(
  text: string,
  hotkeyArmed: boolean,
): Promise<Interpretation> {
  return fetchJson<Interpretation>('/api/assistant/interpret', {
    method: 'POST',
    body: JSON.stringify({ text, hotkey_armed: hotkeyArmed }),
  });
}

export async function searchWorkspace(
  query: string,
  scope = 'knowledge',
): Promise<SearchResult[]> {
  const searchParams = new URLSearchParams({ query, scope });
  const response = await fetchJson<{ results: SearchResult[] }>(
    `/api/search?${searchParams}`,
  );
  return response.results;
}

export async function summarizeContent(
  sourceType: string,
  content: string,
): Promise<SummaryResult> {
  return fetchJson<SummaryResult>('/api/summary', {
    method: 'POST',
    body: JSON.stringify({ source_type: sourceType, content }),
  });
}

export async function executeAction(
  actionType: string,
  target: string,
  content?: string,
  approved = false,
): Promise<ActionRecord> {
  return fetchJson<ActionRecord>('/api/actions/execute', {
    method: 'POST',
    body: JSON.stringify({
      action_type: actionType,
      target,
      content,
      approved,
    }),
  });
}

export async function createTask(title: string, detail = ''): Promise<TaskItem> {
  return fetchJson<TaskItem>('/api/tasks', {
    method: 'POST',
    body: JSON.stringify({ title, detail }),
  });
}

export async function loadHome(): Promise<HomeSnapshot> {
  return fetchJson<HomeSnapshot>('/api/home');
}

export async function loadHealth(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>('/api/health', {
    headers: {
      Accept: 'application/json',
    },
  });
}

export async function savePreferences(
  teacherStyle: string,
  voiceName: string,
): Promise<PreferenceState> {
  return fetchJson<PreferenceState>('/api/preferences', {
    method: 'POST',
    body: JSON.stringify({
      teacher_style: teacherStyle,
      voice_name: voiceName,
    }),
  });
}

export async function uploadContext(
  title: string,
  sourceType: string,
  content: string,
): Promise<UploadedContext> {
  return fetchJson<UploadedContext>('/api/context/upload', {
    method: 'POST',
    body: JSON.stringify({
      title,
      source_type: sourceType,
      content,
    }),
  });
}

export async function saveWorkspaceState(
  workspace: string,
  sessionId?: string,
): Promise<ResumeState> {
  return fetchJson<ResumeState>('/api/workspace/state', {
    method: 'POST',
    body: JSON.stringify({
      workspace,
      session_id: sessionId ?? null,
    }),
  });
}

export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  return fetchJson<RuntimeConfig>('/api/runtime-config');
}

export async function saveRuntimeConfig(
  runtimeConfig: RuntimeConfig,
): Promise<RuntimeConfig> {
  return fetchJson<RuntimeConfig>('/api/runtime-config', {
    method: 'POST',
    body: JSON.stringify(runtimeConfig),
  });
}

export async function checkRuntimeConfig(): Promise<RuntimeConfigCheck> {
  return fetchJson<RuntimeConfigCheck>('/api/runtime-config/check', {
    method: 'POST',
  });
}
