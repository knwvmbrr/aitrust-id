/* A same-origin preference, never transmitted. This runs before styles to avoid a flash. */
(() => {
  'use strict';
  const key = 'aitrustid-appearance';
  const allowed = new Set(['system', 'light', 'dark']);
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  try { const saved = localStorage.getItem(key); if (allowed.has(saved)) preference = saved; } catch {}
  function apply() {
    const dark = preference === 'dark' || (preference === 'system' && media.matches);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#101512' : '#f7f8f6');
    document.querySelectorAll('[data-theme-picker]').forEach(control => { control.value = preference; control.closest('[data-appearance-control]')?.removeAttribute('hidden'); });
  }
  document.addEventListener('change', event => {
    if (!event.target.matches?.('[data-theme-picker]') || !allowed.has(event.target.value)) return;
    preference = event.target.value;
    try { localStorage.setItem(key, preference); } catch {}
    apply();
  });
  media.addEventListener('change', apply);
  window.addEventListener('storage', event => {
    if (event.key !== key) return;
    preference = allowed.has(event.newValue) ? event.newValue : 'system';
    apply();
  });
  window.AITrustTheme = Object.freeze({ preference: () => preference });
  document.addEventListener('DOMContentLoaded', apply);
  apply();
})();
