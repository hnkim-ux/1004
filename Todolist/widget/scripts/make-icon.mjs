// 앱/트레이 아이콘(assets/icon.png, 256x256)을 생성한다. 외부 의존성 없이 PNG를 직접 인코딩.
// 실행: node scripts/make-icon.mjs
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { deflateSync } from 'node:zlib';

const SIZE = 256;
const BG = [0x2f, 0x5f, 0xe0];
const FG = [0xff, 0xff, 0xff];
const RADIUS = 56;
const MARGIN = 8;
const CHECK = [[70, 134], [112, 176], [188, 90]];
const STROKE = 13; // 체크 선 두께의 절반

function inRoundedSquare(x, y) {
  const lo = MARGIN;
  const hi = SIZE - MARGIN;
  if (x < lo || x > hi || y < lo || y > hi) return false;
  const cx = Math.min(Math.max(x, lo + RADIUS), hi - RADIUS);
  const cy = Math.min(Math.max(y, lo + RADIUS), hi - RADIUS);
  return (x - cx) ** 2 + (y - cy) ** 2 <= RADIUS ** 2;
}

function distToSegment(px, py, [ax, ay], [bx, by]) {
  const dx = bx - ax;
  const dy = by - ay;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

function onCheck(x, y) {
  return distToSegment(x, y, CHECK[0], CHECK[1]) <= STROKE ||
    distToSegment(x, y, CHECK[1], CHECK[2]) <= STROKE;
}

// 4x4 슈퍼샘플링으로 가장자리를 부드럽게
const SS = 4;
const raw = Buffer.alloc(SIZE * (SIZE * 4 + 1));
for (let y = 0; y < SIZE; y++) {
  raw[y * (SIZE * 4 + 1)] = 0; // filter: none
  for (let x = 0; x < SIZE; x++) {
    let cover = 0;
    let check = 0;
    for (let sy = 0; sy < SS; sy++) {
      for (let sx = 0; sx < SS; sx++) {
        const px = x + (sx + 0.5) / SS;
        const py = y + (sy + 0.5) / SS;
        if (inRoundedSquare(px, py)) {
          cover++;
          if (onCheck(px, py)) check++;
        }
      }
    }
    const a = cover / (SS * SS);
    const k = cover ? check / cover : 0;
    const i = y * (SIZE * 4 + 1) + 1 + x * 4;
    for (let c = 0; c < 3; c++) raw[i + c] = Math.round(BG[c] * (1 - k) + FG[c] * k);
    raw[i + 3] = Math.round(a * 255);
  }
}

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(buf) {
  let c = 0xffffffff;
  for (const b of buf) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
}

const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(SIZE, 0);
ihdr.writeUInt32BE(SIZE, 4);
ihdr[8] = 8; // bit depth
ihdr[9] = 6; // RGBA

const png = Buffer.concat([
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  chunk('IHDR', ihdr),
  chunk('IDAT', deflateSync(raw)),
  chunk('IEND', Buffer.alloc(0)),
]);

const out = join(dirname(fileURLToPath(import.meta.url)), '..', 'assets', 'icon.png');
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, png);
console.log('wrote', out);
