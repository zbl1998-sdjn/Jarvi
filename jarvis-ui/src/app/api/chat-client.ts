export interface ParsedEvent {
  event: string;
  data: Record<string, unknown>;
}

export function parseEventBlocks(buffer: string): ParsedEvent[] {
  return buffer
    .trim()
    .split(/\r?\n\r?\n+/)
    .filter(Boolean)
    .map((block) => {
      const lines = block.split(/\r?\n/);
      const eventLine =
        lines.find((line) => line.startsWith('event:')) ?? 'event: message';
      const dataLine =
        lines.find((line) => line.startsWith('data:')) ?? 'data: {}';

      return {
        event: eventLine.slice(6).trim(),
        data: JSON.parse(dataLine.slice(5).trim()) as Record<string, unknown>,
      };
    });
}

function getServerBaseUrl(): string {
  return window.jarvisDesktop?.getServerBaseUrl() ?? 'http://127.0.0.1:8001';
}

export async function streamChat(
  query: string,
  onEvent: (event: string, data: Record<string, unknown>) => void,
  sessionId?: string,
) {
  const searchParams = new URLSearchParams({ query });
  if (sessionId) {
    searchParams.set('session_id', sessionId);
  }

  const response = await fetch(`${getServerBaseUrl()}/api/chat?${searchParams}`, {
    headers: { Accept: 'text/event-stream' },
  });

  if (!response.ok) {
    throw new Error(`Jarvis request failed with status ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Jarvis stream reader is unavailable');
  }

  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    const parts = buffer.split(/\r?\n\r?\n+/);
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      for (const entry of parseEventBlocks(`${part}\n\n`)) {
        onEvent(entry.event, entry.data);
      }
    }

    if (done) {
      break;
    }
  }

  if (buffer.trim()) {
    for (const entry of parseEventBlocks(buffer)) {
      onEvent(entry.event, entry.data);
    }
  }
}
