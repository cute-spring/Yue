const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function loadContentScript(elements) {
  let listener;
  class HTMLInputElement {}
  const context = {
    chrome: { runtime: { onMessage: { addListener: (next) => { listener = next; } } } },
    document: {
      body: {
        cloneNode: () => ({
          innerText: 'Expense form',
          querySelectorAll: () => [],
        }),
      },
      querySelectorAll: () => elements,
      querySelector: () => null,
      title: 'Expense form',
    },
    location: { href: 'https://erp.example.com/expense', hostname: 'erp.example.com', assign: () => {} },
    window: { scrollBy: () => {} },
    Event: class Event {},
    HTMLInputElement,
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '..', 'content.js'), 'utf8'),
    context,
    { filename: 'content.js' },
  );
  return (message) => new Promise((resolve) => listener(message, {}, resolve));
}

function button(label) {
  return {
    type: 'button',
    innerText: label,
    value: '',
    clickCount: 0,
    click() { this.clickCount += 1; },
    closest: () => null,
    getAttribute: () => null,
  };
}

test('refuses an ambiguous command target without clicking either control', async () => {
  const first = button('Save changes');
  const second = button('Save changes');
  const send = loadContentScript([first, second]);

  const result = await send({
    type: 'yue.action',
    command: { id: 'command-1', action: 'click', target: 'Save changes' },
  });

  assert.equal(result.ok, false);
  assert.match(result.error, /multiple/i);
  assert.equal(first.clickCount, 0);
  assert.equal(second.clickCount, 0);
});

test('returns a command-scoped receipt after one DOM action', async () => {
  const save = button('Save changes');
  const send = loadContentScript([save]);

  const result = await send({
    type: 'yue.action',
    command: { id: 'command-2', action: 'click', target: 'Save changes' },
  });

  assert.equal(result.ok, true);
  assert.equal(result.command_id, 'command-2');
  assert.equal(result.before_url, 'https://erp.example.com/expense');
  assert.equal(result.after_url, 'https://erp.example.com/expense');
  assert.equal(save.clickCount, 1);
});
