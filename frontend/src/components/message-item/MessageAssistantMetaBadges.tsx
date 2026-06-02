import { Show, createSignal } from 'solid-js';
import { Message } from '../../types';
import { getWorkspaceGroundingModeLabel } from './evidence';
import { formatTime, formatTokenCount, getResponseStatus } from './helpers';

interface MessageAssistantMetaBadgesProps {
  msg: Message;
  isTyping: boolean;
  modelLabel: string;
  visionBadge: { label: string; className: string } | null;
}

export default function MessageAssistantMetaBadges(props: MessageAssistantMetaBadgesProps) {
  const [hoveredMetric, setHoveredMetric] = createSignal<string | null>(null);

  const responseStatus = () => getResponseStatus(props.msg, props.isTyping);

  const MetricPopover = (p: { title: string; label: string; value: string | number; icon?: any; description?: string }) => {
    const isVisible = () => hoveredMetric() === p.label;

    return (
      <div
        class="relative flex items-center"
        onMouseEnter={() => setHoveredMetric(p.label)}
        onMouseLeave={() => setHoveredMetric(null)}
      >
        <div class="flex items-center gap-1.5 rounded-md border border-border/40 bg-surface/50 px-2 py-1 text-[10px] font-medium text-text-secondary/80 transition-all duration-200 hover:border-primary/30 hover:bg-primary/5">
          {p.icon}
          <span class="text-[9px] font-bold uppercase tracking-tighter opacity-50">{p.label}</span>
          <span class="font-semibold text-text-primary/90">{p.value}</span>
        </div>

        <div
          class={`absolute left-1/2 top-full z-[100] mt-2 w-48 -translate-x-1/2 transform pointer-events-none transition-all duration-300 ease-out ${
            isVisible() ? 'translate-y-0 opacity-100' : 'translate-y-1 opacity-0'
          }`}
        >
          <div class="overflow-hidden rounded-xl border border-border/50 bg-white/95 p-3 shadow-[0_8px_30px_rgb(0,0,0,0.12)] backdrop-blur-xl">
            <div class="mb-1.5 flex items-center gap-2">
              <div class="rounded-lg bg-primary/10 p-1.5 text-primary">{p.icon}</div>
              <div class="text-[11px] font-bold tracking-tight text-text-primary">{p.title}</div>
            </div>
            <div class="text-[10px] font-medium leading-relaxed text-text-secondary/90">{p.description}</div>
            <div class="mt-2 flex items-center justify-between border-t border-border/30 pt-2">
              <span class="text-[9px] font-bold uppercase text-text-secondary/50">{p.label}</span>
              <span class="text-[10px] font-bold text-primary">{p.value}</span>
            </div>
          </div>
          <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-b-white/95" />
        </div>
      </div>
    );
  };

  return (
    <div class="export-exclude mt-4 flex flex-wrap items-center gap-3 justify-start">
      <div class="flex items-center gap-1.5 rounded-md border border-border/40 bg-text-secondary/5 px-2 py-1 text-[10px] font-medium text-text-secondary/70">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-60"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        {formatTime(props.msg.timestamp)}
      </div>

      <div class="flex items-center gap-1.5 rounded-md border border-primary/10 bg-primary/5 px-2 py-1 text-[10px] font-bold uppercase tracking-tight text-primary/80 shadow-sm shadow-primary/5">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
        {props.modelLabel}
      </div>

      <div class={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-bold uppercase tracking-tight ${
        responseStatus() === 'Failed'
          ? 'border-rose-500/20 bg-rose-500/5 text-rose-500'
          : responseStatus() === 'Generating'
            ? 'border-amber-500/20 bg-amber-500/5 text-amber-500'
            : 'border-primary/20 bg-primary/5 text-primary shadow-sm shadow-primary/5'
      }`}>
        <Show when={responseStatus() === 'Generating'}>
          <div class="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
        </Show>
        <Show when={responseStatus() === 'Completed'}>
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </Show>
        {responseStatus()}
      </div>

      <Show when={props.visionBadge}>
        <div class={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-bold uppercase tracking-tight ${props.visionBadge?.className}`}>
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h10"/></svg>
          {props.visionBadge?.label}
        </div>
      </Show>

      <div class="flex items-center gap-2">
        <Show when={props.msg.ttft}>
          <MetricPopover
            title="First Token Latency"
            label="TTFT"
            value={`${(props.msg.ttft! / 1000).toFixed(2)}s`}
            icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>}
            description="The time taken from sending the request to receiving the very first token from the model."
          />
        </Show>
        <Show when={props.msg.total_duration}>
          <MetricPopover
            title="Generation Time"
            label="Total"
            value={`${(props.msg.total_duration! / 1000).toFixed(2)}s`}
            icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
            description="The total wall-clock time elapsed for the complete response generation process."
          />
        </Show>
        <Show when={props.msg.tps}>
          <MetricPopover
            title="Inference Speed"
            label="TPS"
            value={`${props.msg.tps!.toFixed(1)} t/s`}
            icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="m16 18 6-6-6-6"/><path d="M8 6l-6 6 6 6"/></svg>}
            description="Tokens Per Second: The average speed at which the model generated the text content."
          />
        </Show>
        <Show when={props.msg.finish_reason}>
          <MetricPopover
            title="Finish Reason"
            label="Exit"
            value={props.msg.finish_reason!}
            icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>}
            description="The reason why the model stopped generating (e.g., 'stop', 'length', 'tool_calls')."
          />
        </Show>
      </div>

      <Show when={props.msg.prompt_tokens || props.msg.completion_tokens}>
        <MetricPopover
          title="Token Consumption"
          label="Usage"
          value={`${formatTokenCount(props.msg.prompt_tokens ?? 0)}i / ${formatTokenCount(props.msg.completion_tokens ?? 0)}o`}
          icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7"/><path d="M16 5V3"/><path d="M8 5V3"/><path d="M3 9h18"/><path d="M16 19h6"/><path d="M19 16v6"/></svg>}
          description="Detailed breakdown of input (prompt) tokens and output (generated) tokens used."
        />
      </Show>

      <Show when={props.msg.citations && props.msg.citations.length > 0}>
        <div class="flex items-center gap-1.5 rounded-md border border-indigo-500/20 bg-indigo-500/5 px-2 py-1 text-[10px] font-bold uppercase tracking-tight text-indigo-500/80">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1 0 2.5 0 5-2 7Z"/><path d="M14 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1 0 2.5 0 5-2 7Z"/></svg>
          {props.msg.citations?.length} Citations
        </div>
      </Show>

      <Show when={props.msg.workspace_grounding}>
        <div class="flex items-center gap-1.5 rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2 py-1 text-[10px] font-bold uppercase tracking-tight text-emerald-600/80">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 4 7v6c0 5 3.4 7.7 8 8 4.6-.3 8-3 8-8V7l-8-4Z"/><path d="m9 12 2 2 4-4"/></svg>
          {getWorkspaceGroundingModeLabel(props.msg.workspace_grounding?.grounding_mode)}
        </div>
      </Show>

      <Show when={props.msg.tools && props.msg.tools.length > 0}>
        <div class="flex items-center gap-1.5 rounded-md border border-amber-500/20 bg-amber-500/5 px-2 py-1 text-[10px] font-bold uppercase tracking-tight text-amber-500/80">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
          {props.msg.tools?.length} Tools
        </div>
      </Show>
    </div>
  );
}
