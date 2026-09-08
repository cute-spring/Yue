import { For, Show, createEffect, createMemo, onCleanup, onMount } from 'solid-js';
import { useSearchParams } from '@solidjs/router';

// PROTOTYPE: Three variants of Workspace Understanding, switchable via ?variant=,
// on a throwaway /workspace-understanding-prototype route.

type VariantKey = 'A' | 'B' | 'C';

type UnderstandingGroup = {
  key: string;
  label: string;
  count: number;
  pending?: number;
  items: string[];
};

type MemoryPrompt = {
  title: string;
  body: string;
  destination: 'About You' | 'This Workspace';
};

const variants: Array<{ key: VariantKey; name: string }> = [
  { key: 'A', name: 'Understanding Overview' },
  { key: 'B', name: 'Two-Layer Context' },
  { key: 'C', name: 'Conversation-First' },
];

const groups: UnderstandingGroup[] = [
  {
    key: 'background',
    label: 'Background',
    count: 3,
    items: ['Yue is a trusted AI workbench for agents, tools, skills, and chat.', 'Workspace should reduce repeated context-setting.'],
  },
  {
    key: 'goals',
    label: 'Goals',
    count: 2,
    items: ['Make Yue feel smarter the more it is used.', 'Let returning users restart without re-explaining basics.'],
  },
  {
    key: 'decisions',
    label: 'Decisions',
    count: 4,
    pending: 1,
    items: ['Workspace first screen should show understanding, not resource lists.', 'Use fixed groups rather than scenario-adaptive layouts.'],
  },
  {
    key: 'constraints',
    label: 'Constraints',
    count: 3,
    items: ['Durable memory requires explicit confirmation.', 'Do not mix user-level memory into workspace-level memory.'],
  },
  {
    key: 'preferences',
    label: 'Preferences',
    count: 2,
    items: ['Prefer simple, predictable IA over clever adaptation.', 'Inline confirmations should not interrupt the task.'],
  },
  {
    key: 'terms',
    label: 'Terms',
    count: 8,
    items: ['Yue Understanding = About You + About This Workspace.', 'Memory Candidate = proposed durable understanding awaiting confirmation.'],
  },
  {
    key: 'open_questions',
    label: 'Open Questions',
    count: 2,
    pending: 2,
    items: ['Should high-signal detection start rule-based or LLM-assisted?', 'Where should global About You management live?'],
  },
  {
    key: 'current_state',
    label: 'Current State',
    count: 3,
    items: ['Product and technical specs are drafted.', 'Next likely implementation starts with /understanding summary API.'],
  },
];

const appliedUserMemory = [
  'Default to Chinese when the user asks in Chinese.',
  'Start with the conclusion, then expand.',
  'Prefer concrete, implementation-ready product design.',
];

const sources = [
  { name: 'Workspace Understanding Product Spec', state: 'Ready' },
  { name: 'Technical Plan', state: 'Ready' },
  { name: 'Earlier chat notes', state: 'Needs review' },
];

const memoryPrompt: MemoryPrompt = {
  title: 'Remember this preference?',
  body: 'Use simple, fixed Workspace Understanding groups instead of adapting labels by scenario.',
  destination: 'This Workspace',
};

const cx = (...parts: Array<string | false | undefined>) => parts.filter(Boolean).join(' ');

function Badge(props: { children: any; tone?: 'green' | 'blue' | 'amber' | 'slate' }) {
  const tone = () => props.tone || 'slate';
  return (
    <span
      class={cx(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold',
        tone() === 'green' && 'border-emerald-200 bg-emerald-50 text-emerald-700',
        tone() === 'blue' && 'border-blue-200 bg-blue-50 text-blue-700',
        tone() === 'amber' && 'border-amber-200 bg-amber-50 text-amber-700',
        tone() === 'slate' && 'border-slate-200 bg-slate-50 text-slate-600',
      )}
    >
      {props.children}
    </span>
  );
}

