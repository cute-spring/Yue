import { createSignal, onMount, For, Show } from 'solid-js';
import { ConfirmModal } from '../components/ConfirmModal';

type Note = {
  id: string;
  title: string;
  content: string;
  updated_at: string;
};

export default function Notebook() {
  const [notes, setNotes] = createSignal<Note[]>([]);
  const [selectedNote, setSelectedNote] = createSignal<Note | null>(null);
  
  // Editor State
  const [editTitle, setEditTitle] = createSignal("");
  const [editContent, setEditContent] = createSignal("");
  const [saveStatus, setSaveStatus] = createSignal("");
  const [confirmDeleteId, setConfirmDeleteId] = createSignal<string | null>(null);

  const loadNotes = async () => {
    try {
      const res = await fetch('/api/notebook/');
      const data = await res.json();
      setNotes(data);
    } catch (e) {
      console.error("Failed to load notes", e);
    }
  };

  onMount(loadNotes);

  const selectNote = (note: Note) => {
    setSelectedNote(note);
    setEditTitle(note.title);
    setEditContent(note.content);
    setSaveStatus("");
  };

  const createNote = async () => {
    const newNote = { title: "Untitled Note", content: "" };
    try {
      const res = await fetch('/api/notebook/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newNote)
      });
      const data = await res.json();
      await loadNotes();
      selectNote(data);
    } catch (e) {
      console.error("Failed to create note", e);
    }
  };

  const saveNote = async () => {
    if (!selectedNote()) return;
    setSaveStatus("Saving...");
    try {
      const res = await fetch(`/api/notebook/${selectedNote()?.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle(),
          content: editContent()
        })
      });
      const data = await res.json();
      setSaveStatus("Saved!");
      setTimeout(() => setSaveStatus(""), 2000);
      
      // Update local list without full reload to keep selection stable
      setNotes(prev => prev.map(n => n.id === data.id ? data : n));
      setSelectedNote(data);
    } catch (e) {
      setSaveStatus("Error saving");
      console.error(e);
    }
  };

  const deleteNote = async (id: string) => {
    try {
      await fetch(`/api/notebook/${id}`, { method: 'DELETE' });
      await loadNotes();
      if (selectedNote()?.id === id) setSelectedNote(null);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div class="flex h-full bg-background transition-colors duration-250">
      {/* Sidebar List */}
      <div class="w-1/3 border-r border-border bg-surface/50 flex flex-col transition-colors duration-250">
        <div class="p-6 border-b border-border flex justify-between items-center bg-surface transition-colors duration-250">
          <h2 class="font-bold text-xl text-text-primary">Notebook</h2>
          <button 
            onClick={createNote}
            class="bg-primary text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-primary-hover active:scale-95 transition-all shadow-lg shadow-primary/10"
          >
            + New Note
          </button>
        </div>
        <div class="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-border/50">
          <For each={notes()}>
            {note => (
              <div 
                onClick={() => selectNote(note)}
                class={`p-5 border-b border-border/60 cursor-pointer hover:bg-surface transition-all duration-200 relative group ${
                  selectedNote()?.id === note.id ? 'bg-surface shadow-sm' : ''
                }`}
              >
                <div class={`absolute left-0 top-0 bottom-0 w-1 bg-primary transition-transform duration-300 ${
                  selectedNote()?.id === note.id ? 'scale-y-100' : 'scale-y-0'
                }`} />
                
                <div class="flex justify-between items-start mb-1">
                  <h3 class={`font-semibold text-base truncate pr-6 ${!note.title ? 'text-text-secondary/50 italic' : 'text-text-primary'}`}>
                    {note.title || "Untitled Note"}
                  </h3>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDeleteId(note.id);
                    }}
                    class="opacity-0 group-hover:opacity-100 text-text-secondary hover:text-red-500 p-1 rounded-md hover:bg-red-50 transition-all"
                    title="Delete note"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
                
                <p class="text-sm text-text-secondary mt-1 line-clamp-2 leading-relaxed">
                  {note.content || "No content"}
                </p>
                
                <div class="flex items-center mt-3 text-[11px] text-text-secondary/70 font-medium">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {new Date(note.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                </div>
              </div>
            )}
          </For>
          <Show when={notes().length === 0}>
            <div class="p-12 text-center">
              <div class="w-16 h-16 bg-surface border border-border rounded-2xl flex items-center justify-center mx-auto mb-4 text-text-secondary/30">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </div>
              <p class="text-text-secondary text-sm">No notes yet. Create one to get started!</p>
            </div>
          </Show>
        </div>
      </div>

      {/* Editor Area */}
      <div class="flex-1 flex flex-col bg-surface transition-colors duration-250">
        <Show when={selectedNote()} fallback={
          <div class="flex-1 flex flex-col items-center justify-center text-text-secondary/30 bg-background/50">
            <div class="w-24 h-24 rounded-3xl border-2 border-dashed border-border flex items-center justify-center mb-6">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
            <p class="text-lg font-medium">Select a note to view or edit</p>
            <p class="text-sm mt-2">All your thoughts, neatly organized in one place.</p>
          </div>
        }>
          <div class="px-8 py-6 border-b border-border flex justify-between items-center bg-surface/80 backdrop-blur-sm sticky top-0 z-10">
            <input 
              type="text" 
              value={editTitle()}
              onInput={(e) => setEditTitle(e.currentTarget.value)}
              placeholder="Note Title"
              class="text-2xl font-bold text-text-primary bg-transparent border-none focus:ring-0 focus:outline-none w-full placeholder:text-text-secondary/30"
            />
            <div class="flex items-center gap-4">
              <span class={`text-sm font-medium transition-opacity duration-300 ${saveStatus() ? 'opacity-100' : 'opacity-0'} ${saveStatus() === 'Error saving' ? 'text-red-500' : 'text-primary'}`}>
                {saveStatus()}
              </span>
              <button 
                onClick={saveNote}
                class="bg-primary text-white px-6 py-2.5 rounded-xl font-semibold hover:bg-primary-hover active:scale-95 transition-all shadow-lg shadow-primary/20 flex items-center gap-2"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                </svg>
                Save
              </button>
            </div>
          </div>
          <textarea
            value={editContent()}
            onInput={(e) => setEditContent(e.currentTarget.value)}
            placeholder="Start writing your thoughts..."
            class="flex-1 p-8 lg:p-12 resize-none focus:outline-none text-text-primary bg-transparent leading-relaxed font-sans text-lg placeholder:text-text-secondary/20"
          />
        </Show>
      </div>

      <ConfirmModal
        show={!!confirmDeleteId()}
        title="Delete Note"
        message="Are you sure you want to delete this note? This action cannot be undone."
        confirmText="Delete Note"
        cancelText="Keep Note"
        type="danger"
        onConfirm={() => {
          const id = confirmDeleteId();
          if (id) {
            deleteNote(id);
            setConfirmDeleteId(null);
          }
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
