import { describe, expect, it } from 'vitest';

import { parseEventBlocks } from './chat-client';

describe('parseEventBlocks', () => {
  it('parses session, text, and done events from an SSE buffer', () => {
    const blocks = parseEventBlocks(
      'event: session\ndata: {"session_id":"abc"}\n\n' +
        'event: text\ndata: {"text":"hello"}\n\n' +
        'event: done\ndata: {"session_id":"abc"}\n\n'
    );

    expect(blocks).toEqual([
      { event: 'session', data: { session_id: 'abc' } },
      { event: 'text', data: { text: 'hello' } },
      { event: 'done', data: { session_id: 'abc' } },
    ]);
  });

  it('parses CRLF-separated SSE events', () => {
    const blocks = parseEventBlocks(
      'event: text\r\ndata: {"text":"hello"}\r\n\r\n' +
        'event: done\r\ndata: {"session_id":"abc"}\r\n\r\n'
    );

    expect(blocks).toEqual([
      { event: 'text', data: { text: 'hello' } },
      { event: 'done', data: { session_id: 'abc' } },
    ]);
  });
});