function PrototypeShell(props: { title: string; subtitle: string; children: any }) {
  return (
    <div class="min-h-full overflow-y-auto bg-[#f7f8fa] text-slate-950">
      <div class="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-5 pb-28 pt-5 lg:px-8">
        <div class="mb-5 flex flex-col justify-between gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-end">
          <div>
            <div class="text-[11px] font-black uppercase tracking-[0.2em] text-emerald-600">Prototype</div>
            <h1 class="mt-2 text-2xl font-black tracking-normal text-slate-950 lg:text-3xl">{props.title}</h1>
            <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{props.subtitle}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <Badge tone="green">About This Workspace</Badge>
            <Badge tone="blue">Also using About You</Badge>
            <Badge tone="amber">2 pending confirmations</Badge>
          </div>
        </div>
        {props.children}
      </div>
    </div>
  );
}

function GroupCard(props: { group: UnderstandingGroup; compact?: boolean }) {
  return (
    <section class="min-h-[154px] rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="text-sm font-black text-slate-900">{props.group.label}</h2>
          <div class="mt-1 flex flex-wrap gap-1.5">
            <Badge>{props.group.count} saved</Badge>
            <Show when={props.group.pending}>
              <Badge tone="amber">{props.group.pending} pending</Badge>
            </Show>
          </div>
        </div>
        <button class="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-bold text-slate-600 hover:bg-slate-50">
          Review
        </button>
      </div>
      <div class="mt-4 space-y-2">
        <For each={props.compact ? props.group.items.slice(0, 1) : props.group.items}>
          {(item) => <p class="text-[13px] leading-5 text-slate-700">{item}</p>}
        </For>
      </div>
    </section>
  );
}

function AppliedUserMemoryPanel() {
  return (
    <section class="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="text-sm font-black text-blue-950">Also using About You</h2>
          <p class="mt-1 text-xs leading-5 text-blue-800">Cross-workspace preferences influencing this workspace chat.</p>
        </div>
        <button class="rounded-md border border-blue-200 bg-white px-2.5 py-1 text-xs font-bold text-blue-700">
          Manage
        </button>
      </div>
      <div class="mt-3 space-y-2">
        <For each={appliedUserMemory}>
          {(item) => (
            <div class="rounded-md border border-blue-100 bg-white px-3 py-2 text-[13px] leading-5 text-slate-700">
              {item}
            </div>
          )}
        </For>
      </div>
    </section>
  );
}

function MemoryConfirmationCard(props: { prompt: MemoryPrompt; roomy?: boolean }) {
  return (
    <section class="rounded-lg border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="min-w-0">
          <div class="text-sm font-black text-emerald-950">{props.prompt.title}</div>
          <p class="mt-1 text-[13px] leading-5 text-emerald-900">{props.prompt.body}</p>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <span class="text-xs font-semibold text-emerald-800">Save to</span>
            <select class="rounded-md border border-emerald-200 bg-white px-2 py-1 text-xs font-bold text-slate-700">
              <option>{props.prompt.destination}</option>
              <option>About You</option>
              <option>This Workspace</option>
            </select>
          </div>
        </div>
        <div class={cx('flex shrink-0 gap-2', props.roomy ? 'lg:flex-row' : 'lg:flex-col')}>
          <button class="rounded-md bg-emerald-600 px-3 py-2 text-xs font-black text-white shadow-sm">Remember</button>
          <button class="rounded-md border border-emerald-200 bg-white px-3 py-2 text-xs font-bold text-emerald-800">Just this time</button>
          <button class="rounded-md border border-emerald-200 bg-white px-3 py-2 text-xs font-bold text-emerald-800">Edit</button>
        </div>
      </div>
    </section>
  );
}

