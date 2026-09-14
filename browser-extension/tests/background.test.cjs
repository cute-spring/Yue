const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

test('reports an uncertain result when the tab command response is lost', async () => {
  const requests = [];
  let poll;
  const command = { id: 'command-1', action: 'click', target: 'Save changes' };
  const context = {
    chrome: {
      storage: {
        local: {
          get: async () => ({
            yueBrowserSessions: {
              session1: { id: 'session1', token: 'token', tabId: 7, endpoint: 'http://127.0.0.1/api/browser' },
            },
          }),
          set: async () => {},
        },
      },
      tabs: { sendMessage: async () => { throw new Error('Port closed'); } },
      runtime: { onMessage: { addListener: () => {} } },
    },
    fetch: async (url, options = {}) => {
      requests.push({ url, options });
      if (url.endsWith('/commands/next')) {
        return { status: 200, ok: true, json: async () => command };
      }
      return { status: 200, ok: true, json: async () => ({}) };
    },
    setInterval: (callback) => { poll = callback; },
    console: { warn: () => {} },
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '..', 'background.js'), 'utf8'),
    context,
    { filename: 'background.js' },
  );

  await poll();

  const resultRequest = requests.find((request) => request.url.endsWith('/actions/command-1/result'));
  assert.ok(resultRequest);
  assert.equal(JSON.parse(resultRequest.options.body).succeeded, null);
});

test('requires a successful post-command snapshot before reporting success', async () => {
  const requests = [];
  let poll;
  const command = { id: 'command-2', action: 'click', target: 'Save changes' };
  const context = {
    chrome: {
      storage: { local: { get: async () => ({ yueBrowserSessions: { session1: { id: 'session1', token: 'token', tabId: 7, endpoint: 'http://127.0.0.1/api/browser' } } }), set: async () => {} } },
      tabs: { sendMessage: async () => ({ ok: true, command_id: 'command-2', url: 'https://erp.example.com/expense', title: 'Expense form', visible_text: 'Saved' }) },
      runtime: { onMessage: { addListener: () => {} } },
    },
    fetch: async (url, options = {}) => {
      requests.push({ url, options });
      if (url.endsWith('/commands/next')) return { status: 200, ok: true, json: async () => command };
      if (url.endsWith('/snapshot')) return { status: 503, ok: false, json: async () => ({}) };
      return { status: 200, ok: true, json: async () => ({}) };
    },
    setInterval: (callback) => { poll = callback; },
    console: { warn: () => {} },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'background.js'), 'utf8'), context, { filename: 'background.js' });

  await poll();

  const resultRequest = requests.find((request) => request.url.endsWith('/actions/command-2/result'));
  assert.equal(JSON.parse(resultRequest.options.body).succeeded, null);
});
