import { For, Show, createEffect, createMemo, createSignal, onMount } from 'solid-js';
import { ConfirmModal } from '../components/ConfirmModal';
import { SkillGroup, SkillSpec } from '../types';

export default function SkillGroups() {
  const [groups, setGroups] = createSignal<SkillGroup[]>([]);
  const [isSaving, setIsSaving] = createSignal(false);
  const [editingId, setEditingId] = createSignal<string | null>(null);
  const [name, setName] = createSignal('');
  const [description, setDescription] = createSignal('');
  const [skillRefs, setSkillRefs] = createSignal<string[]>([]);
  const [skills, setSkills] = createSignal<SkillSpec[]>([]);
  const [skillQuery, setSkillQuery] = createSignal('');
  const [pendingDeleteGroup, setPendingDeleteGroup] = createSignal<SkillGroup | null>(null);
  const [status, setStatus] = createSignal<{ type: 'success' | 'error'; message: string } | null>(null);
  let masterCheckboxRef: HTMLInputElement | undefined;

  const submitLabel = createMemo(() => editingId() ? 'Save Changes' : 'Create Group');
  const sortedSkills = createMemo(() =>
    [...skills()].sort((a, b) => `${a.name}:${a.version}`.localeCompare(`${b.name}:${b.version}`))
  );
  const filteredSkills = createMemo(() => {
    const query = skillQuery().trim().toLowerCase();
    if (!query) return sortedSkills();
    return sortedSkills().filter((skill) => {
      const ref = `${skill.name}:${skill.version}`.toLowerCase();
      const name = skill.name.toLowerCase();
      const desc = (skill.description || '').toLowerCase();
      return ref.includes(query) || name.includes(query) || desc.includes(query);
    });
  });
  const selectedSkillRefSet = createMemo(() => new Set(skillRefs()));
  const selectedCountInView = createMemo(() =>
    filteredSkills().filter(skill => selectedSkillRefSet().has(`${skill.name}:${skill.version}`)).length
  );
  const allInViewSelected = createMemo(() =>
    filteredSkills().length > 0 && selectedCountInView() === filteredSkills().length
  );
  const partiallySelectedInView = createMemo(() =>
    selectedCountInView() > 0 && selectedCountInView() < filteredSkills().length
  );
  const totalSelectedCount = createMemo(() => skillRefs().length);
  const selectedSkillDetails = createMemo(() => {
    const selected = selectedSkillRefSet();
    return sortedSkills().filter(skill => selected.has(`${skill.name}:${skill.version}`));
  });
  const skillSummaryInForm = createMemo(() => {
    if (totalSelectedCount() === 0) return 'No skills selected';
    return `${totalSelectedCount()} selected`;
  });

  const resetForm = () => {
    setEditingId(null);
    setName('');
    setDescription('');
    setSkillRefs([]);
    setSkillQuery('');
  };
  const startCreate = () => {
    resetForm();
    setStatus(null);
  };

  const loadGroups = async () => {
    try {
      const res = await fetch('/api/skill-groups/');
      const data = await res.json();
      setGroups(Array.isArray(data) ? data : []);
    } catch (e) {
      setStatus({ type: 'error', message: `Failed to load skill groups: ${e}` });
    }
  };

  onMount(loadGroups);
  onMount(async () => {
    try {
      const res = await fetch('/api/skills/');
      const data = await res.json();
      setSkills(Array.isArray(data) ? data : []);
    } catch (e) {
      setStatus({ type: 'error', message: `Failed to load skills: ${e}` });
    }
  });
  createEffect(() => {
    if (!masterCheckboxRef) return;
    masterCheckboxRef.indeterminate = partiallySelectedInView();
  });

  const submitForm = async (e: Event) => {
    e.preventDefault();
    if (!name().trim()) return;
    setIsSaving(true);
    setStatus(null);
    const payload = {
      name: name().trim(),
      description: description().trim(),
      skill_refs: skillRefs(),
    };
    try {
      if (editingId()) {
        await fetch(`/api/skill-groups/${editingId()}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        setStatus({ type: 'success', message: 'Skill group updated.' });
      } else {
        await fetch('/api/skill-groups/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        setStatus({ type: 'success', message: 'Skill group created.' });
      }
      resetForm();
      await loadGroups();
    } catch (e) {
      setStatus({ type: 'error', message: `Save failed: ${e}` });
    } finally {
      setIsSaving(false);
    }
  };

  const startEdit = (group: SkillGroup) => {
    setEditingId(group.id);
    setName(group.name);
    setDescription(group.description || '');
    setSkillRefs(group.skill_refs || []);
    setSkillQuery('');
    setStatus(null);
  };

  const confirmDeleteGroup = async () => {
    const group = pendingDeleteGroup();
    if (!group) return;
    setStatus(null);
    try {
      await fetch(`/api/skill-groups/${group.id}`, { method: 'DELETE' });
      setStatus({ type: 'success', message: 'Skill group deleted.' });
      if (editingId() === group.id) resetForm();
      setPendingDeleteGroup(null);
      await loadGroups();
    } catch (e) {
      setStatus({ type: 'error', message: `Delete failed: ${e}` });
    }
  };

  const toggleSkillRef = (ref: string) => {
    if (selectedSkillRefSet().has(ref)) {
      setSkillRefs(skillRefs().filter(item => item !== ref));
      return;
    }
    setSkillRefs([...skillRefs(), ref]);
  };
  const removeSkillRef = (ref: string) => setSkillRefs(skillRefs().filter(item => item !== ref));
  const toggleAllInView = () => {
    const refsInView = filteredSkills().map(skill => `${skill.name}:${skill.version}`);
    if (refsInView.length === 0) return;
    if (allInViewSelected()) {
      setSkillRefs(skillRefs().filter(ref => !refsInView.includes(ref)));
      return;
    }
    setSkillRefs(Array.from(new Set([...skillRefs(), ...refsInView])));
  };
  const clearAllSkills = () => setSkillRefs([]);
  const parseSkillRef = (ref: string) => {
    const [skillName, version] = ref.split(':');
    return { skillName: skillName || ref, version: version || '-' };
  };
  const getRefForSkill = (skill: SkillSpec) => `${skill.name}:${skill.version}`;

  return (
    <div class="max-w-7xl mx-auto p-4 md:p-8">
      <div class="mb-8 space-y-1">
        <h2 class="text-4xl font-black text-gray-900 tracking-tight">Skill Groups</h2>
        <p class="text-gray-500 text-lg">Manage reusable skill bundles for universal agents</p>
      </div>

      <Show when={status()}>
        {(s) => (
          <div class={`mb-4 px-4 py-3 rounded-xl border text-sm font-semibold ${
            s().type === 'success'
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-rose-50 text-rose-700 border-rose-200'
          }`}>
            {s().message}
          </div>
        )}
      </Show>

      <div class="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-6">
        <div class="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 class="text-lg font-black text-gray-800">Group List</h3>
            <div class="flex items-center gap-2">
              <span class="text-xs text-gray-500 font-bold uppercase tracking-wider">{groups().length} total</span>
              <button
                type="button"
                onClick={startCreate}
                class="px-3 py-1.5 rounded-lg border border-violet-200 text-violet-700 text-xs font-bold uppercase tracking-wider hover:bg-violet-50"
              >
                Create Group
              </button>
            </div>
          </div>
          <div class="divide-y divide-gray-100 max-h-[72vh] overflow-y-auto">
            <For each={groups()}>
              {(group) => (
                <div class={`px-5 py-4 space-y-3 transition-colors ${
                  editingId() === group.id ? 'bg-violet-50/70' : 'bg-white'
                }`}>
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <h4 class="text-base font-bold text-gray-900 flex items-center gap-2">
                        {group.name}
                        <Show when={editingId() === group.id}>
                          <span class="text-[10px] px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 font-bold uppercase tracking-wider">
                            Editing
                          </span>
                        </Show>
                      </h4>
                      <p class="text-sm text-gray-500">{group.description || 'No description'}</p>
                      <div class="mt-2 text-[11px] text-violet-700 font-bold uppercase tracking-wider">
                        {(group.skill_refs || []).length} skills
                      </div>
                    </div>
                    <div class="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => startEdit(group)}
                        class="px-3 py-1.5 rounded-lg border border-gray-200 text-gray-700 text-xs font-bold uppercase tracking-wider hover:bg-gray-50"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => setPendingDeleteGroup(group)}
                        class="px-3 py-1.5 rounded-lg border border-rose-200 text-rose-700 text-xs font-bold uppercase tracking-wider hover:bg-rose-50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <For each={group.skill_refs || []}>
                      {(ref) => (
                        <span class="text-xs px-2 py-1 rounded-md bg-violet-50 text-violet-700 border border-violet-100">
                          {parseSkillRef(ref).skillName}
                        </span>
                      )}
                    </For>
                  </div>
                </div>
              )}
            </For>
            <Show when={groups().length === 0}>
              <div class="px-5 py-8 text-sm text-gray-500">No groups yet. Create your first skill group.</div>
            </Show>
          </div>
        </div>

        <form onSubmit={submitForm} class="bg-white border border-gray-100 rounded-2xl shadow-sm p-5 space-y-5">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-black text-gray-800">{editingId() ? 'Edit Group' : 'Create Group'}</h3>
              <p class="text-xs text-gray-500 mt-1">
                {editingId() ? 'Update group details and selected skills.' : 'Create a reusable skill bundle for universal agents.'}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <Show when={editingId()}>
                <button
                  type="button"
                  onClick={startCreate}
                  class="text-xs px-2.5 py-1.5 border border-gray-200 rounded-md text-gray-600 hover:bg-gray-50 font-semibold"
                >
                  Cancel
                </button>
              </Show>
              <button
                type="button"
                onClick={startCreate}
                class="text-xs px-2.5 py-1.5 border border-violet-200 rounded-md text-violet-700 hover:bg-violet-50 font-semibold"
              >
                New
              </button>
            </div>
          </div>

          <div class="space-y-2">
            <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider">Name</label>
            <input
              type="text"
              value={name()}
              onInput={(e) => setName(e.currentTarget.value)}
              placeholder="e.g. Backend Defaults"
              class="w-full border border-gray-200 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-violet-500 outline-none"
              required
            />
          </div>

          <div class="space-y-2">
            <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider">Description</label>
            <textarea
              value={description()}
              onInput={(e) => setDescription(e.currentTarget.value)}
              placeholder="Describe this skill group"
              rows={3}
              class="w-full border border-gray-200 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-violet-500 outline-none resize-y"
            />
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between gap-3">
              <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider">Skill list</label>
              <div class="text-[11px] font-bold text-violet-700 uppercase tracking-wider">{skillSummaryInForm()}</div>
            </div>
            <div class="space-y-2">
              <input
                type="text"
                value={skillQuery()}
                onInput={(e) => setSkillQuery(e.currentTarget.value)}
                placeholder="Search skill list to add"
                class="w-full border border-gray-200 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-violet-500 outline-none"
              />
              <div class="flex items-center justify-between gap-3">
                <label class="inline-flex items-center gap-2 text-xs text-gray-700 font-semibold">
                  <input
                    ref={masterCheckboxRef}
                    type="checkbox"
                    checked={allInViewSelected()}
                    onChange={toggleAllInView}
                    class="text-violet-600 focus:ring-violet-500 rounded border-gray-300"
                  />
                  Select current results ({selectedCountInView()}/{filteredSkills().length})
                </label>
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={clearAllSkills}
                    class="text-[10px] uppercase tracking-wider font-bold text-gray-500 hover:text-gray-600 bg-gray-100 px-2 py-1 rounded"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
            <Show when={selectedSkillDetails().length > 0}>
              <div class="flex flex-wrap gap-2">
                <For each={selectedSkillDetails()}>
                  {(skill) => (
                    <button
                      type="button"
                      onClick={() => removeSkillRef(getRefForSkill(skill))}
                      class="text-xs px-2 py-1 rounded-md bg-violet-50 text-violet-700 border border-violet-100 hover:bg-violet-100"
                    >
                      {skill.name}:{skill.version}
                    </button>
                  )}
                </For>
              </div>
            </Show>
            <div class="max-h-[28rem] overflow-y-auto pr-1">
              <div class="grid grid-cols-1 gap-2">
                <For each={filteredSkills()}>
                  {(skill) => {
                    const ref = getRefForSkill(skill);
                    const selected = () => selectedSkillRefSet().has(ref);
                    return (
                      <label class={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                        selected()
                          ? 'bg-violet-100 border-violet-400 ring-1 ring-violet-300'
                          : 'bg-white border-violet-100 hover:bg-violet-50'
                      }`}>
                        <input
                          type="checkbox"
                          checked={selected()}
                          onChange={() => toggleSkillRef(ref)}
                          class="mt-1 text-violet-600 focus:ring-violet-500 rounded border-gray-300"
                        />
                        <div class="min-w-0">
                          <div class="flex items-center gap-2">
                            <div class="text-sm font-semibold text-gray-900 truncate">{skill.name}</div>
                            <div class="text-[10px] uppercase tracking-wider font-bold text-violet-700">{skill.version}</div>
                          </div>
                          <div class="text-xs text-gray-500 mt-1 line-clamp-2">
                            {skill.description || 'No description available.'}
                          </div>
                          <div class="text-[10px] text-gray-400 mt-1">{ref}</div>
                        </div>
                      </label>
                    );
                  }}
                </For>
              </div>
              <Show when={filteredSkills().length === 0}>
                <div class="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 mt-2">
                  No matching skills found for this keyword.
                </div>
              </Show>
              <Show when={skills().length === 0}>
                <div class="text-xs text-violet-700/80 bg-violet-50 border border-violet-200 rounded-lg px-3 py-2 mt-2">
                  No loaded skills found. Reload from the Agents page or check /api/skills/reload.
                </div>
              </Show>
            </div>
            <Show when={skillRefs().length > 0}>
              <div class="text-[11px] text-gray-500">
                Click a selected chip above to remove quickly.
              </div>
            </Show>
            <Show when={skillRefs().length === 0}>
              <div class="text-[11px] text-gray-500">
                Select one or more skills to define this group.
              </div>
            </Show>
          </div>

          <button
            type="submit"
            disabled={isSaving()}
            class="w-full px-4 py-2.5 rounded-xl bg-violet-600 text-white font-bold uppercase tracking-wider hover:bg-violet-700 disabled:opacity-60"
          >
            {submitLabel()}
          </button>
        </form>
      </div>
      <ConfirmModal
        show={!!pendingDeleteGroup()}
        title="Delete Skill Group"
        message={`This will permanently delete "${pendingDeleteGroup()?.name || ''}". This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
        onConfirm={confirmDeleteGroup}
        onCancel={() => setPendingDeleteGroup(null)}
      />
    </div>
  );
}
