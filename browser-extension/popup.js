const endpointInput = document.querySelector('#endpoint');
const status = document.querySelector('#status');

chrome.storage.local.get({ endpoint: 'http://127.0.0.1:8003/api/browser' }, ({ endpoint }) => {
  endpointInput.value = endpoint;
});

function setStatus(message, isError = false) {
  status.textContent = message;
  status.style.color = isError ? '#b91c1c' : '#047857';
}

document.querySelector('#share').addEventListener('click', async () => {
  const endpoint = endpointInput.value.replace(/\/$/, '');
  const authorization = 'step_confirm';
  await chrome.storage.local.set({ endpoint });
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url || !/^https?:/.test(tab.url)) {
    setStatus('Open an HTTP/S webpage before sharing.', true);
    return;
  }

  try {
    setStatus('Sharing the current tab…');
    const registration = await fetch(`${endpoint}/sessions/register`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ tab_id: String(tab.id), title: tab.title || tab.url, url: tab.url, authorization_mode: authorization }),
    });
    if (!registration.ok) throw new Error((await registration.json()).detail || 'Could not register tab.');
    const session = await registration.json();
    const snapshot = await chrome.tabs.sendMessage(tab.id, { type: 'yue.snapshot' });
    const uploaded = await fetch(`${endpoint}/sessions/${session.id}/snapshot`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'X-Yue-Browser-Token': session.extension_token },
      body: JSON.stringify(snapshot),
    });
    if (!uploaded.ok) throw new Error((await uploaded.json()).detail || 'Could not upload page snapshot.');
    await chrome.runtime.sendMessage({
      type: 'yue.track-session',
      session: { id: session.id, token: session.extension_token, tabId: tab.id, endpoint },
    });
    setStatus('Shared. Attach this browser session to a Yue chat to let an authorized agent read it.');
  } catch (error) {
    setStatus(error instanceof Error ? error.message : 'Could not share this tab.', true);
  }
});
