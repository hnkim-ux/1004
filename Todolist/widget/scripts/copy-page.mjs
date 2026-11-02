// 상위 폴더에서 빌드한 단일 파일 todolist.html을 위젯이 읽는 page/index.html로 복사한다.
import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const widgetDir = join(dirname(fileURLToPath(import.meta.url)), '..');
mkdirSync(join(widgetDir, 'page'), { recursive: true });
copyFileSync(join(widgetDir, '..', 'todolist.html'), join(widgetDir, 'page', 'index.html'));
console.log('copied page/index.html');
