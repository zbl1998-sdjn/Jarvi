import { useEffect, useMemo, useState } from 'react';

import type {
  RuntimeConfig,
  RuntimeConfigCheck,
  RuntimeProviderConfig,
} from '../../app/api/assistant-client';

interface RuntimeConfigPanelProps {
  runtimeConfig: RuntimeConfig | null;
  onSave: (runtimeConfig: RuntimeConfig) => Promise<void>;
  onReload: () => Promise<void>;
  onCheck: () => Promise<RuntimeConfigCheck>;
  onOpenWebSearch: () => Promise<void>;
  onFocusUpload: () => void;
  onResumeSession: () => void;
  onOpenRecords: () => void;
  onOpenTasks: () => void;
  onRefreshHome: () => Promise<void>;
}

const EMPTY_CONFIG: RuntimeConfig = {
  database_url: '',
  providers: [
    {
      id: 'provider-1',
      label: '',
      base_url: '',
      api_key: '',
      model: '',
      enabled: true,
    },
  ],
  active_provider_id: 'provider-1',
  speech: {
    api_key: '',
    asr_model: 'paraformer-realtime-v2',
    tts_model: 'cosyvoice-v1',
    voice_name: 'longxiaochun',
    language: 'zh-CN',
    provider: 'aliyun',
  },
  knowledge_root: '',
};

