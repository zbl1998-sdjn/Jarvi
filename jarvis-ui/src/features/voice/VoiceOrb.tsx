import { getVoiceStateLabel } from './voice-utils';

export type VoiceState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'interrupted';

interface VoiceOrbProps {
  state?: VoiceState;
}

export function VoiceOrb({ state = 'idle' }: VoiceOrbProps) {
  return (
    <div className={`voice-orb voice-orb--${state}`}>
      <div className="voice-orb__ring" />
      <div className="voice-orb__core">{getVoiceStateLabel(state)}</div>
    </div>
  );
}
