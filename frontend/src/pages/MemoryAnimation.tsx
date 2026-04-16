import { For, Show, createMemo, createSignal, type Component } from 'solid-js';

type TurnKind = 'user' | 'assistant' | 'tool';
type MemoryStage = 'recent' | 'summary' | 'long_term';

type Turn = {
  id: number;
  kind: TurnKind;
  title: string;
  text: string;
  summaryText?: string;
  longTermText?: string;
  toolAction?: string;
};

const turns: Turn[] = [
  { id: 1, kind: 'user', title: '提出目标', text: '我想做一个带短期和长期记忆的聊天系统。', summaryText: '用户要设计带双层记忆的聊天系统。' },
  { id: 2, kind: 'assistant', title: '首次分层', text: '可以先把系统拆成短期上下文和长期记忆。', summaryText: '助手提出短期和长期分层。' },
  { id: 3, kind: 'user', title: '问 mem0', text: '长期记忆用 mem0 可以吗？', summaryText: '用户评估 mem0 是否适合长期记忆。' },
  { id: 4, kind: 'assistant', title: '确认定位', text: 'mem0 更适合长期记忆，短期会话最好独立管理。', summaryText: 'mem0 适合长期层，短期层应单独管理。', longTermText: '架构原则：长期记忆和短期会话解耦。' },
  { id: 5, kind: 'user', title: '追问短期', text: '那短期记忆应该怎么做？', summaryText: '用户继续追问短期会话管理。' },
  { id: 6, kind: 'assistant', title: '短期方案', text: '短期层通常由最近消息、会话摘要、工具状态组成。', summaryText: '短期层包含 recent、summary、tool state。', longTermText: '短期层结构：recent + summary + tool state。' },
  { id: 7, kind: 'user', title: '问摘要时机', text: '什么时候应该开始做摘要？', summaryText: '用户追问摘要触发条件。' },
  { id: 8, kind: 'assistant', title: '解释触发', text: '上下文变长时，就该把较早内容压缩成滚动摘要。', summaryText: '当上下文过长，早期轮次进入摘要。', toolAction: 'summary.policy.check()' },
  { id: 9, kind: 'user', title: '问保留窗口', text: '做了摘要之后，还要保留最近几轮原文吗？', summaryText: '用户关心摘要后最近原文是否保留。' },
  { id: 10, kind: 'assistant', title: '解释保留', text: '要保留，摘要保留背景，最近原文保留细节。', summaryText: '摘要保留背景，recent 保留最新细节。', longTermText: '规则：最近窗口优先于摘要。' },
  { id: 11, kind: 'user', title: '问长会话', text: '如果一直围绕同一主题追问，会发生什么？', summaryText: '用户开始关心超长主题会话。' },
  { id: 12, kind: 'assistant', title: '四层管理', text: '会进入热上下文、会话摘要、可检索历史、长期记忆四层协作。', summaryText: '长会话采用四层记忆管理。', longTermText: '长会话策略：热上下文、摘要、可检索历史、长期记忆协同。' },
  { id: 13, kind: 'tool', title: '触发摘要器', text: '系统调用摘要器，准备压缩第 1 到第 8 轮。', summaryText: '摘要器开始提取第 1 到第 8 轮核心信息。', toolAction: 'summary.generate(turns_1_to_8)' },
  { id: 14, kind: 'assistant', title: '得到摘要卡', text: '旧对话被压成一张摘要卡，原文从 prompt 里移出。', summaryText: '第 1 到第 8 轮被压成摘要卡。' },
  { id: 15, kind: 'user', title: '新增偏好', text: '我希望展示方式更像时间轴电影，不要太抽象。', summaryText: '用户要求界面更具象、更像电影时间轴。', longTermText: '用户偏好：希望机制表达更具象、更可视化。' },
  { id: 16, kind: 'assistant', title: '偏好入库', text: '这个偏好足够稳定，可以写进长期记忆。', summaryText: '稳定表达偏好被提升为长期记忆。', toolAction: 'memory.write(user_visual_preference)' },
  { id: 17, kind: 'tool', title: '检索旧决定', text: '系统从历史中召回之前关于摘要窗口的决定。', summaryText: '历史检索召回了旧的窗口规则。', toolAction: 'history.search(summary_window_rule)' },
  { id: 18, kind: 'assistant', title: '拼回 prompt', text: '被召回的旧决定和最近对话一起进入 prompt。', summaryText: '检索结果与 recent 对话一起送入 prompt。' },
  { id: 19, kind: 'assistant', title: '二次滚动压缩', text: '新的一段对话再次被并入摘要，减轻 prompt 压力。', summaryText: '第二阶段摘要继续吸收较老轮次。', toolAction: 'summary.merge(stage_2)' },
  { id: 20, kind: 'assistant', title: '稳定运行', text: '最终系统保持 recent、summary、long-term 三层稳定协作。', summaryText: '系统进入稳定的三层记忆协作状态。', longTermText: '最终策略：recent + summary + long-term 协同。' },
];

