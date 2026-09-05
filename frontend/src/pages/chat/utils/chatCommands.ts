import { Setter } from 'solid-js';
import {
  DiscoveryQuestionnaireArtifactInput,
  Message,
  SessionHandoffArtifactInput,
  WorkspaceArtifact,
  WorkspaceNote,
} from '../../../types';

type ToastLike = {
  error: (message: string, duration?: number) => void;
  success: (message: string, duration?: number) => void;
};

type HandleChatCommandArgs = {
  trimmedInput: string;
  setMessages: Setter<Message[]>;
  setInput: (value: string) => void;
  submitText: (value: string, overrides?: Record<string, unknown>) => Promise<void> | void;
  saveLastAssistantAsWorkspaceNote: () => Promise<WorkspaceNote | null>;
  saveLastAssistantAsResearchArtifact: () => Promise<void>;
  saveSessionHandoffArtifact: (handoff: SessionHandoffArtifactInput) => Promise<void>;
  saveDiscoveryQuestionnaireArtifact: (questionnaire: DiscoveryQuestionnaireArtifactInput) => Promise<void>;
  messages: Message[];
  workspaceArtifacts: WorkspaceArtifact[];
  toast: ToastLike;
};

const CLARIFY_COMMAND = '/clarify';
const HANDOFF_COMMAND = '/handoff';
const QUESTIONNAIRE_COMMAND = '/questionnaire';

export const parseClarifyModeTask = (trimmedInput: string): string | null => {
  if (trimmedInput === CLARIFY_COMMAND) return '';
  if (trimmedInput.startsWith(`${CLARIFY_COMMAND} `)) {
    return trimmedInput.slice(CLARIFY_COMMAND.length).trim();
  }

  const naturalTriggers = [
    'clarify this:',
    'clarify this request:',
    'help me shape this:',
  ];
  const lower = trimmedInput.toLowerCase();
  for (const trigger of naturalTriggers) {
    if (lower.startsWith(trigger)) {
      return trimmedInput.slice(trigger.length).trim();
    }
  }

  return null;
};

export const buildClarifyModePrompt = (task: string): string => {
  const normalizedTask = task.trim();
  return [
    'Clarify Mode',
    '',
    'User request to clarify:',
    normalizedTask,
    '',
    'Ask one round of only the highest-impact questions before doing any implementation, research, writing, or external action.',
    '',
    'For each question, include:',
    '- Why this decision changes the outcome',
    '- Recommended answer',
    '- User-approved decision: pending',
    '',
    'Use this exact response format:',
    '',
    '## Clarifying Questions',
    '',
    '1. Question:',
    '   Why it matters:',
    '   Recommended answer:',
    '   User-approved decision: pending',
    '',
    '## Decision Brief',
    '',
    'Confirmed facts:',
    'Recommended defaults:',
    'Assumptions:',
    'Open questions:',
    'Next workbench mode:',
    'Follow-up handoff text:',
    '',
    'Do not execute the task yet. Do not treat recommended answers as user-approved decisions.',
  ].join('\n');
};

const buildClarifyUsageMessage = (): Message => ({
  role: 'assistant',
  content: 'Use `/clarify <task>` to ask Yue for one focused decision round and a decision brief before it acts.',
  timestamp: new Date().toISOString(),
});

const buildQuestionnaireUsageMessage = (): Message => ({
  role: 'assistant',
  content: [
    'Use `/questionnaire <human information gap>` to save a stakeholder questionnaire.',
    '',
    'Include the recipient, objective, and what Yue needs to learn.',
  ].join('\n'),
  timestamp: new Date().toISOString(),
});

const normalizeForLine = (value: string, fallback = 'None captured yet.'): string => {
  const trimmed = value.replace(/\s+/g, ' ').trim();
  if (!trimmed) return fallback;
  return trimmed.length > 220 ? `${trimmed.slice(0, 217)}...` : trimmed;
};

