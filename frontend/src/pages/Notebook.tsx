import { createSignal, onMount, For, Show } from 'solid-js';

type Note = {
  id: string;
  title: string;
  content: string;
  updated_at: string;
};

export default function Notebook() {
  const [notes, setNotes] = createSignal<Note[]>([]);
  const [selectedNote, setSelectedNote] = createSignal<Note | null>(null);
  const [isEditing, setIsEditing] = createSignal(false);
  
  // Editor State
  const [editTitle, setEditTitle] = createSignal("");
  const [editContent, setEditContent] = createSignal("");
  const [saveStatus, setSaveStatus] = createSignal("");

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
    setIsEditing(false);
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
      setIsEditing(true);
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

  const deleteNote = async (id: string, e: Event) => {
    e.stopPropagation();
    if (!confirm("Delete this note?")) return;
    try {
      await fetch(`/api/notebook/${id}`, { method: 'DELETE' });
      await loadNotes();
      if (selectedNote()?.id === id) setSelectedNote(null);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div class="flex h-full bg-white">
      {/* Sidebar List */}
      <div class="w-1/3 border-r bg-gray-50 flex flex-col">
        <div class="p-4 border-b flex justify-between items-center bg-white">
          <h2 class="font-bold text-lg text-gray-800">Notebook</h2>
          <button 
            onClick={createNote}
            class="bg-emerald-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors"
          >
            + New Note
          </button>
        </div>
        <div class="flex-1 overflow-y-auto">
          <For each={notes()}>
            {note => (
              <div 
                onClick={() => selectNote(note)}
                class={`p-4 border-b cursor-pointer hover:bg-white transition-colors ${
                  selectedNote()?.id === note.id ? 'bg-white border-l-4 border-l-emerald-500 shadow-sm' : 'border-l-4 border-l-transparent'
                }`}
              >
                <h3 class={`font-medium ${!note.title ? 'text-gray-400 italic' : 'text-gray-800'}`}>
                  {note.title || "Untitled Note"}
                </h3>
                <p class="text-xs text-gray-500 mt-1 truncate">
                  {note.content || "No content"}
                </p>
                <div class="flex justify-between items-center mt-2">
                  <span class="text-[10px] text-gray-400">
                    {new Date(note.updated_at).toLocaleDateString()}
                  </span>
                  <button 
                    onClick={(e) => deleteNote(note.id, e)}
                    class="text-gray-400 hover:text-red-600 px-2"
                  >
                    ×
                  </button>
                </div>
              </div>
            )}
          </For>
          <Show when={notes().length === 0}>
            <div class="p-8 text-center text-gray-400 text-sm">
              No notes yet. Create one to get started!
            </div>
          </Show>
        </div>
      </div>

      {/* Editor Area */}
      <div class="flex-1 flex flex-col bg-white">
        <Show when={selectedNote()} fallback={
          <div class="flex-1 flex flex-col items-center justify-center text-gray-300">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            <p>Select a note to view or edit</p>
          </div>
        }>
          <div class="p-4 border-b flex justify-between items-center">
            <input 
              type="text" 
              value={editTitle()}
              onInput={(e) => setEditTitle(e.currentTarget.value)}
              placeholder="Note Title"
              class="text-xl font-bold text-gray-800 bg-transparent border-none focus:ring-0 focus:outline-none w-full"
            />
            <div class="flex items-center gap-2">
              <span class="text-sm text-emerald-600 font-medium">{saveStatus()}</span>
              <button 
                onClick={saveNote}
                class="bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700 transition-colors shadow-sm"
              >
                Save
              </button>
            </div>
          </div>
          <textarea
            value={editContent()}
            onInput={(e) => setEditContent(e.currentTarget.value)}
            placeholder="Start writing..."
            class="flex-1 p-6 resize-none focus:outline-none text-gray-700 leading-relaxed font-mono text-sm"
          />
        </Show>
      </div>
    </div>
  );
}
