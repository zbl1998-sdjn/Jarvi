import { useMemo, useState } from 'react';

import type {
  RuntimeConfig,
  RuntimeConfigCheck,
} from '../../app/api/assistant-client';
import { RuntimeConfigPanel } from './RuntimeConfigPanel';

interface RuntimeSettingsSummaryProps {
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

export function RuntimeSettingsSummary(props: RuntimeSettingsSummaryProps) {
  const [expanded, setExpanded] = useState(false);

  const summaryText = useMemo(() => {
    if (!props.runtimeConfig) return '未加载';
    const active = props.runtimeConfig.providers.find(
      (p) => p.id === props.runtimeConfig!.active_provider_id,
    );
    const providerPart = active ? `${active.label} / ${active.model}` : '未配置';
    const voicePart = props.runtimeConfig.speech.voice_name;
    return `${providerPart} · ${voicePart}`;
  }, [props.runtimeConfig]);

  return (
    <div className="runtime-summary">
      <div className="runtime-summary__row">
        <span className="runtime-summary__text">当前配置：{summaryText}</span>
        <button
          className="secondary-button"
          onClick={() => setExpanded((v) => !v)}
          type="button"
        >
          {expanded ? '收起配置' : '展开配置'}
        </button>
      </div>
      {expanded && <RuntimeConfigPanel {...props} />}
    </div>
  );
}
