function yueVisibleText() {
  const clone = document.body.cloneNode(true);
  clone.querySelectorAll('script, style, noscript, input[type="password"]').forEach((node) => node.remove());
  return (clone.innerText || '').replace(/\n{3,}/g, '\n\n').trim().slice(0, 100000);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'yue.snapshot') {
    sendResponse({ title: document.title || location.hostname, url: location.href, visible_text: yueVisibleText() });
    return;
  }
  if (message?.type !== 'yue.action') return;
  try {
    const { id, action, target, value } = message.command;
    const beforeUrl = location.href;
    const element = target ? yueFindTarget(target) : null;
    if (action === 'fill' || action === 'select') {
      if (!element || element instanceof HTMLInputElement && element.type === 'password') throw new Error('Target field is unavailable or protected.');
      element.focus(); element.value = value || '';
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    } else if (action === 'click' || action === 'download') {
      if (!element) throw new Error('Target control was not found.');
      if (action === 'click' && (element.type === 'submit' || element.closest('form'))) throw new Error('Form submission must use the submit action.');
      element.click();
    } else if (action === 'submit') {
      const form = element?.closest('form') || document.querySelector('form');
      if (!form) throw new Error('No form was found to submit.');
      form.requestSubmit();
    } else if (action === 'scroll') {
      window.scrollBy({ top: Number(value || 600), behavior: 'smooth' });
    } else if (action === 'navigate') {
      location.assign(target);
    }
    sendResponse({
      ok: true,
      command_id: id,
      before_url: beforeUrl,
      after_url: location.href,
      title: document.title || location.hostname,
      url: location.href,
      visible_text: yueVisibleText(),
    });
  } catch (error) {
    sendResponse({
      ok: false,
      command_id: message.command?.id,
      error: error instanceof Error ? error.message : 'Browser action failed.',
    });
  }
});

function yueFindTarget(target) {
  const normalized = target.trim().toLowerCase();
  const candidates = [...document.querySelectorAll('button, a, input, select, textarea, [role="button"], [aria-label]')];
  const matches = candidates.filter((element) => {
    const labels = [element.getAttribute('aria-label'), element.getAttribute('placeholder'), element.getAttribute('name'), element.innerText, element.value]
      .filter(Boolean).map((label) => label.trim().toLowerCase());
    return labels.includes(normalized);
  });
  if (matches.length > 1) throw new Error('Multiple controls match the browser command target.');
  return matches[0] || null;
}
