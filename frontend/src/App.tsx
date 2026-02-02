import { type Component, createSignal, onMount } from 'solid-js';
import { A } from '@solidjs/router';

const App: Component<{children?: any}> = (props) => {
  const [theme, setTheme] = createSignal<'light' | 'dark'>('light');
  const [isSidebarOpen, setIsSidebarOpen] = createSignal(true);
  const [isSidebarExpanded, setIsSidebarExpanded] = createSignal(false);

  onMount(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    }
  });

  const toggleTheme = () => {
    const newTheme = theme() === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  return (
    <div class="flex h-screen bg-background text-text-primary transition-colors duration-250">
       {/* Sidebar */}
       <aside 
         class={`fixed inset-y-0 left-0 z-50 ${isSidebarExpanded() ? 'w-sidebar' : 'w-16'} bg-surface border-r border-border flex flex-col transition-transform duration-250 ease-out lg:relative lg:translate-x-0 ${isSidebarOpen() ? 'translate-x-0' : '-translate-x-full'}`}
       >
         <div class={`flex items-center justify-between ${isSidebarExpanded() ? 'p-6' : 'p-4'} border-b border-border/60`}>
           <button
             type="button"
             class={`flex items-center ${isSidebarExpanded() ? 'gap-2' : 'justify-center w-full'} text-primary`}
             title="Yue Platform"
             onClick={() => setIsSidebarExpanded(v => !v)}
           >
             <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/10 flex items-center justify-center font-black text-lg">
               Y
             </div>
             <span class={`font-black text-xl ${isSidebarExpanded() ? 'block' : 'hidden'}`}>Yue</span>
           </button>

            <button 
              onClick={() => setIsSidebarOpen(false)}
             class="lg:hidden p-2 hover:bg-primary/10 rounded-xl"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

         <nav class={`flex-1 ${isSidebarExpanded() ? 'px-4' : 'px-2'} py-3 space-y-2`}>
           <A
             href="/"
             title="Chat"
             class={`group flex items-center ${isSidebarExpanded() ? 'gap-3 px-4' : 'justify-center px-0'} py-2.5 rounded-xl hover:bg-primary/10 text-text-secondary hover:text-primary transition-colors`}
             activeClass="bg-primary/10 text-primary font-semibold"
             end
           >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
             <span class={isSidebarExpanded() ? 'block font-bold text-sm' : 'hidden'}>Chat</span>
            </A>
           <A
             href="/notebook"
             title="Notebook"
             class={`group flex items-center ${isSidebarExpanded() ? 'gap-3 px-4' : 'justify-center px-0'} py-2.5 rounded-xl hover:bg-primary/10 text-text-secondary hover:text-primary transition-colors`}
             activeClass="bg-primary/10 text-primary font-semibold"
           >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
             <span class={isSidebarExpanded() ? 'block font-bold text-sm' : 'hidden'}>Notebook</span>
            </A>
           <A
             href="/agents"
             title="Agents"
             class={`group flex items-center ${isSidebarExpanded() ? 'gap-3 px-4' : 'justify-center px-0'} py-2.5 rounded-xl hover:bg-primary/10 text-text-secondary hover:text-primary transition-colors`}
             activeClass="bg-primary/10 text-primary font-semibold"
           >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
             <span class={isSidebarExpanded() ? 'block font-bold text-sm' : 'hidden'}>Agents</span>
            </A>
          </nav>

         <div class={`border-t border-border ${isSidebarExpanded() ? 'p-4' : 'p-2'} space-y-2`}>
            <button 
              onClick={toggleTheme}
             title={theme() === 'light' ? 'Dark Mode' : 'Light Mode'}
             class={`flex items-center w-full ${isSidebarExpanded() ? 'gap-3 px-4' : 'justify-center px-0'} py-2.5 text-text-secondary hover:text-text-primary hover:bg-primary/10 rounded-xl transition-colors`}
            >
              {theme() === 'light' ? (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                 <span class={isSidebarExpanded() ? 'block font-bold text-sm' : 'hidden'}>Dark Mode</span>
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 9H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                 <span class={isSidebarExpanded() ? 'block font-bold text-sm' : 'hidden'}>Light Mode</span>
                </>
              )}
            </button>
           <A
             href="/settings"
             title="Settings"
             class={`group flex items-center w-full ${isSidebarExpanded() ? 'gap-3 px-4' : 'justify-center px-0'} py-3 bg-primary text-white rounded-xl hover:bg-primary-hover transition-colors shadow-lg shadow-primary/15`}
           >
             <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-white/80 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
             <span class={isSidebarExpanded() ? 'block font-black text-sm' : 'hidden'}>Settings</span>
            </A>
          </div>
       </aside>

       {/* Mobile Sidebar Overlay */}
       {isSidebarOpen() && (
         <div 
           onClick={() => setIsSidebarOpen(false)}
           class="fixed inset-0 z-40 bg-black/50 lg:hidden"
         />
       )}

       {/* Main Area */}
       <main class="flex-1 overflow-hidden relative flex flex-col min-w-0">
          {/* Mobile Header */}
          <header class="lg:hidden flex items-center h-16 px-6 bg-surface/80 backdrop-blur-md border-b border-border z-30 sticky top-0">
            <button 
              onClick={() => setIsSidebarOpen(true)}
              class="p-2 -ml-2 hover:bg-primary/10 text-text-secondary hover:text-primary rounded-xl transition-all active:scale-90"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div class="ml-4 flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/10 flex items-center justify-center font-black text-primary text-sm">
                Y
              </div>
              <span class="font-black text-text-primary tracking-tight">Yue</span>
            </div>
          </header>
          
          <div class="flex-1 relative overflow-hidden">
            {props.children}
          </div>
       </main>
    </div>
  );
};

export default App;