const kindLabel: Record<TurnKind, string> = {
  user: '用户输入',
  assistant: '助手回复',
  tool: '工具调用',
};

const kindIcon: Record<TurnKind, string> = {
  user: 'U',
  assistant: 'A',
  tool: 'T',
};

const kindBadge: Record<TurnKind, string> = {
  user: 'bg-sky-500 text-white',
  assistant: 'bg-violet-500 text-white',
  tool: 'bg-amber-400 text-slate-950',
};

const stageStyle: Record<MemoryStage, string> = {
  recent: 'border-cyan-300/30 bg-cyan-400/12 text-cyan-50',
  summary: 'border-amber-300/30 bg-amber-400/12 text-amber-50',
  long_term: 'border-emerald-300/30 bg-emerald-400/12 text-emerald-50',
};

const stageLabel: Record<MemoryStage, string> = {
  recent: 'P',
  summary: 'S',
  long_term: 'L',
};

const getRecentIds = (currentTurn: number) => {
  const start = Math.max(1, currentTurn - 3);
  return Array.from({ length: currentTurn - start + 1 }, (_, index) => start + index);
};

const getSummaryIds = (currentTurn: number) => {
  if (currentTurn <= 8) return [];
  const summaryEnd = currentTurn - 4;
  const summaryStart = Math.max(1, summaryEnd - 5);
  return Array.from({ length: summaryEnd - summaryStart + 1 }, (_, index) => summaryStart + index);
};

const getLongTermIds = (currentTurn: number) => {
  const recent = new Set(getRecentIds(currentTurn));
  const summary = new Set(getSummaryIds(currentTurn));
  return turns
    .filter((turn) => turn.id <= currentTurn && !recent.has(turn.id) && !summary.has(turn.id))
    .map((turn) => turn.id);
};

const getStage = (id: number, currentTurn: number): MemoryStage => {
  if (getRecentIds(currentTurn).includes(id)) return 'recent';
  if (getSummaryIds(currentTurn).includes(id)) return 'summary';
  return 'long_term';
};