function VariantA() {
  return (
    <PrototypeShell
      title="Workspace Understanding"
      subtitle="A fixed eight-group overview that answers: what does Yue already understand about this workspace?"
    >
      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
        <main>
          <div class="mb-4 grid gap-3 sm:grid-cols-4">
            <div class="rounded-lg border border-slate-200 bg-white p-4">
              <div class="text-2xl font-black">27</div>
              <div class="mt-1 text-xs font-semibold text-slate-500">saved understanding items</div>
            </div>
            <div class="rounded-lg border border-slate-200 bg-white p-4">
              <div class="text-2xl font-black">2</div>
              <div class="mt-1 text-xs font-semibold text-slate-500">pending confirmations</div>
            </div>
            <div class="rounded-lg border border-slate-200 bg-white p-4">
              <div class="text-2xl font-black">3</div>
              <div class="mt-1 text-xs font-semibold text-slate-500">ready sources</div>
            </div>
            <div class="rounded-lg border border-slate-200 bg-white p-4">
              <div class="text-2xl font-black">8</div>
              <div class="mt-1 text-xs font-semibold text-slate-500">fixed groups</div>
            </div>
          </div>
          <div class="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
            <For each={groups}>{(group) => <GroupCard group={group} />}</For>
          </div>
        </main>
        <aside class="space-y-4">
          <AppliedUserMemoryPanel />
          <MemoryConfirmationCard prompt={memoryPrompt} />
          <section class="rounded-lg border border-slate-200 bg-white p-4">
            <h2 class="text-sm font-black text-slate-900">Secondary workspace materials</h2>
            <div class="mt-3 space-y-2">
              <For each={sources}>
                {(source) => (
                  <div class="flex items-center justify-between gap-3 rounded-md border border-slate-100 px-3 py-2">
                    <span class="truncate text-[13px] font-semibold text-slate-700">{source.name}</span>
                    <Badge tone={source.state === 'Ready' ? 'green' : 'amber'}>{source.state}</Badge>
                  </div>
                )}
              </For>
            </div>
          </section>
        </aside>
      </div>
    </PrototypeShell>
  );
}

function VariantB() {
  return (
    <PrototypeShell
      title="Yue Understanding"
      subtitle="A more explicit two-layer layout: About You stays visible, while About This Workspace gets the main canvas."
    >
      <div class="grid min-h-[calc(100vh-150px)] gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div class="text-[11px] font-black uppercase tracking-[0.18em] text-blue-600">About You</div>
          <h2 class="mt-2 text-lg font-black text-slate-950">Applied preferences</h2>
          <div class="mt-4 space-y-2">
            <For each={appliedUserMemory}>
              {(item) => <div class="rounded-md bg-blue-50 px-3 py-2 text-[13px] leading-5 text-blue-950">{item}</div>}
            </For>
          </div>
          <div class="mt-5 border-t border-slate-200 pt-4">
            <div class="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">Capture policy</div>
            <p class="mt-2 text-[13px] leading-5 text-slate-600">Only high-signal preferences, corrections, decisions, terms, and long-lived constraints become candidates.</p>
          </div>
        </aside>
        <main class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex flex-col justify-between gap-4 border-b border-slate-200 pb-4 lg:flex-row lg:items-center">
            <div>
              <div class="text-[11px] font-black uppercase tracking-[0.18em] text-emerald-600">About This Workspace</div>
              <h2 class="mt-2 text-xl font-black text-slate-950">Yue Workspace redesign</h2>
            </div>
            <div class="flex gap-2">
              <button class="rounded-md border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700">Sources</button>
              <button class="rounded-md border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700">Notes</button>
              <button class="rounded-md border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700">Artifacts</button>
            </div>
          </div>
          <div class="mt-5 grid gap-3 md:grid-cols-2">
            <For each={groups}>{(group) => <GroupCard group={group} compact />}</For>
          </div>
          <div class="mt-5">
            <MemoryConfirmationCard prompt={memoryPrompt} roomy />
          </div>
        </main>
      </div>
    </PrototypeShell>
  );
}

function ChatBubble(props: { role: 'user' | 'assistant'; children: any }) {
  return (
    <div class={cx('max-w-[760px] rounded-lg border px-4 py-3 text-sm leading-6', props.role === 'user' ? 'ml-auto border-slate-200 bg-white text-slate-800' : 'border-emerald-200 bg-emerald-50 text-emerald-950')}>
      {props.children}
    </div>
  );
}

