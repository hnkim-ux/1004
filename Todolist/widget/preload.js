// 페이지 위에 위젯용 상단 바(끌어서 이동, 고정, 숨기기)와 좁은 창용 스타일을 덧붙인다.
// 할일 페이지 자체(page/index.html)는 브라우저용과 동일하게 유지한다.
const { ipcRenderer } = require('electron');

const SVG = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
const ICONS = {
  pin: `<svg ${SVG}><path d="M9 4h6l-1 6 3 3v2H7v-2l3-3z"/><path d="M12 15v5"/></svg>`,
  close: `<svg ${SVG}><path d="M6 6l12 12M18 6L6 18"/></svg>`,
};

const CSS = `
html.widget body { padding: 0 14px 72px; }
html.widget .app { padding-top: 48px; }
html.widget .header h1 { display: none; }
html.widget .toast { bottom: 12px; }

.widget-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 2px;
  height: 36px;
  padding: 0 4px 0 14px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  -webkit-app-region: drag;
  user-select: none;
}

.widget-title {
  flex: 1;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--muted);
}

.widget-btn {
  -webkit-app-region: no-drag;
  display: grid;
  place-items: center;
  width: 32px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.widget-btn svg { width: 16px; height: 16px; }
.widget-btn:hover { background: var(--accent-soft); color: var(--text); }
.widget-btn[aria-pressed="true"] { color: var(--accent); }
.widget-btn.close:hover { background: var(--danger); color: #fff; }

html.widget ::-webkit-scrollbar { width: 8px; }
html.widget ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
`;

window.addEventListener('DOMContentLoaded', async () => {
  document.documentElement.classList.add('widget');

  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);

  const bar = document.createElement('div');
  bar.className = 'widget-bar';
  bar.innerHTML = `
    <span class="widget-title">오늘의 할일</span>
    <button type="button" class="widget-btn pin" aria-label="항상 위에 표시" title="항상 위에 표시" aria-pressed="false">${ICONS.pin}</button>
    <button type="button" class="widget-btn close" aria-label="트레이로 숨기기" title="트레이로 숨기기">${ICONS.close}</button>`;
  document.body.prepend(bar);

  const pin = bar.querySelector('.pin');
  const setPinned = (on) => pin.setAttribute('aria-pressed', String(on));
  pin.addEventListener('click', () => ipcRenderer.send('widget:toggle-pin'));
  bar.querySelector('.close').addEventListener('click', () => ipcRenderer.send('widget:hide'));
  ipcRenderer.on('widget:pin-changed', (_e, on) => setPinned(on));

  const { alwaysOnTop } = await ipcRenderer.invoke('widget:get-state');
  setPinned(alwaysOnTop);
});
