// index.html에 styles.css와 js/*.js를 인라인해 단일 파일 todolist.html을 만든다.
// 어디로 복사해도 열리도록 배포용으로 사용한다.  실행: node build.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFileSync(join(root, path), 'utf8');

let html = read('index.html');

html = html.replace(
  /<link rel="stylesheet" href="([^"]+)">/g,
  (_, href) => `<style>\n${read(href)}</style>`,
);

html = html.replace(
  /<script src="([^"]+)"><\/script>/g,
  // </script> 문자열이 코드 안에 있으면 태그가 끊기므로 이스케이프
  (_, src) => `<script>\n${read(src).replace(/<\/script/gi, '<\\/script')}</script>`,
);

html = html.replace(/\s*<!-- file:\/\/로 바로 열 수 있도록[^>]*-->/, '');

writeFileSync(join(root, 'todolist.html'), html);
console.log('built todolist.html');
