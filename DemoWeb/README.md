# DemoWeb 게시판

Next.js(App Router) + TypeScript + shadcn/ui(Tailwind CSS v4)로 만든 간단한 웹 게시판입니다.

## 기능

- 게시글 목록: 10개 단위 페이지네이션, 제목 검색(대소문자 무시, `?q=검색어&page=2`처럼 URL에 상태가 남음)
- 게시글 상세 보기 (본문 줄바꿈 유지, 수정 시각 표시)
- 게시글 작성 / 수정 / 삭제 (삭제 시 확인 다이얼로그, 달린 댓글도 함께 삭제)
- 댓글 작성 / 삭제
- 입력값 검증 (서버에서 검사하고 오류를 필드 아래에 표시)
- 반응형 레이아웃 (모바일에서는 목록이 카드형으로, 데스크톱에서는 표 형태로 표시)
- 다크 모드 (시스템 설정을 따르고, 헤더의 버튼으로 전환 가능 — `next-themes`)

로그인 기능은 없으므로 누구나 수정·삭제할 수 있습니다(데모용).

## 실행

```bash
npm install
npm run dev      # http://localhost:5176
npm run build    # 프로덕션 빌드
npm run start    # 빌드 결과 실행 (포트 5176)
npm run lint
```

`C:\work\.claude\launch.json`의 `demoweb` 항목으로 Claude 미리보기에서도 띄울 수 있습니다.

## 저장소: 로컬 JSON 파일

데이터는 `data/db.json` 한 파일에 저장합니다. 파일이 없으면 첫 요청 때 샘플 게시글 23개와 댓글 몇 개로 자동 생성됩니다(`src/lib/seed.ts`). 초기 상태로 되돌리려면 서버를 끄고 `data/` 폴더를 지우면 됩니다. 실행 중에 생기는 데이터이므로 `data/`는 `.gitignore`로 커밋에서 제외합니다.

### SQLite 대신 JSON 파일을 고른 이유

- **설치 의존성 없음**: `better-sqlite3` 같은 SQLite 드라이버는 네이티브 모듈이라 Windows에서 Node 버전에 맞는 바이너리가 없으면 빌드 도구(Visual Studio Build Tools, Python)가 필요합니다. JSON 파일은 Node 기본 `fs`만 씁니다.
- **눈으로 확인 가능**: QA·디버깅할 때 `data/db.json`을 열어 바로 상태를 보고, 직접 고쳐서 경계값(긴 제목, 빈 목록 등)을 재현하기 쉽습니다.
- **규모에 충분**: 데모 게시판 수준의 데이터(수백~수천 건)는 매 요청마다 파일 전체를 읽어도 문제가 없습니다.

### 안전장치와 한계

- 모든 쓰기는 하나의 큐로 직렬화해서, 동시에 요청이 와도 read-modify-write가 서로 덮어쓰지 않습니다(`src/lib/db.ts`의 `mutate`).
- 임시 파일에 먼저 쓰고 `rename`으로 교체해서, 쓰는 도중 프로세스가 죽어도 파일이 반쯤 깨지지 않습니다.
- 단일 Node 프로세스 기준입니다. 서버를 여러 대 띄우거나, Vercel 같은 서버리스(읽기 전용 파일 시스템) 환경에 배포하려면 SQLite/PostgreSQL 등으로 바꿔야 합니다. 데이터 접근은 `src/lib/db.ts`에만 모여 있어 이 파일만 교체하면 됩니다.

## 구조

```
src/
  app/
    page.tsx                 목록 (검색 + 페이지네이션)
    posts/new/page.tsx       작성
    posts/[id]/page.tsx      상세 + 댓글
    posts/[id]/edit/page.tsx 수정
    actions.ts               Server Actions (작성/수정/삭제/댓글, 입력값 검증)
  components/
    ui/                      shadcn/ui 컴포넌트 (button, input, card, alert-dialog …)
    post-form.tsx            작성·수정 공용 폼
    comment-section.tsx      댓글 목록·작성·삭제
    pagination.tsx, site-header.tsx, theme-toggle.tsx …
  lib/
    db.ts                    JSON 파일 저장소
    seed.ts                  초기 샘플 데이터
```

shadcn/ui 컴포넌트는 `components.json` 설정이 들어 있으므로 `npx shadcn@latest add <컴포넌트>`로 추가할 수 있습니다.