const MemoryAnimation: Component = () => {
  const [currentTurn, setCurrentTurn] = createSignal(1);

  const current = createMemo(() => turns[currentTurn() - 1]);
  const recentIds = createMemo(() => getRecentIds(currentTurn()));
  const summaryIds = createMemo(() => getSummaryIds(currentTurn()));
  const longTermIds = createMemo(() => getLongTermIds(currentTurn()));

  const removedFromPrompt = createMemo(() => {
    if (currentTurn() <= 8) return [];
    return summaryIds().map((id) => turns[id - 1]);
  });

  const longTermFacts = createMemo(() =>
    turns
      .filter((turn) => turn.id <= currentTurn() && turn.longTermText)
      .map((turn) => ({ id: turn.id, text: turn.longTermText as string })),
  );

  const longTermSourceTurns = createMemo(() =>
    turns.filter((turn) => turn.id <= currentTurn() && turn.longTermText),
  );

  const summaryCard = createMemo(() => {
    if (removedFromPrompt().length === 0) return null;

    const covered = removedFromPrompt().map((turn) => turn.id);
    const firstId = covered[0];
    const lastId = covered[covered.length - 1];

    const goals = removedFromPrompt()
      .filter((turn) => turn.id <= 5)
      .map((turn) => turn.summaryText)
      .filter(Boolean) as string[];

    const decisions = removedFromPrompt()
      .filter((turn) => [4, 6, 8, 10, 12, 14, 19].includes(turn.id))
      .map((turn) => turn.summaryText)
      .filter(Boolean) as string[];

    const constraints = removedFromPrompt()
      .filter((turn) => [9, 10, 15].includes(turn.id))
      .map((turn) => turn.summaryText)
      .filter(Boolean) as string[];

    return {
      title: `阶段摘要卡：第 ${firstId} 到第 ${lastId} 轮`,
      covered,
      goals,
      decisions,
      constraints,
    };
  });

  const narration = createMemo(() => {
    const turn = current();
    const stage = getStage(turn.id, currentTurn());
    if (turn.kind === 'tool') {
      return `第 ${turn.id} 轮发生工具调用。系统正在执行 ${turn.toolAction ?? '工具动作'}，并据此更新摘要或长期记忆。`;
    }
    if (stage === 'recent') {
      return `第 ${turn.id} 轮是最新剧情的一部分，所以它的原文仍然保留在 Prompt 里，方便模型读取最新细节。`;
    }
    if (stage === 'summary') {
      return `第 ${turn.id} 轮已经不再以整段原文留在 Prompt 中，而是被压缩进会话摘要，只保留核心结论。`;
    }
    return `第 ${turn.id} 轮已经离开实时 Prompt，被归档为更稳定的历史信息；如果其中有稳定偏好或规则，也会进入长期记忆。`;
  });

  const changeReason = createMemo(() => {
    const turn = current();
    const stage = getStage(turn.id, currentTurn());

    if (turn.kind === 'tool') {
      return {
        from: '工具触发',
        to: turn.toolAction?.includes('summary') ? '更新摘要层' : turn.toolAction?.includes('memory') ? '写入长期记忆' : '更新上下文',
        why: '当前轮不是普通对话，而是系统在执行一次中间动作，用来压缩、检索或写入记忆。',
        effect: '这类轮次通常不需要像用户原话那样长期保留在 Prompt 中，但它会改变摘要或记忆状态。',
      };
    }

    if (stage === 'recent') {
      return {
        from: `第 ${turn.id} 轮原文`,
        to: '保留在 Prompt',
        why: '它仍然属于最近窗口，离当前问题最近，包含最新措辞、修正和限制。',
        effect: '模型会直接看到这一轮的原文，而不是只看到摘要后的结论。',
      };
    }

    if (stage === 'summary') {
      return {
        from: `第 ${turn.id} 轮原文`,
        to: '压缩进摘要卡',
        why: '它已经变成较早历史，不必继续占用 Prompt 的原文空间，但其中的目标和决定仍然有价值。',
        effect: '原文被移出 Prompt，只留下更短的摘要结果，减少上下文体积。',
      };
    }

    return {
      from: `第 ${turn.id} 轮历史`,
      to: '沉淀为长期层',
      why: '这一轮已经足够旧，或者其中出现了稳定偏好、规则、长期有效的事实。',
      effect: '它不再作为即时上下文参与每次推理，而是作为可复用记忆在需要时被召回。',
    };
  });

  return (
    <div class="min-h-full bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.16),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(249,115,22,0.14),_transparent_26%),linear-gradient(180deg,_#08111d_0%,_#101826_60%,_#0b1220_100%)] text-white">
      <style>{`
        @keyframes active-glow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(255,255,255,0.18); }
          50% { box-shadow: 0 0 0 8px rgba(255,255,255,0.05); }
        }

        .turn-active {
          animation: active-glow 1.8s ease-in-out infinite;
        }
      `}</style>

      <div class="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header class="rounded-[2rem] border border-white/10 bg-white/8 px-6 py-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
          <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div class="max-w-3xl">
              <p class="text-xs font-semibold uppercase tracking-[0.36em] text-cyan-200/80">Memory Slides</p>
              <h1 class="mt-2 text-3xl font-black tracking-tight text-white sm:text-4xl">
                20 轮对话如何流入 P / S / L
              </h1>
              <p class="mt-3 text-sm leading-6 text-slate-200/82">
                左边看轮次， 中间看 Prompt，右边看摘要与长期记忆，底部只保留当前一步的旁白。
              </p>
            </div>

            <div class="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => setCurrentTurn((value) => (value <= 1 ? turns.length : value - 1))}
                class="rounded-xl border border-white/10 bg-white/8 px-4 py-2 text-sm font-bold text-white transition hover:bg-white/12"
              >
                上一轮
              </button>
              <button
                type="button"
                onClick={() => setCurrentTurn((value) => (value >= turns.length ? 1 : value + 1))}
                class="rounded-xl border border-white/10 bg-white/8 px-4 py-2 text-sm font-bold text-white transition hover:bg-white/12"
              >
                下一轮
              </button>
              <div class="rounded-xl border border-white/10 bg-black/20 px-4 py-2 text-right">
                <div class="text-[11px] uppercase tracking-[0.28em] text-slate-300/70">Current</div>
                <div class="mt-1 text-lg font-black text-white">第 {currentTurn()} 轮</div>
              </div>
            </div>
          </div>
        </header>

        <section class="grid gap-5 xl:grid-cols-[0.9fr_1.1fr_0.95fr]">
          <div class="rounded-[2rem] border border-white/10 bg-slate-950/60 p-5 shadow-2xl shadow-black/20 backdrop-blur">
            <div class="mb-4">
              <div class="text-xs font-semibold uppercase tracking-[0.32em] text-slate-300/70">Conversation Track</div>
              <h2 class="mt-1 text-2xl font-black text-white">轮次轨道</h2>
            </div>

            <div class="relative rounded-[1.7rem] border border-white/10 bg-black/20 p-4">
              <div class="absolute bottom-5 left-8 top-5 w-px bg-gradient-to-b from-white/10 via-white/30 to-cyan-300/30" />
              <div class="space-y-3">
                <For each={turns}>
                  {(turn) => {
                    const stage = createMemo(() => getStage(turn.id, currentTurn()));
                    const isCurrent = () => turn.id === currentTurn();
                    const isFuture = () => turn.id > currentTurn();
                    return (
                      <button
                        type="button"
                        onClick={() => setCurrentTurn(turn.id)}
                        class={`relative flex w-full items-start gap-3 rounded-[1.15rem] border p-3 text-left transition ${
                          isFuture() ? 'opacity-40' : 'opacity-100'
                        } ${isCurrent() ? 'turn-active border-white/20 bg-white/12' : 'border-white/10 bg-white/[0.05] hover:bg-white/[0.08]'}`}
                      >
                        <div class={`mt-1 h-4 w-4 shrink-0 rounded-full ${isCurrent() ? 'bg-white' : 'bg-white/40'}`} />
                        <div class="min-w-0 flex-1">
                          <div class="flex flex-wrap items-center gap-2">
                            <span class={`rounded-full px-2 py-0.5 text-[11px] font-black ${kindBadge[turn.kind]}`}>
                              {kindIcon[turn.kind]}
                            </span>
                            <span class={`rounded-full border px-2 py-0.5 text-[11px] font-bold ${stageStyle[stage()]}`}>
                              {stageLabel[stage()]}
                            </span>
                          </div>
                          <div class="mt-2 flex items-center justify-between gap-3">
                            <div class="font-black text-white">第 {turn.id} 轮</div>
                            <div class="text-xs font-bold text-slate-300/75">{turn.title}</div>
                          </div>
                          <div class="mt-1 text-[11px] text-slate-400/80">{kindLabel[turn.kind]}</div>
                        </div>
                      </button>
                    );
                  }}
                </For>
              </div>
            </div>
          </div>

          <div class="space-y-5">
            <div class="rounded-[2rem] border border-cyan-300/15 bg-cyan-400/8 p-5 shadow-2xl shadow-black/15 backdrop-blur">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <div class="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-100/75">Prompt Window</div>
                  <h2 class="mt-1 text-2xl font-black text-white">Prompt</h2>
                </div>
                <div class="rounded-full border border-cyan-300/20 bg-cyan-400/12 px-3 py-1 text-xs font-bold text-cyan-50">
                  P x {recentIds().length}
                </div>
              </div>

              <div class="mt-4 rounded-[1.6rem] border border-cyan-300/15 bg-black/20 p-4">
                <div class="grid gap-3 sm:grid-cols-2">
                  <For each={recentIds()}>
                    {(id) => {
                      const turn = turns[id - 1];
                      return (
                        <div class="rounded-[1.2rem] border border-cyan-300/15 bg-cyan-400/10 p-3">
                          <div class="flex items-center justify-between gap-3">
                            <div class="flex items-center gap-2">
                              <span class="rounded-full bg-cyan-300 px-2 py-0.5 text-[11px] font-black text-slate-950">P</span>
                              <span class={`rounded-full px-2 py-0.5 text-[11px] font-black ${kindBadge[turn.kind]}`}>{kindIcon[turn.kind]}</span>
                            </div>
                            <span class="text-xs font-black uppercase tracking-[0.18em] text-cyan-100/85">#{turn.id}</span>
                          </div>
                          <div class="mt-3 rounded-xl border border-cyan-200/10 bg-black/15 px-3 py-4 text-center">
                            <div class="text-xs font-semibold uppercase tracking-[0.26em] text-cyan-100/62">slot</div>
                            <div class="mt-2 text-sm font-black text-white">{turn.title}</div>
                          </div>
                        </div>
                      );
                    }}
                  </For>
                </div>

                <div class="mt-4 flex items-center justify-between rounded-[1.1rem] border border-cyan-300/12 bg-cyan-400/8 px-4 py-3">
                  <div class="flex items-center gap-2 text-xs font-bold text-cyan-50">
                    <span class="rounded-full bg-cyan-300 px-2 py-0.5 text-slate-950">P</span>
                    <span>当前送入模型</span>
                  </div>
                  <div class="text-xs font-bold text-cyan-100/80">只保留标题，完整句子看旁白</div>
                </div>
              </div>
            </div>

            <div class="rounded-[2rem] border border-white/10 bg-slate-950/60 p-5 shadow-2xl shadow-black/20 backdrop-blur">
              <div class="text-xs font-semibold uppercase tracking-[0.32em] text-slate-300/70">Current Step</div>
              <h2 class="mt-1 text-2xl font-black text-white">当前变化说明</h2>
              <div class="mt-4 rounded-[1.6rem] border border-white/10 bg-white/[0.04] p-5">
                <div class="flex flex-wrap items-center gap-2">
                  <span class={`rounded-full px-3 py-1 text-xs font-black ${kindBadge[current().kind]}`}>{kindIcon[current().kind]}</span>
                  <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-bold text-slate-200">{current().title}</span>
                </div>
                <p class="mt-4 text-lg font-semibold leading-8 text-white">{current().title}</p>
                <Show when={current().toolAction}>
                  <div class="mt-4 rounded-xl border border-amber-300/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-50">
                    {current().toolAction}
                  </div>
                </Show>
                <div class="mt-4 grid gap-3 sm:grid-cols-2">
                  <div class="rounded-xl border border-white/10 bg-black/20 p-4">
                    <div class="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400/75">变化路径</div>
                    <div class="mt-3 flex items-center gap-3">
                      <div class="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-bold text-white">
                        {changeReason().from}
                      </div>
                      <div class="text-lg font-black text-slate-400">{'->'}</div>
                      <div class="rounded-lg border border-cyan-300/15 bg-cyan-400/10 px-3 py-2 text-sm font-bold text-cyan-50">
                        {changeReason().to}
                      </div>
                    </div>
                  </div>
                  <div class="rounded-xl border border-white/10 bg-black/20 p-4">
                    <div class="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400/75">为什么这样做</div>
                    <p class="mt-3 text-sm leading-6 text-slate-200/88">{changeReason().why}</p>
                  </div>
                </div>
                <div class="mt-3 rounded-xl border border-white/10 bg-black/20 p-4">
                  <div class="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400/75">变化结果</div>
                  <p class="mt-3 text-sm leading-6 text-slate-200/88">{changeReason().effect}</p>
                </div>
                <div class="mt-3 rounded-xl border border-white/10 bg-black/20 p-4">
                  <div class="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400/75">当前旁白</div>
                  <p class="mt-3 text-sm leading-7 text-slate-300/88">{narration()}</p>
                </div>
                <div class="mt-4 rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-300/85">
                  例句：{current().text}
                </div>
              </div>
            </div>
          </div>

          <div class="space-y-5">
            <div class="rounded-[2rem] border border-amber-300/15 bg-amber-400/8 p-5 shadow-2xl shadow-black/15 backdrop-blur">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <div class="text-xs font-semibold uppercase tracking-[0.32em] text-amber-100/75">Summary Layer</div>
                  <h2 class="mt-1 text-2xl font-black text-white">摘要</h2>
                </div>
                <div class="rounded-full border border-amber-300/20 bg-amber-400/12 px-3 py-1 text-xs font-bold text-amber-50">
                  S x {summaryIds().length}
                </div>
              </div>

              <div class="mt-4 rounded-[1.6rem] border border-amber-300/15 bg-black/20 p-4">
                <div class="mt-4 flex flex-wrap gap-2">
                  <For each={removedFromPrompt()}>
                    {(turn) => (
                      <div class="rounded-full border border-amber-300/20 bg-amber-400/12 px-3 py-1 text-xs font-bold text-amber-50">
                        第 {turn.id} 轮
                      </div>
                    )}
                  </For>
                </div>

                <Show when={summaryCard()}>
                  {(card) => (
                    <div class="mt-4 rounded-[1.2rem] border border-amber-200/20 bg-[linear-gradient(180deg,_rgba(251,191,36,0.14),_rgba(120,53,15,0.12))] p-4 shadow-lg shadow-black/10">
                      <div class="text-xs font-semibold uppercase tracking-[0.3em] text-amber-100/70">S replacement</div>
                      <div class="mt-1 text-base font-black text-white">{'原文 -> 摘要卡'}</div>

                      <div class="mt-4 grid gap-3 xl:grid-cols-[1fr_auto_1.1fr] xl:items-stretch">
                        <div class="rounded-xl border border-amber-200/15 bg-black/15 p-3">
                          <div class="text-xs font-semibold uppercase tracking-[0.28em] text-amber-100/68">Before</div>
                          <div class="mt-3 space-y-2">
                            <For each={removedFromPrompt().slice(0, 4)}>
                              {(turn) => (
                                <div class="rounded-lg border border-amber-300/12 bg-amber-400/8 px-3 py-2">
                                  <div class="flex items-center gap-2">
                                    <span class="rounded-full bg-amber-300 px-2 py-0.5 text-[10px] font-black text-slate-950">#{turn.id}</span>
                                    <span class="text-xs font-bold text-white">{turn.title}</span>
                                  </div>
                                </div>
                              )}
                            </For>
                            <Show when={removedFromPrompt().length > 4}>
                              <div class="rounded-lg border border-dashed border-amber-300/20 px-3 py-2 text-xs font-bold text-amber-100/80">
                                还有 {removedFromPrompt().length - 4} 轮也一起被压缩
                              </div>
                            </Show>
                          </div>
                        </div>

                        <div class="flex items-center justify-center">
                          <div class="rounded-full border border-amber-200/20 bg-amber-300/10 px-4 py-3 text-center">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-amber-100/70">S</div>
                            <div class="mt-1 text-2xl font-black text-amber-50">{'->'}</div>
                          </div>
                        </div>

                        <div class="rounded-xl border border-amber-200/15 bg-black/15 p-3">
                          <div class="flex items-center justify-between gap-3">
                            <div>
                              <div class="text-xs font-semibold uppercase tracking-[0.28em] text-amber-100/68">After</div>
                              <div class="mt-1 text-base font-black text-white">Summary Card</div>
                            </div>
                            <div class="rounded-full border border-amber-200/20 bg-amber-300/10 px-3 py-1 text-xs font-bold text-amber-50">
                              keep 1 card
                            </div>
                          </div>

                          <div class="mt-4 space-y-3">
                            <div class="rounded-xl border border-amber-200/15 bg-black/15 p-3">
                              <div class="text-xs font-semibold uppercase tracking-[0.28em] text-amber-100/68">Goal</div>
                              <div class="mt-2 space-y-2">
                                <For each={card().goals.slice(0, 2)}>
                                  {(item) => <p class="text-sm leading-6 text-amber-50">{item}</p>}
                                </For>
                              </div>
                            </div>

                            <div class="rounded-xl border border-amber-200/15 bg-black/15 p-3">
                              <div class="text-xs font-semibold uppercase tracking-[0.28em] text-amber-100/68">Rules</div>
                              <div class="mt-2 space-y-2">
                                <For each={card().decisions.slice(0, 4)}>
                                  {(item) => <p class="text-sm leading-6 text-amber-50">{item}</p>}
                                </For>
                              </div>
                            </div>

                            <Show when={card().constraints.length > 0}>
                              <div class="rounded-xl border border-amber-200/15 bg-black/15 p-3">
                                <div class="text-xs font-semibold uppercase tracking-[0.28em] text-amber-100/68">Prefs</div>
                                <div class="mt-2 space-y-2">
                                  <For each={card().constraints.slice(0, 3)}>
                                    {(item) => <p class="text-sm leading-6 text-amber-50">{item}</p>}
                                  </For>
                                </div>
                              </div>
                            </Show>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </Show>
              </div>
            </div>

            <div class="rounded-[2rem] border border-emerald-300/15 bg-emerald-400/8 p-5 shadow-2xl shadow-black/15 backdrop-blur">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <div class="text-xs font-semibold uppercase tracking-[0.32em] text-emerald-100/75">Long-Term Layer</div>
                  <h2 class="mt-1 text-2xl font-black text-white">长期记忆</h2>
                </div>
                <div class="rounded-full border border-emerald-300/20 bg-emerald-400/12 px-3 py-1 text-xs font-bold text-emerald-50">
                  L x {longTermIds().length}
                </div>
              </div>

              <div class="mt-4 rounded-[1.6rem] border border-emerald-300/15 bg-black/20 p-4">
                <div class="flex flex-wrap gap-2">
                  <For each={longTermIds()}>
                    {(id) => (
                      <div class="rounded-full border border-emerald-300/20 bg-emerald-400/12 px-3 py-1 text-xs font-bold text-emerald-50">
                        第 {id} 轮
                      </div>
                    )}
                  </For>
                </div>

                <Show when={longTermFacts().length > 0}>
                  <div class="mt-4 rounded-[1.2rem] border border-emerald-200/20 bg-[linear-gradient(180deg,_rgba(52,211,153,0.14),_rgba(6,78,59,0.12))] p-4 shadow-lg shadow-black/10">
                    <div class="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-100/70">L replacement</div>
                    <div class="mt-1 text-base font-black text-white">{'稳定事实 -> 长期记忆条目'}</div>

                    <div class="mt-4 grid gap-3 xl:grid-cols-[1fr_auto_1.1fr] xl:items-stretch">
                      <div class="rounded-xl border border-emerald-200/15 bg-black/15 p-3">
                        <div class="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-100/68">Before</div>
                        <div class="mt-3 space-y-2">
                          <For each={longTermSourceTurns().slice(0, 4)}>
                            {(turn) => (
                              <div class="rounded-lg border border-emerald-300/12 bg-emerald-400/8 px-3 py-2">
                                <div class="flex items-center gap-2">
                                  <span class="rounded-full bg-emerald-300 px-2 py-0.5 text-[10px] font-black text-slate-950">#{turn.id}</span>
                                  <span class="text-xs font-bold text-white">{turn.title}</span>
                                </div>
                              </div>
                            )}
                          </For>
                          <Show when={longTermSourceTurns().length > 4}>
                            <div class="rounded-lg border border-dashed border-emerald-300/20 px-3 py-2 text-xs font-bold text-emerald-100/80">
                              还有 {longTermSourceTurns().length - 4} 条稳定事实已写入
                            </div>
                          </Show>
                        </div>
                      </div>

                      <div class="flex items-center justify-center">
                        <div class="rounded-full border border-emerald-200/20 bg-emerald-300/10 px-4 py-3 text-center">
                          <div class="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-100/70">L</div>
                          <div class="mt-1 text-2xl font-black text-emerald-50">{'->'}</div>
                        </div>
                      </div>

                      <div class="rounded-xl border border-emerald-200/15 bg-black/15 p-3">
                        <div class="flex items-center justify-between gap-3">
                          <div>
                            <div class="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-100/68">After</div>
                            <div class="mt-1 text-base font-black text-white">Long-term Cards</div>
                          </div>
                          <div class="rounded-full border border-emerald-200/20 bg-emerald-300/10 px-3 py-1 text-xs font-bold text-emerald-50">
                            keep as memory
                          </div>
                        </div>

                        <div class="mt-4 space-y-3">
                          <For each={longTermFacts().slice(0, 4)}>
                            {(fact) => (
                              <div class="rounded-xl border border-emerald-200/15 bg-black/15 p-3">
                                <div class="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-100/68">L #{fact.id}</div>
                                <p class="mt-2 text-sm leading-6 text-emerald-50">{fact.text}</p>
                              </div>
                            )}
                          </For>
                        </div>
                      </div>
                    </div>
                  </div>
                </Show>
              </div>
            </div>

            <div class="rounded-[2rem] border border-white/10 bg-white/8 p-5 shadow-2xl shadow-black/15 backdrop-blur">
              <div class="text-xs font-semibold uppercase tracking-[0.32em] text-slate-300/70">Legend</div>
              <h2 class="mt-1 text-xl font-black text-white">图例</h2>
              <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div class="rounded-xl border border-cyan-300/15 bg-cyan-400/10 px-3 py-2 font-bold text-cyan-50">P = Prompt</div>
                <div class="rounded-xl border border-amber-300/15 bg-amber-400/10 px-3 py-2 font-bold text-amber-50">S = Summary</div>
                <div class="rounded-xl border border-emerald-300/15 bg-emerald-400/10 px-3 py-2 font-bold text-emerald-50">L = Long-term</div>
                <div class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 font-bold text-slate-100">U / A / T = 用户 / 助手 / 工具</div>
              </div>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
};

export default MemoryAnimation;
