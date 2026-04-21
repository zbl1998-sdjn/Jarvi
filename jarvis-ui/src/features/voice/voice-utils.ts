import type { VoiceState } from './VoiceOrb';

const FEMALE_HINTS = ['female', 'woman', 'girl', 'xiaoxiao', 'xiaoyi', '晓', '女'];
const MALE_HINTS = ['male', 'man', 'boy', 'yunxi', '云希', '男'];

export function getVoiceStateLabel(state: VoiceState): string {
  const labels: Record<VoiceState, string> = {
    idle: '待命',
    listening: '聆听中',
    thinking: '思考中',
    speaking: '播报中',
    interrupted: '已打断',
  };
  return labels[state];
}

export function getVoiceModeLabel(state: VoiceState): string {
  return `语音模式 / ${getVoiceStateLabel(state)}`;
}

export function getShellModeLabel(mode: string | undefined): string {
  if (!mode) {
    return '桌面外壳';
  }

  const normalized = mode.toLowerCase();
  if (normalized === 'desktop-shell') {
    return '桌面外壳';
  }
  if (normalized === 'm6') {
    return 'M6 常驻副驾';
  }
  return mode;
}

export function getVoiceToneLabel(voice: SpeechSynthesisVoice): string {
  const fingerprint = `${voice.name} ${voice.lang}`.toLowerCase();
  if (FEMALE_HINTS.some((hint) => fingerprint.includes(hint))) {
    return '温润女声';
  }
  if (MALE_HINTS.some((hint) => fingerprint.includes(hint))) {
    return '沉稳男声';
  }
  if (voice.lang.toLowerCase().startsWith('zh')) {
    return '自然中文';
  }
  return '系统音色';
}

export function getVoiceOptionLabel(voice: SpeechSynthesisVoice): string {
  return `${voice.name} · ${getVoiceToneLabel(voice)}`;
}

export function getPreferredVoice(
  voices: SpeechSynthesisVoice[],
): SpeechSynthesisVoice | undefined {
  const chineseVoices = voices.filter((voice) =>
    voice.lang.toLowerCase().startsWith('zh'),
  );
  return (
    chineseVoices.find((voice) => getVoiceToneLabel(voice) === '温润女声') ??
    chineseVoices[0] ??
    voices[0]
  );
}
