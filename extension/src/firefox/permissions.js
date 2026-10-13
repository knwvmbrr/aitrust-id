// Firefox-only options control. The Chrome package never loads this script.
// Browser origin permission and application consent are separate decisions.
(() => {
  const origins = ['https://chatgpt.com/*', 'http://127.0.0.1/*'];
  const control = document.querySelector('#checks-enabled');
  const status = document.querySelector('#status');
  let allowed = false, revision = 0;
  const refreshView = () => { if (typeof refresh === 'function') refresh(); };
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && (changes.token || changes.gateway_public_key || changes.checks_enabled)) revision++;
  });
  document.querySelector('#clear').addEventListener('click', () => { revision++; }, true);
  browser.permissions.onRemoved.addListener(async removed => {
    if (!removed.origins?.length) return;
    revision++; allowed = false;
    try { await chrome.storage.local.set({checks_enabled: false}); }
    catch { status.textContent = 'Permission changed. Checks remain unavailable; reload settings.'; }
  });
  const initialRevision = revision;
  browser.permissions.contains({origins}).then(async granted => {
    if (initialRevision !== revision) return;
    allowed = granted;
    if (!granted) {
      // A saved application setting never substitutes for browser permission.
      await chrome.storage.local.set({checks_enabled: false});
    }
  }).catch(() => { allowed = false; });
  control.addEventListener('click', event => {
    if (!control.checked || allowed) return;
    event.preventDefault(); event.stopImmediatePropagation();
    const current = ++revision;
    control.disabled = true;
    // Called synchronously inside the owner's trusted click, never on startup.
    browser.permissions.request({origins}).then(async granted => {
      if (current !== revision) return;
      if (!granted || !await browser.permissions.contains({origins})) {
        status.textContent = 'Permission was not granted. Checks stay paused.';
        return;
      }
      if (current !== revision) return;
      allowed = true;
      await chrome.storage.local.set({checks_enabled: true});
      status.textContent = 'Firefox checks enabled. Only assistant responses go to your local service.';
    }).catch(() => {
      status.textContent = 'Could not obtain Firefox permission. Checks stay paused.';
    }).finally(refreshView);
  }, true);
})();
