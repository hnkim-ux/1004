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

## 저장소: Neon PostgreSQL

데이터는 [Neon](https://neon.tech) 서버리스 PostgreSQL에 저장합니다. 드라이버는 `@neondatabase/serverless`(HTTP 방식)를 쓰고, 데이터 접근은 모두 `src/lib/db.ts`에 모여 있습니다.

### 설정

`.env.example`을 `.env.local`로 복사하고 Neon 대시보드의 연결 문자열을 넣습니다. `.env.local`은 `.gitignore`로 커밋에서 제외됩니다.

```bash
DATABASE_URL="postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require"
```

### 테이블과 샘플 데이터

- `posts`(id, title, content, author, created_at, updated_at)
- `comments`(id, post_id → posts.id `ON DELETE CASCADE`, author, content, created_at)

서버가 첫 요청을 받을 때 `posts` 테이블이 없으면 두 테이블을 만들고 샘플 게시글 23개와 댓글 4개(`src/lib/seed.ts`)를 넣습니다. 테이블이 이미 있으면 게시글이 0건이어도 다시 넣지 않습니다. 초기 상태로 되돌리려면 Neon SQL 편집기에서 `DROP TABLE comments, posts;`를 실행한 뒤 페이지를 새로 고치면 됩니다.

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
    db.ts                    Neon PostgreSQL 데이터 접근
    seed.ts                  초기 샘플 데이터
```

shadcn/ui 컴포넌트는 `components.json` 설정이 들어 있으므로 `npx shadcn@latest add <컴포넌트>`로 추가할 수 있습니다.