export const redactSessionHandoffText = (value: string): string =>
  value
    .replace(/\b(sk-[A-Za-z0-9_-]{12,})\b/g, '[REDACTED_OPENAI_KEY]')
    .replace(/\b(gh[pousr]_[A-Za-z0-9_]{20,})\b/g, '[REDACTED_GITHUB_TOKEN]')
    .replace(/\b(xox[baprs]-[A-Za-z0-9-]{12,})\b/g, '[REDACTED_SLACK_TOKEN]')
    .replace(/\b(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}/gi, '$1[REDACTED_TOKEN]')
    .replace(/\b(api[_-]?key|password|passwd|secret|token)\s*[:=]\s*["']?[^"'\s,;]+/gi, '$1=[REDACTED]')
    .replace(/\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/g, '[REDACTED_JWT]');

const redact = (value: string): string => redactSessionHandoffText(value);

const summarizeMessages = (messages: Message[], role: string, limit: number): string[] =>
  messages
    .filter((message) => message.role === role && message.content?.trim())
    .slice(-limit)
    .map((message) => normalizeForLine(redact(message.content)));

const extractMatchingLines = (messages: Message[], patterns: RegExp[], limit: number): string[] => {
  const lines = messages
    .flatMap((message) => message.content.split(/\n+/))
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => patterns.some((pattern) => pattern.test(line)))
    .map((line) => normalizeForLine(redact(line)));
  return [...new Set(lines)].slice(-limit);
};

const latestNumericMessageId = (messages: Message[]): number | null => {
  const message = [...messages].reverse().find((entry) => typeof entry.id === 'number');
  return typeof message?.id === 'number' ? message.id : null;
};

const EARLY_WORKBENCH_ARTIFACT_TYPES = new Set([
  'clarify_decision_brief',
  'decision_brief',
  'session_handoff',
  'discovery_questionnaire',
]);

const relatedWorkbenchArtifacts = (artifacts: WorkspaceArtifact[]): WorkspaceArtifact[] =>
  artifacts
    .filter((artifact) => EARLY_WORKBENCH_ARTIFACT_TYPES.has(artifact.artifact_type))
    .slice(0, 8);

const artifactReferences = (artifacts: WorkspaceArtifact[]): Record<string, unknown>[] =>
  relatedWorkbenchArtifacts(artifacts).map((artifact) => ({
    id: artifact.id,
    type: artifact.artifact_type,
    title: artifact.title,
    content_ref: artifact.content_ref || null,
    source_session_id: artifact.source_session_id || null,
    source_message_id: artifact.source_message_id || null,
  }));

const formatArtifactReferences = (artifacts: WorkspaceArtifact[]): string => {
  const refs = relatedWorkbenchArtifacts(artifacts);
  if (!refs.length) return '- No related early workbench artifacts linked yet.';
  return refs
    .map((artifact) =>
      `- ${artifact.title} (${artifact.artifact_type}, id: ${artifact.id}${
        artifact.content_ref ? `, ref: ${artifact.content_ref}` : ''
      })`,
    )
    .join('\n');
};

export const buildSessionHandoffArtifact = (
  messages: Message[],
  workspaceArtifacts: WorkspaceArtifact[] = [],
  generatedAt = new Date(),
): SessionHandoffArtifactInput => {
  const includedMessages = messages.filter((message) => message.content?.trim());
  const sourceMessageIds = includedMessages
    .map((message) => message.id)
    .filter((id): id is number | string => id !== undefined);
  const firstUserRequest =
    includedMessages.find((message) => message.role === 'user')?.content ||
    'Current Yue workbench session';
  const objective = normalizeForLine(redact(firstUserRequest), 'No explicit objective captured.');
  const userRequests = summarizeMessages(includedMessages, 'user', 4);
  const assistantUpdates = summarizeMessages(includedMessages, 'assistant', 4);
  const decisions = extractMatchingLines(
    includedMessages,
    [/\bdecid(?:e|ed|ing|es)\b/i, /\bdecision\b/i, /\bapproved\b/i, /\bchose\b/i],
    8,
  );
  const blockers = extractMatchingLines(
    includedMessages,
    [/\bblock(?:ed|er|ing)?\b/i, /\bfail(?:ed|ure|ing)?\b/i, /\berror\b/i, /\bmissing\b/i],
    8,
  );
  const openQuestions = extractMatchingLines(includedMessages, [/\?$/], 8);
  const citations = includedMessages.flatMap((message) => message.citations || []);
  const chartArtifacts = includedMessages.flatMap((message) => message.chart_artifacts || []);
  const generatedAtIso = generatedAt.toISOString();
  const title = `Session handoff - ${generatedAtIso.slice(0, 10)}`;

  const section = (items: string[], fallback = 'None captured yet.') =>
    items.length ? items.map((item) => `- ${item}`).join('\n') : `- ${fallback}`;

  const markdown = [
    '# Session Handoff',
    '',
    `Generated: ${generatedAtIso}`,
    'Mode: Session Handoff',
    'Privacy: Sensitive tokens, passwords, API keys, and bearer credentials were redacted before saving.',
    '',
    '## Objective',
    `- ${objective}`,
    '',
    '## Current State',
    section(assistantUpdates, 'No assistant progress captured yet.'),
    '',
    '## Completed Work',
    section(assistantUpdates, 'No completed work captured yet.'),
    '',
    '## Decisions',
    section(decisions),
    '',
    '## Assumptions',
    '- Any uncited summary line is inferred from the chat transcript and should be verified before high-impact action.',
    '',
    '## Sources',
    citations.length
      ? citations.map((citation, index) => `- Source ${index + 1}: ${normalizeForLine(redact(JSON.stringify(citation)))}`).join('\n')
      : '- No citations captured in this chat.',
    '',
    '## Artifacts',
    chartArtifacts.length
      ? chartArtifacts.map((artifact, index) => `- Artifact ${index + 1}: ${normalizeForLine(redact(JSON.stringify(artifact)))}`).join('\n')
      : '- No generated artifacts captured in this chat.',
    '',
    '## Related Workspace Artifacts',
    formatArtifactReferences(workspaceArtifacts),
    '',
    '## Blockers',
    section(blockers),
    '',
    '## Open Questions',
    section(openQuestions),
    '',
    '## Proposed Next Actions',
    section(userRequests, 'Review this handoff, then continue from the continuation prompt.'),
    '',
    '## Continuation Prompt',
    'Continue this Yue workbench session from the handoff artifact. Start by confirming current state, decisions, blockers, and open questions, then proceed with the next proposed action. Do not assume proposed next steps are approved if the user has not confirmed them.',
  ].join('\n');

  return {
    title,
    markdown,
    source_message_ids: sourceMessageIds,
    latest_source_message_id: latestNumericMessageId(includedMessages),
    artifact_metadata: {
      mode: 'session_handoff',
      generated_at: generatedAtIso,
      content: markdown,
      sections: [
        'objective',
        'current_state',
        'completed_work',
        'decisions',
        'assumptions',
        'sources',
        'artifacts',
        'related_workspace_artifacts',
        'blockers',
        'open_questions',
        'proposed_next_actions',
        'continuation_prompt',
      ],
      redaction_policy: {
        applied: true,
        redacts: ['api keys', 'passwords', 'secrets', 'tokens', 'bearer credentials', 'JWTs'],
      },
      source_message_ids: sourceMessageIds,
      related_artifacts: artifactReferences(workspaceArtifacts),
      no_external_side_effects: true,
    },
  };
};

export const parseDiscoveryQuestionnaireGap = (trimmedInput: string): string | null => {
  if (trimmedInput === QUESTIONNAIRE_COMMAND) return '';
  if (trimmedInput.startsWith(`${QUESTIONNAIRE_COMMAND} `)) {
    return trimmedInput.slice(QUESTIONNAIRE_COMMAND.length).trim();
  }

  const naturalTriggers = [
    'make questions for the stakeholder:',
    'make a questionnaire for:',
    'we need to ask the pm:',
    'we need to ask the stakeholder:',
  ];
  const lower = trimmedInput.toLowerCase();
  for (const trigger of naturalTriggers) {
    if (lower.startsWith(trigger)) {
      return trimmedInput.slice(trigger.length).trim();
    }
  }

  return null;
};

const inferRecipient = (gap: string): string => {
  const match = gap.match(/\b(?:for|ask|from)\s+(the\s+)?([A-Za-z][A-Za-z0-9 _-]{1,40})/i);
  return normalizeForLine(redact(match?.[2] || 'Stakeholder or decision owner'));
};

export const buildDiscoveryQuestionnaireArtifact = (
  gap: string,
  messages: Message[],
  workspaceArtifacts: WorkspaceArtifact[] = [],
  generatedAt = new Date(),
): DiscoveryQuestionnaireArtifactInput => {
  const normalizedGap = normalizeForLine(redact(gap), 'Unspecified human information gap.');
  const includedMessages = messages.filter((message) => message.content?.trim());
  const sourceMessageIds = includedMessages
    .map((message) => message.id)
    .filter((id): id is number | string => id !== undefined);
  const recentContext = [
    ...summarizeMessages(includedMessages, 'user', 2),
    ...summarizeMessages(includedMessages, 'assistant', 2),
  ].slice(-4);
  const generatedAtIso = generatedAt.toISOString();
  const title = `Discovery questionnaire - ${generatedAtIso.slice(0, 10)}`;
  const recipient = inferRecipient(gap);
  const section = (items: string[], fallback = 'None captured yet.') =>
    items.length ? items.map((item) => `- ${item}`).join('\n') : `- ${fallback}`;

  const factQuestions = [
    `What facts, constraints, or source-of-truth details should Yue know about: ${normalizedGap}?`,
    'Which existing documents, dashboards, systems, or people should be treated as authoritative?',
    'Are there deadlines, budgets, compliance requirements, or operational constraints Yue must respect?',
  ];
  const decisionQuestions = [
    'What decision do you want Yue to optimize for if tradeoffs appear?',
    'Which option or direction is already preferred, and what would change that preference?',
    'Who needs to approve the next step before Yue acts beyond drafting or analysis?',
  ];

  const markdown = [
    '# Discovery Questionnaire',
    '',
    `Generated: ${generatedAtIso}`,
    'Mode: Discovery Questionnaire',
    'Delivery: Not sent externally. Review and send only after explicit user approval.',
    '',
    '## Recipient',
    `- ${recipient}`,
    '',
    '## Objective',
    `- Fill this human information gap: ${normalizedGap}`,
    '',
    '## Context For Recipient',
    section(recentContext, 'No additional chat context captured.'),
    '',
    '## Related Workspace Artifacts',
    formatArtifactReferences(workspaceArtifacts),
    '',
    '## Fact Questions',
    ...factQuestions.map((question, index) => [
      `${index + 1}. ${question}`,
      '   Answer:',
      '   Source or confidence:',
    ].join('\n')),
    '',
    '## Decision Or Preference Questions',
    ...decisionQuestions.map((question, index) => [
      `${index + 1}. ${question}`,
      '   Answer:',
      '   Decision owner:',
    ].join('\n')),
    '',
    '## Answer Stubs',
    '- Facts confirmed:',
    '- Decisions or preferences confirmed:',
    '- Remaining unknowns:',
    '- Follow-up needed:',
    '',
    '## Safety Notes',
    '- Avoid sharing unnecessary sensitive personal data.',
    '- Do not treat returned answers as durable workspace facts until a user reviews and confirms them.',
    '- Do not send this questionnaire through email, chat, tickets, forms, or other connectors without explicit approval.',
  ].join('\n');

  return {
    title,
    markdown,
    information_gap: normalizedGap,
    source_message_ids: sourceMessageIds,
    latest_source_message_id: latestNumericMessageId(includedMessages),
    artifact_metadata: {
      mode: 'discovery_questionnaire',
      generated_at: generatedAtIso,
      content: markdown,
      information_gap: normalizedGap,
      recipient,
      question_classes: ['fact', 'decision_or_preference'],
      source_message_ids: sourceMessageIds,
      related_artifacts: artifactReferences(workspaceArtifacts),
      no_external_side_effects: true,
      requires_user_approval_before_send: true,
    },
  };
};

export const handleChatCommand = ({
  trimmedInput,
  setMessages,
  setInput,
  submitText,
  saveLastAssistantAsWorkspaceNote,
  saveLastAssistantAsResearchArtifact,
  saveSessionHandoffArtifact,
  saveDiscoveryQuestionnaireArtifact,
  messages,
  workspaceArtifacts,
  toast,
}: HandleChatCommandArgs): boolean => {
  if (trimmedInput === '/help') {
    const helpMsg: Message = {
      role: 'assistant',
      content: 'Commands: /help /clarify /handoff /questionnaire /note /research /clear',
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, helpMsg]);
    setInput('');
    return true;
  }

  if (trimmedInput === '/clear') {
    setMessages([]);
    setInput('');
    return true;
  }

  const clarifyTask = parseClarifyModeTask(trimmedInput);
  if (clarifyTask !== null) {
    const task = clarifyTask.trim();
    if (!task) {
      setMessages((prev) => [...prev, buildClarifyUsageMessage()]);
      setInput('');
      return true;
    }

    void submitText(buildClarifyModePrompt(task));
    setInput('');
    return true;
  }

  if (trimmedInput === HANDOFF_COMMAND || trimmedInput.startsWith(`${HANDOFF_COMMAND} `)) {
    const handoff = buildSessionHandoffArtifact(messages, workspaceArtifacts);
    saveSessionHandoffArtifact(handoff)
      .then(() => toast.success('Saved session handoff artifact.', 3000))
      .catch((err) => {
        console.error('Failed to save session handoff', err);
        toast.error('Failed to save session handoff.', 3000);
      });
    setInput('');
    return true;
  }

  const questionnaireGap = parseDiscoveryQuestionnaireGap(trimmedInput);
  if (questionnaireGap !== null) {
    const gap = questionnaireGap.trim();
    if (!gap) {
      setMessages((prev) => [...prev, buildQuestionnaireUsageMessage()]);
      setInput('');
      return true;
    }

    const questionnaire = buildDiscoveryQuestionnaireArtifact(gap, messages, workspaceArtifacts);
    saveDiscoveryQuestionnaireArtifact(questionnaire)
      .then(() => toast.success('Saved discovery questionnaire artifact.', 3000))
      .catch((err) => {
        console.error('Failed to save discovery questionnaire', err);
        toast.error('Failed to save discovery questionnaire.', 3000);
      });
    setInput('');
    return true;
  }

  if (trimmedInput === '/note') {
    saveLastAssistantAsWorkspaceNote()
      .then((note) =>
        toast.success(note?.title ? `Saved note: ${note.title}` : 'Saved to workspace notes.', 3000),
      )
      .catch((err) => {
        console.error('Failed to save workspace note', err);
        toast.error('Failed to save workspace note.', 3000);
      });
    setInput('');
    return true;
  }

  if (trimmedInput === '/research') {
    saveLastAssistantAsResearchArtifact()
      .then(() => toast.success('Saved as research artifact.', 3000))
      .catch((err) => {
        console.error('Failed to save research artifact', err);
        toast.error('Failed to save research artifact.', 3000);
      });
    setInput('');
    return true;
  }

  return false;
};
