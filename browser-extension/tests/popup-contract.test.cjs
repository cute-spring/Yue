const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

test('describes the controlled-write approval boundary in the extension UI', () => {
  const popup = fs.readFileSync(path.join(__dirname, '..', 'popup.html'), 'utf8');

  assert.match(popup, /Every change, save, submit, download, and navigation requires your confirmation/i);
  assert.doesNotMatch(popup, /for this site/i);
});