export function RuntimeConfigPanel({
  runtimeConfig,
  onSave,
  onReload,
  onCheck,
  onOpenWebSearch,
  onFocusUpload,
  onResumeSession,
  onOpenRecords,
  onOpenTasks,
  onRefreshHome,
}: RuntimeConfigPanelProps) {
  const [draft, setDraft] = useState<RuntimeConfig>(runtimeConfig ?? EMPTY_CONFIG);
  const [checkResult, setCheckResult] = useState<RuntimeConfigCheck | null>(null);

  useEffect(() => {
    setDraft(runtimeConfig ?? EMPTY_CONFIG);
  }, [runtimeConfig]);

  const activeProviderIndex = useMemo(
    () =>
      Math.max(
        0,
        draft.providers.findIndex((provider) => provider.id === draft.active_provider_id),
      ),
    [draft.active_provider_id, draft.providers],
  );

  function updateProvider(index: number, key: keyof RuntimeProviderConfig, value: string | boolean) {
    setDraft((current) => ({
      ...current,
      providers: current.providers.map((provider, providerIndex) =>
        providerIndex === index ? { ...provider, [key]: value } : provider,
      ),
    }));
  }

  function addProvider() {
    const providerId = `provider-${draft.providers.length + 1}`;
    setDraft((current) => ({
      ...current,
      providers: [
        ...current.providers,
        {
          id: providerId,
          label: '',
          base_url: '',
          api_key: '',
          model: '',
          enabled: true,
        },
      ],
      active_provider_id: current.active_provider_id || providerId,
    }));
  }

  function removeProvider(index: number) {
    setDraft((current) => {
      if (current.providers.length === 1) {
        return current;
      }

      const nextProviders = current.providers.filter((_, providerIndex) => providerIndex !== index);
      const nextActiveProviderId = nextProviders.some(
        (provider) => provider.id === current.active_provider_id,
      )
        ? current.active_provider_id
        : nextProviders[0].id;
      return {
        ...current,
        providers: nextProviders,
        active_provider_id: nextActiveProviderId,
      };
    });
  }

  async function runCheck() {
    setCheckResult(await onCheck());
  }

  return (
    <section className="workspace-card workspace-card--compact">
      <h2>服务与模型配置</h2>
      <div className="settings-grid settings-grid--single">
        <section className="provider-card">
          <h3>快速设置</h3>
          <label className="settings-field">
            <span>LLM 提供商</span>
            <select
              className="settings-input"
              onChange={(event) =>
                setDraft((current) => ({ ...current, active_provider_id: event.target.value }))
              }
              value={draft.active_provider_id}
            >
              {draft.providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.label || provider.id}
                </option>
              ))}
            </select>
          </label>
          <label className="settings-field">
            <span>LLM 模型</span>
            <input
              className="settings-input"
              onChange={(event) =>
                updateProvider(activeProviderIndex, 'model', event.target.value)
              }
              value={draft.providers[activeProviderIndex]?.model ?? ''}
            />
          </label>
          <label className="settings-field">
            <span>语音提供商</span>
            <input
              className="settings-input"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  speech: { ...current.speech, provider: event.target.value },
                }))
              }
              value={draft.speech.provider}
            />
          </label>
          <label className="settings-field">
            <span>知识库路径</span>
            <input
              className="settings-input"
              onChange={(event) =>
                setDraft((current) => ({ ...current, knowledge_root: event.target.value }))
              }
              value={draft.knowledge_root}
            />
          </label>
        </section>
        <label className="settings-field">
          <span>数据库连接串</span>
          <input
            className="settings-input"
            onChange={(event) =>
              setDraft((current) => ({ ...current, database_url: event.target.value }))
            }
            value={draft.database_url}
          />
        </label>
        <div className="config-button-row">
          <button className="secondary-button" onClick={() => void runCheck()} type="button">
            检测数据库
          </button>
          <button className="secondary-button" onClick={() => void onReload()} type="button">
            重新加载配置
          </button>
          <button className="secondary-button" onClick={() => void onSave(draft)} type="button">
            保存配置
          </button>
        </div>
        <section className="provider-list">
          <div className="provider-list__header">
            <h3>模型 Provider</h3>
            <button className="secondary-button" onClick={addProvider} type="button">
              新增 Provider
            </button>
          </div>
          {draft.providers.map((provider, index) => (
            <article className="provider-card" key={provider.id}>
              <label className="settings-field">
                <span>名称</span>
                <input
                  className="settings-input"
                  onChange={(event) => updateProvider(index, 'label', event.target.value)}
                  value={provider.label}
                />
              </label>
              <label className="settings-field">
                <span>Base URL</span>
                <input
                  className="settings-input"
                  onChange={(event) => updateProvider(index, 'base_url', event.target.value)}
                  value={provider.base_url}
                />
              </label>
              <label className="settings-field">
                <span>API Key</span>
                <input
                  className="settings-input"
                  onChange={(event) => updateProvider(index, 'api_key', event.target.value)}
                  value={provider.api_key}
                />
              </label>
              <label className="settings-field">
                <span>模型名</span>
                <input
                  className="settings-input"
                  onChange={(event) => updateProvider(index, 'model', event.target.value)}
                  value={provider.model}
                />
              </label>
              <div className="config-button-row">
                <button
                  className="secondary-button"
                  onClick={() =>
                    setDraft((current) => ({ ...current, active_provider_id: provider.id }))
                  }
                  type="button"
                >
                  {activeProviderIndex === index ? '当前模型' : '设为当前'}
                </button>
                <button className="secondary-button" onClick={() => void runCheck()} type="button">
                  检测模型连接
                </button>
                <button
                  className="secondary-button"
                  onClick={() => removeProvider(index)}
                  type="button"
                >
                  删除 Provider
                </button>
              </div>
            </article>
          ))}
        </section>
        <section className="provider-card">
          <h3>语音配置（阿里云 DashScope）</h3>
          <label className="settings-field">
            <span>DashScope API Key</span>
            <input
              className="settings-input"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  speech: { ...current.speech, api_key: event.target.value },
                }))
              }
              value={draft.speech.api_key}
            />
          </label>
          <label className="settings-field">
            <span>ASR 模型</span>
            <input
              className="settings-input"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  speech: { ...current.speech, asr_model: event.target.value },
                }))
              }
              value={draft.speech.asr_model}
            />
          </label>
          <label className="settings-field">
            <span>TTS 模型</span>
            <input
              className="settings-input"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  speech: { ...current.speech, tts_model: event.target.value },
                }))
              }
              value={draft.speech.tts_model}
            />
          </label>
          <label className="settings-field">
            <span>音色（Voice）</span>
            <select
              className="settings-input"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  speech: { ...current.speech, voice_name: event.target.value },
                }))
              }
              value={draft.speech.voice_name}
            >
              <option value="longxiaochun">longxiaochun（长晓春·女声，推荐）</option>
              <option value="longxiaobai">longxiaobai（长晓白·女声）</option>
              <option value="longwan">longwan（龙婉·女声）</option>
              <option value="longcheng">longcheng（龙橙·男声）</option>
              <option value="longhua">longhua（龙华·男声）</option>
            </select>
          </label>
          <label className="settings-field">
            <span>识别语言</span>
            <input
              className="settings-input"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  speech: { ...current.speech, language: event.target.value },
                }))
              }
              value={draft.speech.language}
            />
          </label>
          <div className="config-button-row">
            <button className="secondary-button" onClick={() => void runCheck()} type="button">
              检测语音配置
            </button>
          </div>
        </section>
        <div className="config-button-row">
          <button className="secondary-button" onClick={() => void onOpenWebSearch()} type="button">
            网页搜索
          </button>
          <button className="secondary-button" onClick={onFocusUpload} type="button">
            资料上传
          </button>
          <button className="secondary-button" onClick={onResumeSession} type="button">
            恢复上次会话
          </button>
          <button className="secondary-button" onClick={onOpenRecords} type="button">
            打开记录
          </button>
          <button className="secondary-button" onClick={onOpenTasks} type="button">
            打开任务
          </button>
          <button className="secondary-button" onClick={() => void onRefreshHome()} type="button">
            刷新首页状态
          </button>
        </div>
        {checkResult ? (
          <p className="config-status">
            数据库：{checkResult.dependencies.database} / 模型：{checkResult.dependencies.llm} / 语音：
            {checkResult.dependencies.speech}
          </p>
        ) : null}
      </div>
    </section>
  );
}
