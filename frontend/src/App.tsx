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
            <A href="/settings" class="block px-4 py-2 rounded hover:bg-emerald-50 text-gray-700" activeClass="bg-emerald-50 text-emerald-600 font-medium">Settings</A>
          </nav>
       </aside>
       <main class="flex-1 overflow-hidden">
          {props.children}
       </main>
    </div>
  );
};

export default App;
