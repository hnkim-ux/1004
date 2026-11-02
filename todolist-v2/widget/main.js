// 오늘의 할일 데스크톱 위젯: 테두리 없는 작은 창 + 트레이 아이콘.
// 창의 X는 종료가 아니라 트레이로 숨기기이고, 종료는 트레이 메뉴에서 한다.
const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, screen } = require('electron');
const path = require('node:path');
const fs = require('node:fs');

const DEFAULT_STATE = { width: 380, height: 640, alwaysOnTop: false, hideTipShown: false };
const ICON = nativeImage.createFromPath(path.join(__dirname, 'assets', 'icon.png'));

let win = null;
let tray = null;
let state = { ...DEFAULT_STATE };
let quitting = false;
let saveTimer = null;

const stateFile = () => path.join(app.getPath('userData'), 'window-state.json');

function loadState() {
  try {
    return { ...DEFAULT_STATE, ...JSON.parse(fs.readFileSync(stateFile(), 'utf8')) };
  } catch (e) {
    return { ...DEFAULT_STATE };
  }
}

function saveState() {
  if (win && !win.isDestroyed()) {
    state = { ...state, ...win.getNormalBounds(), alwaysOnTop: win.isAlwaysOnTop() };
  }
  try {
    fs.writeFileSync(stateFile(), JSON.stringify(state));
  } catch (e) {
    // 위치 저장 실패는 무시 (다음 실행 때 기본 위치)
  }
}

function saveStateSoon() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveState, 400);
}

// 저장된 위치가 지금 연결된 모니터 밖이면(모니터 분리 등) 사용하지 않는다
function isOnScreen(b) {
  return screen.getAllDisplays().some(({ workArea: a }) =>
    b.x < a.x + a.width && b.x + b.width > a.x && b.y < a.y + a.height && b.y + 36 > a.y);
}

function showWindow() {
  if (!win) return;
  win.show();
  win.focus();
  updateTray();
}

function hideWindow() {
  if (!win) return;
  win.hide();
  updateTray();
  if (!state.hideTipShown && tray) {
    tray.displayBalloon({
      icon: ICON,
      title: '오늘의 할일 V2',
      content: '트레이로 숨겼어요. 작업 표시줄 오른쪽 아이콘을 누르면 다시 열려요.',
    });
    state.hideTipShown = true;
    saveState();
  }
}

function toggleWindow() {
  if (win && win.isVisible()) hideWindow();
  else showWindow();
}

function setAlwaysOnTop(on) {
  win.setAlwaysOnTop(on);
  win.webContents.send('widget:pin-changed', on);
  saveState();
  updateTray();
}

function updateTray() {
  if (!tray || !win) return;
  const loginItem = app.getLoginItemSettings();
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: win.isVisible() ? '숨기기' : '보이기', click: toggleWindow },
    { type: 'separator' },
    {
      label: '항상 위에 표시',
      type: 'checkbox',
      checked: win.isAlwaysOnTop(),
      click: (item) => setAlwaysOnTop(item.checked),
    },
    {
      label: 'Windows 시작 시 실행',
      type: 'checkbox',
      checked: loginItem.openAtLogin,
      // 개발 실행(npm start)에서는 electron.exe가 등록되므로 설치본에서만 허용
      enabled: app.isPackaged,
      click: (item) => {
        app.setLoginItemSettings({ openAtLogin: item.checked });
        updateTray();
      },
    },
    { type: 'separator' },
    { label: '종료', click: () => { quitting = true; app.quit(); } },
  ]));
}

function createWindow() {
  state = loadState();
  const opts = {
    width: state.width,
    height: state.height,
    minWidth: 320,
    minHeight: 360,
    frame: false,
    show: false,
    skipTaskbar: true,
    alwaysOnTop: state.alwaysOnTop,
    title: '오늘의 할일 V2',
    icon: ICON,
    backgroundColor: '#0a0f2e', // V2 테마는 항상 우주(다크) 배경
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  };
  if (state.x !== undefined && isOnScreen(state)) {
    opts.x = state.x;
    opts.y = state.y;
  } else {
    // 처음 실행: 주 모니터 오른쪽 위
    const a = screen.getPrimaryDisplay().workArea;
    opts.x = a.x + a.width - opts.width - 24;
    opts.y = a.y + 24;
  }

  win = new BrowserWindow(opts);
  win.setMenu(null);
  win.loadFile(path.join(__dirname, 'page', 'index.html'));

  // 위젯 안에서 다른 페이지로 이동하거나 새 창을 여는 것은 막는다
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (e) => e.preventDefault());

  win.once('ready-to-show', showWindow);
  win.on('moved', saveStateSoon);
  win.on('resized', saveStateSoon);
  win.on('close', (e) => {
    if (!quitting) {
      e.preventDefault();
      hideWindow();
    }
  });
}

ipcMain.handle('widget:get-state', () => ({ alwaysOnTop: win ? win.isAlwaysOnTop() : false }));
ipcMain.on('widget:toggle-pin', () => setAlwaysOnTop(!win.isAlwaysOnTop()));
ipcMain.on('widget:hide', hideWindow);

if (!app.requestSingleInstanceLock()) {
  // 이미 실행 중이면 그 창을 띄우고 종료
  app.quit();
} else {
  app.on('second-instance', showWindow);

  app.whenReady().then(() => {
    createWindow();
    tray = new Tray(ICON.resize({ width: 16, height: 16 }));
    tray.setToolTip('오늘의 할일 V2');
    tray.on('click', toggleWindow);
    updateTray();
  });

  app.on('before-quit', () => {
    quitting = true;
    saveState();
  });
}
