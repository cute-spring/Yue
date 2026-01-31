import { type Component } from 'solid-js';
import { A } from '@solidjs/router';

const App: Component<{children?: any}> = (props) => {
  return (
    <div class="flex h-screen bg-gray-50">
       <aside class="w-64 bg-white border-r flex flex-col">
          <div class="p-6 font-bold text-xl text-emerald-600">Yue Platform</div>
          <nav class="flex-1 px-4 space-y-2">
            <A href="/" class="block px-4 py-2 rounded hover:bg-emerald-50 text-gray-700" activeClass="bg-emerald-50 text-emerald-600 font-medium" end>Chat</A>
            <A href="/agents" class="block px-4 py-2 rounded hover:bg-emerald-50 text-gray-700" activeClass="bg-emerald-50 text-emerald-600 font-medium">Agents</A>
          </nav>
          <div class="p-4 border-t">
            <A href="/settings" class="flex items-center gap-2 w-full px-4 py-3 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span class="font-bold">System Config</span>
            </A>
          </div>
       </aside>
       <main class="flex-1 overflow-hidden">
          {props.children}
       </main>
    </div>
  );
};

export default App;
