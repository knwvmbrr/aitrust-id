/* Same-origin preference; never transmitted. Runs before styles to avoid a flash. */
(() => {
  'use strict';
  const key = 'aitrustid-appearance';
  const allowed = new Set(['system', 'light', 'dark']);
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  try { const saved = localStorage.getItem(key); if (allowed.has(saved)) preference = saved; } catch {}
  const snapshot = () => preference + ':' + (preference === 'dark' || (preference === 'system' && media.matches) ? 'dark' : 'light');
  function apply() {
    const resolved = snapshot().split(':')[1];
    document.documentElement.dataset.theme = resolved;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', resolved === 'dark' ? '#101512' : '#f7f8f6');
    document.querySelectorAll('[data-theme-toggle]').forEach(control => { control.checked = resolved === 'dark'; });
    document.querySelectorAll('[data-theme-state]').forEach(control => { control.textContent = resolved === 'dark' ? 'Dark' : 'Light'; });
    document.querySelectorAll('[data-theme-auto]').forEach(control => { control.setAttribute('aria-pressed', String(preference === 'system')); });
    document.querySelectorAll('[data-appearance-control]').forEach(control => control.removeAttribute('hidden'));
    window.dispatchEvent(new Event('aitrust-theme-change'));
  }
  function setPreference(value) {
    if (!allowed.has(value)) return;
    preference = value;
    try { localStorage.setItem(key, preference); } catch {}
    apply();
  }
  document.addEventListener('change', event => {
    if (event.target.matches?.('[data-theme-toggle]')) setPreference(event.target.checked ? 'dark' : 'light');
  });
  document.addEventListener('click', event => {
    if (event.target.closest?.('[data-theme-auto]')) setPreference('system');
  });
  media.addEventListener('change', apply);
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    preference = allowed.has(event.newValue) ? event.newValue : 'system';
    apply();
  });
  window.AITrustTheme = Object.freeze({
    preference: () => preference,
    snapshot,
    setPreference,
    subscribe: callback => {
      window.addEventListener('aitrust-theme-change', callback);
      return () => window.removeEventListener('aitrust-theme-change', callback);
    }
  });
  document.addEventListener('DOMContentLoaded', apply);
  apply();
})();