function VariantC() {
  return (
    <PrototypeShell
      title="Conversation-First Workspace"
      subtitle="A chat-adjacent design where the understanding summary sits beside the work, and memory confirmation appears inline."
    >
      <div class="grid min-h-[calc(100vh-150px)] gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <main class="flex min-h-[560px] flex-col rounded-lg border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-5 py-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 class="text-lg font-black text-slate-950">Yue Workspace redesign</h2>
                <p class="mt-1 text-xs text-slate-500">3 sources ready - 27 understanding items - 2 pending confirmations</p>
              </div>
              <button class="rounded-md bg-emerald-600 px-3 py-2 text-xs font-black text-white">Ask with this workspace</button>
            </div>
          </div>
          <div class="flex-1 space-y-4 overflow-y-auto p-5">
            <ChatBubble role="user">Workspace 不要按场景自适应，保持简单简洁。</ChatBubble>
            <ChatBubble role="assistant">
              认同。第一版应该保持固定 8 组，让用户知道每类背景和约束放在哪里，而不是依赖系统推断改变结构。
            </ChatBubble>
            <MemoryConfirmationCard prompt={memoryPrompt} roomy />
            <ChatBubble role="user">下一步先做可视化原型。</ChatBubble>
          </div>
        </main>
        <aside class="space-y-4">
          <AppliedUserMemoryPanel />
          <section class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-sm font-black text-slate-900">Workspace Understanding</h2>
              <button class="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-bold text-slate-600">Open</button>
            </div>
            <div class="mt-3 space-y-2">
              <For each={groups}>
                {(group) => (
                  <div class="rounded-md border border-slate-100 px-3 py-2">
                    <div class="flex items-center justify-between gap-2">
                      <span class="text-[13px] font-black text-slate-800">{group.label}</span>
                      <span class="text-xs font-bold text-slate-500">{group.count}</span>
                    </div>
                    <p class="mt-1 truncate text-xs text-slate-500">{group.items[0]}</p>
                  </div>
                )}
              </For>
            </div>
          </section>
        </aside>
      </div>
    </PrototypeShell>
  );
}

function PrototypeSwitcher(props: { current: VariantKey; onChange: (variant: VariantKey) => void }) {
  const currentIndex = createMemo(() => Math.max(0, variants.findIndex((item) => item.key === props.current)));
  const currentVariant = createMemo(() => variants[currentIndex()]);

  const move = (step: number) => {
    const next = (currentIndex() + step + variants.length) % variants.length;
    props.onChange(variants[next].key);
  };

  onMount(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || target?.isContentEditable) return;
      if (event.key === 'ArrowLeft') move(-1);
      if (event.key === 'ArrowRight') move(1);
    };
    window.addEventListener('keydown', handler);
    onCleanup(() => window.removeEventListener('keydown', handler));
  });

  return (
    <div class="fixed bottom-5 left-1/2 z-[80] flex -translate-x-1/2 items-center gap-2 rounded-full border border-slate-900 bg-slate-950 px-2 py-2 text-white shadow-2xl">
      <button class="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-lg font-black hover:bg-white/20" onClick={() => move(-1)} title="Previous variant">
        <span aria-hidden="true">&lt;</span>
      </button>
      <div class="min-w-[220px] px-3 text-center text-xs font-black">
        {currentVariant().key} - {currentVariant().name}
      </div>
      <button class="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-lg font-black hover:bg-white/20" onClick={() => move(1)} title="Next variant">
        <span aria-hidden="true">&gt;</span>
      </button>
    </div>
  );
}

export default function WorkspaceUnderstandingPrototype() {
  const [params, setParams] = useSearchParams();
  const selectedVariant = createMemo<VariantKey>(() => {
    const value = String(params.variant || 'A').toUpperCase();
    return variants.some((item) => item.key === value) ? (value as VariantKey) : 'A';
  });

  const setVariant = (variant: VariantKey) => {
    setParams({ variant });
  };

  createEffect(() => {
    if (String(params.variant || '').toUpperCase() !== selectedVariant()) {
      setVariant(selectedVariant());
    }
  });

  return (
    <>
      <Show when={selectedVariant() === 'A'}>
        <VariantA />
      </Show>
      <Show when={selectedVariant() === 'B'}>
        <VariantB />
      </Show>
      <Show when={selectedVariant() === 'C'}>
        <VariantC />
      </Show>
      <Show when={import.meta.env.DEV}>
        <PrototypeSwitcher current={selectedVariant()} onChange={setVariant} />
      </Show>
    </>
  );
}
