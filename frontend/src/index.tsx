/* @refresh reload */
import { render } from 'solid-js/web';
import { Router, Route } from '@solidjs/router';
import './index.css';
import App from './App';
import Chat from './pages/Chat';
import Agents from './pages/Agents';
import Settings from './pages/Settings';

import Notebook from './pages/Notebook';

const root = document.getElementById('root');

if (import.meta.env.DEV && !(root instanceof HTMLElement)) {
  throw new Error(
    'Root element not found. Did you forget to add it to your index.html? Or maybe the id attribute is misspelled?',
  );
}

render(() => (
  <Router root={App}>
    <Route path="/" component={Chat} />
    <Route path="/agents" component={Agents} />
    <Route path="/settings" component={Settings} />
    <Route path="/notebook" component={Notebook} />
  </Router>
), root!);
