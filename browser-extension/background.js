const SESSION_KEY = 'yueBrowserSessions';

async function sessions() {
  const stored = await chrome.storage.local.get({ [SESSION_KEY]: {} });
  return stored[SESSION_KEY];
}

async function saveSessions(value) {
  await chrome.storage.local.set({ [SESSION_KEY]: value });
}

async function pollSession(session) {
  try {
    const response = await fetch(`${session.endpoint}/sessions/${session.id}/commands/next`, {
      headers: { 'X-Yue-Browser-Token': session.token },
    });
    if (response.status === 204) return;
    if (!response.ok) throw new Error('Yue browser session is unavailable.');
    const command = await response.json();
    const result = await chrome.tabs.sendMessage(session.tabId, { type: 'yue.action', command });
    if (result?.ok && result.url && result.title && typeof result.visible_text === 'string') {
      await fetch(`${session.endpoint}/sessions/${session.id}/snapshot`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'X-Yue-Browser-Token': session.token },
        body: JSON.stringify({ title: result.title, url: result.url, visible_text: result.visible_text }),
      });
    }
    await fetch(`${session.endpoint}/sessions/${session.id}/actions/${command.id}/result`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'X-Yue-Browser-Token': session.token },
      body: JSON.stringify({ succeeded: Boolean(result?.ok), result: result || {} }),
    });
  } catch (error) {
    console.warn('Yue Browser Companion could not run a command.', error);
  }
}

setInterval(async () => {
  const active = await sessions();
  await Promise.all(Object.values(active).map(pollSession));
}, 1000);

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'yue.track-session') return;
  sessions().then(async (active) => {
    active[message.session.id] = message.session;
    await saveSessions(active);
    sendResponse({ ok: true });
  });
  return true;
});
