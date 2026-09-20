(() => {
  const dialog = document.getElementById('certificate-dialog');
  if (!dialog) return;
  let trigger;
  document.querySelectorAll('[data-certificate]').forEach(button => {
    button.addEventListener('click', () => {
      const path = button.dataset.certificate;
      if (!/^\/documents\/\d+\/download$/.test(path)) return;
      trigger = button;
      document.getElementById('certificate-title').textContent = button.dataset.title;
      dialog.querySelector('iframe').src = path;
      document.getElementById('certificate-direct').href = path;
      dialog.showModal();
    });
  });
  document.getElementById('certificate-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    dialog.querySelector('iframe').removeAttribute('src');
    trigger?.focus();
  });
})();
