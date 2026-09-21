/* Refresh CSRF immediately before native form submission; never replay a failed POST. */
(() => {
  'use strict';
  const busy = new WeakSet();
  let pending;
  async function refresh() {
    if (!pending) pending = (async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 12000);
      try {
        const response = await fetch('/auth/csrf', {credentials: 'same-origin', cache: 'no-store', signal: controller.signal, headers: {'Accept': 'application/json'}});
        if (!response.ok) throw new Error('Token refresh failed');
        const data = await response.json();
        if (typeof data.csrf_token !== 'string' || !data.csrf_token) throw new Error('Missing token');
        return data;
      } finally { clearTimeout(timer); }
    })().finally(() => { pending = null; });
    return pending;
  }
  document.addEventListener('submit', async event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || event.defaultPrevented || form.method.toLowerCase() !== 'post' || !form.querySelector('[name="csrf_token"]')) return;
    if (new URL(form.action, location.href).origin !== location.origin) return;
    event.preventDefault();
    if (busy.has(form)) return;
    busy.add(form);
    const submitter = event.submitter;
    form.setAttribute('aria-busy', 'true');
    let message = form.querySelector('.session-status');
    if (!message) { message = document.createElement('p'); message.className = 'session-status'; message.setAttribute('role', 'alert'); form.append(message); }
    message.textContent = 'Checking form session…';
    try {
      const data = await refresh();
      if (document.querySelector('meta[name="session-authenticated"]')?.content === 'true' && !data.authenticated) {
        message.textContent = 'Your sign-in expired. Your text remains here. Sign in in another tab, then submit again. ';
        const link = document.createElement('a'); link.href = '/admin/login'; link.target = '_blank'; link.rel = 'noopener'; link.textContent = 'Open sign-in'; message.append(link);
        return;
      }
      form.querySelectorAll('[name="csrf_token"]').forEach(input => { input.value = data.csrf_token; });
      const meta = document.querySelector('meta[name="csrf-token"]');
      if (meta) meta.content = data.csrf_token;
      // The initial submit event already ran validation, editor sync and confirmations.
      if (submitter?.name) { const field = document.createElement('input'); field.type = 'hidden'; field.name = submitter.name; field.value = submitter.value; form.append(field); }
      HTMLFormElement.prototype.submit.call(form);
    } catch {
      message.textContent = 'Could not check your session. Your text has not been cleared. Check your connection and allow this site’s cookies, then try again.';
    } finally { busy.delete(form); form.removeAttribute('aria-busy'); }
  });
})();
