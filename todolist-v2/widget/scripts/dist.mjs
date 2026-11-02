// 설치 파일을 빌드해 release/ 폴더에 복사한다.
// 빌드 작업 폴더를 프로젝트 밖(임시 폴더)에 두는 이유: 프로젝트 폴더를 감시하는 Electron 기반 앱
// (에디터 등)이 .asar 파일을 열어 잠그면 electron-builder가 EBUSY로 실패한다.
import { execSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const widgetDir = join(dirname(fileURLToPath(import.meta.url)), '..');
const pkg = JSON.parse(readFileSync(join(widgetDir, 'package.json'), 'utf8'));
const outDir = join(tmpdir(), 'todaytodo-v2-build');
const installer = `TodayTodo-V2-Setup-${pkg.version}.exe`;

rmSync(outDir, { recursive: true, force: true });
execSync(`npx electron-builder --win nsis --config.directories.output="${outDir}"`, {
  cwd: widgetDir,
  stdio: 'inherit',
});

mkdirSync(join(widgetDir, 'release'), { recursive: true });
copyFileSync(join(outDir, installer), join(widgetDir, 'release', installer));
console.log(`release/${installer}`);
