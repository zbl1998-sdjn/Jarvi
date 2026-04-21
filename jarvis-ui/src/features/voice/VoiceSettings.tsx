import { useEffect, useState } from 'react';

import type { PreferenceState } from '../../app/api/assistant-client';

const TEACHER_STYLES = ['幽默风趣型', '面试高压陪练型'];
const VOICE_OPTIONS = ['zh-CN-XiaoxiaoNeural', 'zh-CN-YunxiNeural', 'zh-CN-XiaochenNeural'];

interface VoiceSettingsProps {
  preferences: PreferenceState;
  onSave: (teacherStyle: string, voiceName: string) => Promise<void>;
}

export function VoiceSettings({ preferences, onSave }: VoiceSettingsProps) {
  const [teacherStyle, setTeacherStyle] = useState(preferences.teacher_style);
  const [voiceName, setVoiceName] = useState(preferences.voice_name);

  useEffect(() => {
    setTeacherStyle(preferences.teacher_style);
    setVoiceName(preferences.voice_name);
  }, [preferences.teacher_style, preferences.voice_name]);

  return (
    <section className="workspace-card workspace-card--compact">
      <h2>老师风格与音色</h2>
      <div className="settings-grid">
        <label className="settings-field">
          <span>老师风格</span>
          <select value={teacherStyle} onChange={(event) => setTeacherStyle(event.target.value)}>
            {TEACHER_STYLES.map((style) => (
              <option key={style} value={style}>
                {style}
              </option>
            ))}
          </select>
        </label>
        <label className="settings-field">
          <span>音色</span>
          <select value={voiceName} onChange={(event) => setVoiceName(event.target.value)}>
            {VOICE_OPTIONS.map((voice) => (
              <option key={voice} value={voice}>
                {voice}
              </option>
            ))}
          </select>
        </label>
        <button
          className="secondary-button"
          onClick={() => void onSave(teacherStyle, voiceName)}
          type="button"
        >
          保存风格
        </button>
      </div>
    </section>
  );
}
