/* FreeAmir PWA — SW registration, install prompt, mobile sidebar */
(function () {
  'use strict';

  if ('serviceWorker' in navigator && !window.FREEAMIR_DEBUG) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js').catch((err) => {
        console.warn('[PWA] SW registration failed:', err);
      });
    });
  }

  let deferredPrompt = null;
  const installBtn = document.getElementById('install-btn');
  if (installBtn) {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      installBtn.classList.remove('hidden');
    });
    installBtn.addEventListener('click', async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') installBtn.classList.add('hidden');
      deferredPrompt = null;
    });
  }

  const menuToggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove('translate-x-full');
    sidebar.classList.add('translate-x-0');
    if (overlay) overlay.classList.remove('hidden');
  }
  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.add('translate-x-full');
    sidebar.classList.remove('translate-x-0');
    if (overlay) overlay.classList.add('hidden');
  }

  if (menuToggle) {
    menuToggle.addEventListener('click', () => {
      if (sidebar && sidebar.classList.contains('translate-x-full')) openSidebar();
      else closeSidebar();
    });
  }
  if (overlay) overlay.addEventListener('click', closeSidebar);

  if (sidebar) {
    sidebar.querySelectorAll('nav a').forEach((a) => {
      a.addEventListener('click', () => {
        if (window.innerWidth < 768) closeSidebar();
      });
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSidebar();
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth >= 768) {
      if (sidebar) {
        sidebar.classList.remove('translate-x-full');
        sidebar.classList.add('translate-x-0');
      }
      if (overlay) overlay.classList.add('hidden');
    }
  });
})();
