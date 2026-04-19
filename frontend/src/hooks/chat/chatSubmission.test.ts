import { describe, expect, it, vi } from 'vitest';
import { submitChatText, uploadAttachments } from './chatSubmission';
import { Attachment, Message } from '../../types';

const makeFile = (name: string, type: string, content = 'x'): File => new File([content], name, { type });

describe('chatSubmission attachments', () => {
  it('uploads files via /api/files and returns attachments', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          files: [{ id: 'att_1', kind: 'file', display_name: 'report.pdf', mime_type: 'application/pdf' }],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const attachments = await uploadAttachments([makeFile('report.pdf', 'application/pdf')], fetchMock);
    expect(fetchMock).toHaveBeenCalledWith('/api/files', expect.objectContaining({ method: 'POST' }));
    expect(attachments).toHaveLength(1);
    expect(attachments[0].id).toBe('att_1');
  });

  it('surfaces upload validation error on /api/files failure', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: {
            code: 'file_too_large',
            message: 'file_too_large',
            max_file_size_bytes: 8 * 1024 * 1024,
          },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    await expect(uploadAttachments([makeFile('big.pdf', 'application/pdf')], fetchMock)).rejects.toThrow(
      '附件上传失败：文件超过大小限制（8MB）',
    );
  });

  it('surfaces too-many-files error with backend max count', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: {
            code: 'too_many_files',
            message: 'too_many_files',
            max_files: 6,
          },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    await expect(uploadAttachments([makeFile('a.pdf', 'application/pdf')], fetchMock)).rejects.toThrow(
      '附件上传失败：单次最多上传 6 个文件',
    );
  });

  it('submits attachments after upload and keeps legacy images for vision compatibility', async () => {
    const calls: Array<{ url: string; body?: any }> = [];
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, body: init?.body });
      if (url === '/api/files') {
        return new Response(
          JSON.stringify({
            files: [
              {
                id: 'att_img',
                kind: 'file',
                display_name: 'screen.png',
                mime_type: 'image/png',
                url: '/files/chat/att_img.png',
                size_bytes: 12,
              },
              {
                id: 'att_pdf',
                kind: 'file',
                display_name: 'report.pdf',
                mime_type: 'application/pdf',
                url: '/files/chat/att_pdf.pdf',
                size_bytes: 24,
              },
            ] satisfies Attachment[],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      return new Response('', { status: 200 });
    });

    const messagesState: Message[] = [];
    const setMessages = (value: Message[] | ((prev: Message[]) => Message[])) => {
      if (typeof value === 'function') {
        messagesState.splice(0, messagesState.length, ...(value(messagesState) as Message[]));
      } else {
        messagesState.splice(0, messagesState.length, ...value);
      }
      return undefined;
    };

    await submitChatText({
      rawText: '请分析附件',
      currentImages: [
        makeFile('screen.png', 'image/png', 'image'),
        makeFile('report.pdf', 'application/pdf', 'pdf'),
      ],
      messages: () => messagesState,
      currentChatId: () => null,
      selectedProvider: () => 'openai',
      selectedModel: () => 'gpt-4o',
      selectedAgent: () => null,
      requestedSkill: () => null,
      isDeepThinking: () => false,
      setMessages,
      setInput: () => undefined,
      setImageAttachments: () => undefined,
      setIsTyping: () => undefined,
      setLastGenerationOutcome: () => undefined,
      setActiveSkill: () => undefined,
      setElapsedTime: () => undefined,
      setCurrentChatId: () => undefined,
      setActionStates: () => undefined,
      setShowLLMSelector: () => undefined,
      refreshChatMeta: async () => false,
      scheduleMetaRefreshForTitle: () => undefined,
      toast: {
        error: () => undefined,
        warning: () => undefined,
      },
      fileToBase64: async (file: File) => `data:${file.type};base64,AAA`,
      setAbortController: () => undefined,
      setTimerInterval: () => undefined,
      getTimerInterval: () => null,
      fetchImpl: fetchMock,
    });

    expect(calls.map((item) => item.url)).toEqual(['/api/files', '/api/chat/stream']);
    const streamPayload = JSON.parse(String(calls[1].body));
    expect(streamPayload.attachments).toHaveLength(2);
    expect(streamPayload.images).toEqual(['data:image/png;base64,AAA']);
  });
});
