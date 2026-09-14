const SESSION_KEY = 'yueBrowserSessions';

async function sessions() {
  const stored = await chrome.storage.local.get({ [SESSION_KEY]: {} });
  return stored[SESSION_KEY];
}

async function saveSessions(value) {
  await chrome.storage.local.set({ [SESSION_KEY]: value });
}

async function reportCommandResult(session, commandId, succeeded, result) {
  await fetch(`${session.endpoint}/sessions/${session.id}/actions/${commandId}/result`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'X-Yue-Browser-Token': session.token },
    body: JSON.stringify({ succeeded, result }),
  });
}

async function pollSession(session) {
  try {
    const response = await fetch(`${session.endpoint}/sessions/${session.id}/commands/next`, {
      headers: { 'X-Yue-Browser-Token': session.token },
    });
    if (response.status === 204) return;
    if (!response.ok) throw new Error('Yue browser session is unavailable.');
    const command = await response.json();
    let result;
    try {
      result = await chrome.tabs.sendMessage(session.tabId, { type: 'yue.action', command });
    } catch {
      await reportCommandResult(session, command.id, null, { error: 'The browser command response was lost.' });
      return;
    }
    if (!result?.ok) {
      await reportCommandResult(session, command.id, Boolean(result?.ok), result || {});
      return;
    }
    if (result.command_id !== command.id || !result.url || !result.title || typeof result.visible_text !== 'string') {
      await reportCommandResult(session, command.id, null, { error: 'The browser command receipt is incomplete.' });
      return;
    }
    const snapshotResponse = await fetch(`${session.endpoint}/sessions/${session.id}/snapshot`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'X-Yue-Browser-Token': session.token },
        body: JSON.stringify({ title: result.title, url: result.url, visible_text: result.visible_text }),
    });
    if (!snapshotResponse.ok) {
      await reportCommandResult(session, command.id, null, { error: 'The post-command page snapshot could not be recorded.' });
      return;
    }
    await reportCommandResult(session, command.id, true, result);
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
