import { createSignal, For, onCleanup, onMount, Show } from "solid-js";

export type ProviderInfo = {
  name: string;
  models: string[];
  available_models?: string[];
  configured?: boolean;
};

type Props = {
  providers: ProviderInfo[];
  selectedModel: string;
  onSelect: (provider: string, model: string) => void;
  onRefresh?: () => Promise<void>;
  providerFilter?: string;
  theme?: "dark" | "light";
  placement?: "top" | "bottom";
};

export default function ModelSwitcher(props: Props) {
  const [open, setOpen] = createSignal(false);
  const [refreshing, setRefreshing] = createSignal(false);
  let rootRef: HTMLDivElement | undefined;

  onMount(() => {
    const handle = (e: MouseEvent) => {
      const el = rootRef;
      if (!el) return;
      if (el.contains(e.target as Node)) return;
      setOpen(false);
    };
    window.addEventListener("click", handle);
    onCleanup(() => window.removeEventListener("click", handle));
  });

  const filteredProviders = () => {
    const list = props.providers || [];
    const filtered = props.providerFilter
      ? list.filter((p) => p.name === props.providerFilter)
      : list;
    return filtered.filter((p) => (p.available_models || p.models || []).length > 0);
  };

  const modelsOf = (p: ProviderInfo) => {
    const available = p.available_models || [];
    if (available.length > 0) return available;
    return p.models || [];
  };

  const buttonClass =
    props.theme === "dark"
      ? "flex items-center gap-2.5 px-4 py-2.5 bg-background border border-border hover:border-primary/30 hover:bg-primary/5 rounded-2xl transition-all active:scale-95 shadow-sm"
      : "flex items-center gap-2.5 px-4 py-2.5 bg-white border border-gray-200 hover:border-emerald-400 hover:bg-emerald-50 rounded-xl transition-all active:scale-95 shadow-sm";

  const menuClass =
    props.theme === "dark"
      ? "bg-slate-900/95 border border-white/10 text-white"
      : "bg-white border border-gray-200 text-gray-900";

  const headerClass =
    props.theme === "dark"
      ? "border-white/10 bg-white/5"
      : "border-gray-100 bg-gray-50";

  const providerHeaderClass =
    props.theme === "dark"
      ? "text-primary bg-primary/10"
      : "text-emerald-700 bg-emerald-50";

  const itemActiveClass =
    props.theme === "dark"
      ? "bg-primary text-white font-bold shadow-lg shadow-primary/20"
      : "bg-emerald-600 text-white font-semibold shadow-md shadow-emerald-200";

  const itemIdleClass =
    props.theme === "dark"
      ? "hover:bg-white/5 text-gray-300 hover:text-white"
      : "hover:bg-gray-50 text-gray-700";

  const placementClass =
    props.placement === "bottom" ? "top-full mt-2" : "bottom-full mb-3";

  const refresh = async () => {
    if (!props.onRefresh) return;
    setRefreshing(true);
    try {
      await props.onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div ref={rootRef} class="relative">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open());
          refresh();
        }}
        class={buttonClass}
      >
        <div class={`w-2 h-2 rounded-full ${props.theme === "dark" ? "bg-primary animate-pulse" : "bg-emerald-500"}`}></div>
        <span class="text-xs font-bold uppercase tracking-wider">
          {props.selectedModel || "Select Model"}
        </span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class={`h-3.5 w-3.5 transition-transform duration-300 ${
            props.theme === "dark" ? "text-text-secondary" : "text-gray-500"
          } ${open() ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <Show when={open()}>
        <div
          onClick={(e) => e.stopPropagation()}
          class={`absolute left-0 ${placementClass} w-72 backdrop-blur-xl rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-200 ${menuClass}`}
        >
          <div class={`p-4 border-b flex items-center justify-between ${headerClass}`}>
            <span class={`text-xs font-bold uppercase tracking-widest ${props.theme === "dark" ? "text-white/70" : "text-gray-600"}`}>
              Quick Switch
            </span>
            <Show when={refreshing()}>
              <div class={`w-4 h-4 border-2 rounded-full animate-spin ${props.theme === "dark" ? "border-white/20 border-t-primary" : "border-gray-200 border-t-emerald-500"}`}></div>
            </Show>
          </div>

          <div class={`p-2 max-h-80 overflow-y-auto space-y-1 ${props.theme === "dark" ? "scrollbar-thin scrollbar-thumb-white/10" : ""}`}>
            <For each={filteredProviders()}>
              {(provider) => (
                <div>
                  <div class={`px-3 py-2 text-[10px] font-bold uppercase rounded-lg mb-1 tracking-wider ${providerHeaderClass}`}>
                    {provider.name}
                  </div>
                  <For each={modelsOf(provider)}>
                    {(model) => (
                      <button
                        type="button"
                        onClick={() => {
                          props.onSelect(provider.name, model);
                          setOpen(false);
                        }}
                        class={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all flex items-center justify-between group ${
                          props.selectedModel === model ? itemActiveClass : itemIdleClass
                        }`}
                      >
                        <span>{model}</span>
                        <Show when={props.selectedModel === model}>
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path
                              fill-rule="evenodd"
                              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                              clip-rule="evenodd"
                            />
                          </svg>
                        </Show>
                      </button>
                    )}
                  </For>
                </div>
              )}
            </For>
            <Show when={filteredProviders().length === 0}>
              <div class={`px-4 py-6 text-sm ${props.theme === "dark" ? "text-white/60" : "text-gray-500"}`}>No models available</div>
            </Show>
          </div>
        </div>
      </Show>
    </div>
  );
}
