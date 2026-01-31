import { type Component } from 'solid-js';
import { A } from '@solidjs/router';

const App: Component<{children?: any}> = (props) => {
  return (
    <div class="flex h-screen bg-gray-50">
       <aside class="w-64 bg-white border-r flex flex-col">
          <div class="p-6 font-bold text-xl text-emerald-600 flex items-center gap-2">
            <span>Yue Platform</span>
          </div>
          <nav class="flex-1 px-4 space-y-2">
            <A href="/" class="flex items-center gap-3 px-4 py-2.5 rounded-lg hover:bg-emerald-50 text-gray-700 transition-colors" activeClass="bg-emerald-50 text-emerald-700 font-semibold" end>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              Chat
            </A>
            <A href="/notebook" class="flex items-center gap-3 px-4 py-2.5 rounded-lg hover:bg-emerald-50 text-gray-700 transition-colors" activeClass="bg-emerald-50 text-emerald-700 font-semibold">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              Notebook
            </A>
            <A href="/agents" class="flex items-center gap-3 px-4 py-2.5 rounded-lg hover:bg-emerald-50 text-gray-700 transition-colors" activeClass="bg-emerald-50 text-emerald-700 font-semibold">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Agents
            </A>
          </nav>
          <div class="p-4 border-t">
            <A href="/settings" class="flex items-center gap-3 w-full px-4 py-3 bg-gray-800 text-white rounded-xl hover:bg-gray-700 transition-colors shadow-lg group">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span class="font-bold text-sm">Settings</span>
            </A>
          </div>
       </aside>
       <main class="flex-1 overflow-hidden relative">
          {props.children}
       </main>
    </div>
  );
};

export default App;
