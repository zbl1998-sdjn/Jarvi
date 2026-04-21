import type { VoiceState } from '../../features/voice/VoiceOrb';

export type RealtimeEvent =
  | { type: 'voice_state'; state: VoiceState }
  | { type: 'transcript'; role: string; text: string; final: boolean }
  | {
      type: 'audio_chunk';
      text: string;
      final: boolean;
      audio_base64?: string;
      mime_type?: string;
    };

interface RealtimeHandlers {
  onEvent: (event: RealtimeEvent) => void;
  onError?: (error: Error) => void;
}

function getRealtimeUrl(): string {
  const serverBaseUrl =
    window.jarvisDesktop?.getServerBaseUrl() ?? 'http://127.0.0.1:8001';
  return `${serverBaseUrl.replace(/^http/, 'ws')}/ws/realtime`;
}

export function createRealtimeVoiceClient(handlers: RealtimeHandlers) {
  let socket: WebSocket | null = null;
  let readyPromise: Promise<void> | null = null;
  let audioContext: AudioContext | null = null;
  let microphoneStream: MediaStream | null = null;
  let processor: ScriptProcessorNode | null = null;
  let sourceNode: MediaStreamAudioSourceNode | null = null;

  function encodePcmChunk(samples: Float32Array): string {
    const pcm = new Int16Array(samples.length);
    for (let index = 0; index < samples.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, samples[index]));
      pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }

    const bytes = new Uint8Array(pcm.buffer);
    let binary = '';
    for (const value of bytes) {
      binary += String.fromCharCode(value);
    }
    return btoa(binary);
  }

  function ensureConnected(): Promise<void> {
    if (socket?.readyState === WebSocket.OPEN && readyPromise) {
      return readyPromise;
    }

    const activeSocket = new WebSocket(getRealtimeUrl());
    socket = activeSocket;
    readyPromise = new Promise((resolve, reject) => {
      activeSocket.addEventListener(
        'open',
        () => {
          activeSocket.send(JSON.stringify({ type: 'start' }));
          resolve();
        },
        { once: true },
      );
      activeSocket.addEventListener('message', (event) => {
        handlers.onEvent(JSON.parse(event.data) as RealtimeEvent);
      });
      activeSocket.addEventListener(
        'error',
        () => {
          const error = new Error('Jarvis realtime socket failed');
          handlers.onError?.(error);
          reject(error);
        },
        { once: true },
      );
      activeSocket.addEventListener('close', () => {
        socket = null;
        readyPromise = null;
      });
    });

    return readyPromise;
  }

  return {
    async connect() {
      await ensureConnected();
    },
    async startMicrophoneCapture() {
      await ensureConnected();
      if (audioContext || microphoneStream || processor || sourceNode) {
        return;
      }

      microphoneStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      audioContext = new AudioContext();
      sourceNode = audioContext.createMediaStreamSource(microphoneStream);
      processor = audioContext.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        const channelData = event.inputBuffer.getChannelData(0);
        socket?.send(
          JSON.stringify({
            type: 'audio_chunk',
            audio_base64: encodePcmChunk(channelData),
          }),
        );
      };
      sourceNode.connect(processor);
      processor.connect(audioContext.destination);
    },
    async stopMicrophoneCapture(voiceName?: string, teacherStyle?: string) {
      await ensureConnected();
      const sampleRate = audioContext?.sampleRate ?? 16000;
      processor?.disconnect();
      processor = null;
      sourceNode?.disconnect();
      sourceNode = null;
      microphoneStream?.getTracks().forEach((track) => track.stop());
      microphoneStream = null;
      if (audioContext) {
        await audioContext.close();
        audioContext = null;
      }

      socket?.send(
        JSON.stringify({
          type: 'audio_commit',
          sample_rate_hz: Math.round(sampleRate),
          voice_name: voiceName,
          teacher_style: teacherStyle,
        }),
      );
    },
    async sendText(text: string, teacherStyle?: string) {
      await ensureConnected();
      socket?.send(JSON.stringify({ type: 'input_text', text, teacher_style: teacherStyle }));
    },
    interrupt() {
      socket?.send(JSON.stringify({ type: 'interrupt' }));
    },
    disconnect() {
      processor?.disconnect();
      processor = null;
      sourceNode?.disconnect();
      sourceNode = null;
      microphoneStream?.getTracks().forEach((track) => track.stop());
      microphoneStream = null;
      void audioContext?.close();
      audioContext = null;
      socket?.close();
      socket = null;
      readyPromise = null;
    },
  };
}
