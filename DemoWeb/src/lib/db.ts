import { neon, type NeonQueryFunction } from "@neondatabase/serverless";

import { createSeed } from "@/lib/seed";

export type Post = {
  id: number;
  title: string;
  content: string;
  author: string;
  createdAt: string;
  updatedAt: string;
};

export type Comment = {
  id: number;
  postId: number;
  author: string;
  content: string;
  createdAt: string;
};

export type Database = {
  nextPostId: number;
  nextCommentId: number;
  posts: Post[];
  comments: Comment[];
};

export type PostSummary = Post & { commentCount: number };

type Row = Record<string, unknown>;

// dev 모드의 HMR로 모듈이 다시 로드돼도 연결과 초기화 상태를 재사용하도록 globalThis에 둔다.
const globalForDb = globalThis as unknown as {
  demowebSql?: NeonQueryFunction<false, false>;
  demowebReady?: Promise<void>;
};

function getSql() {
  if (!globalForDb.demowebSql) {
    const url = process.env.DATABASE_URL;
    if (!url) throw new Error("DATABASE_URL이 설정되지 않았습니다. .env.local을 확인해 주세요.");
    globalForDb.demowebSql = neon(url);
  }
  return globalForDb.demowebSql;
}

// 테이블이 없으면 만들고 샘플 데이터를 넣는다. 테이블이 이미 있으면(게시글을 모두 지운 경우 포함) 건드리지 않는다.
async function init() {
  const sql = getSql();
  const [{ exists }] = await sql`SELECT to_regclass('public.posts') IS NOT NULL AS exists`;
  if (exists) return;

  const seed = createSeed();
  await sql.transaction([
    sql`CREATE TABLE IF NOT EXISTS posts (
      id SERIAL PRIMARY KEY,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      author TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )`,
    sql`CREATE TABLE IF NOT EXISTS comments (
      id SERIAL PRIMARY KEY,
      post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
      author TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )`,
    sql`CREATE INDEX IF NOT EXISTS comments_post_id_idx ON comments(post_id)`,
    sql`INSERT INTO posts (id, title, content, author, created_at, updated_at)
      SELECT * FROM unnest(
        ${seed.posts.map((p) => p.id)}::int[],
        ${seed.posts.map((p) => p.title)}::text[],
        ${seed.posts.map((p) => p.content)}::text[],
        ${seed.posts.map((p) => p.author)}::text[],
        ${seed.posts.map((p) => p.createdAt)}::timestamptz[],
        ${seed.posts.map((p) => p.updatedAt)}::timestamptz[]
      )`,
    sql`INSERT INTO comments (id, post_id, author, content, created_at)
      SELECT * FROM unnest(
        ${seed.comments.map((c) => c.id)}::int[],
        ${seed.comments.map((c) => c.postId)}::int[],
        ${seed.comments.map((c) => c.author)}::text[],
        ${seed.comments.map((c) => c.content)}::text[],
        ${seed.comments.map((c) => c.createdAt)}::timestamptz[]
      )`,
    // id를 직접 넣었으므로 시퀀스를 그 다음 번호로 맞춘다.
    sql`SELECT setval(pg_get_serial_sequence('posts', 'id'), (SELECT max(id) FROM posts))`,
    sql`SELECT setval(pg_get_serial_sequence('comments', 'id'), (SELECT max(id) FROM comments))`,
  ]);
}

async function db() {
  globalForDb.demowebReady ??= init().catch((error) => {
    globalForDb.demowebReady = undefined;
    throw error;
  });
  await globalForDb.demowebReady;
  return getSql();
}

const iso = (value: unknown) => new Date(value as string | Date).toISOString();

function toPost(row: Row): Post {
  return {
    id: Number(row.id),
    title: String(row.title),
    content: String(row.content),
    author: String(row.author),
    createdAt: iso(row.created_at),
    updatedAt: iso(row.updated_at),
  };
}

function toComment(row: Row): Comment {
  return {
    id: Number(row.id),
    postId: Number(row.post_id),
    author: String(row.author),
    content: String(row.content),
    createdAt: iso(row.created_at),
  };
}

export const PAGE_SIZE = 10;

export async function listPosts({ query, page }: { query: string; page: number }) {
  const sql = await db();
  const keyword = query.trim();
  // position()은 %, _ 같은 패턴 문자를 그대로 비교하므로 LIKE처럼 이스케이프할 필요가 없다.
  const [{ count }] = await sql`
    SELECT count(*)::int AS count FROM posts
    WHERE ${keyword} = '' OR position(lower(${keyword}) IN lower(title)) > 0`;

  const totalCount = Number(count);
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const currentPage = Math.min(Math.max(1, page), totalPages);

  const rows = await sql`
    SELECT p.*, (SELECT count(*)::int FROM comments c WHERE c.post_id = p.id) AS comment_count
    FROM posts p
    WHERE ${keyword} = '' OR position(lower(${keyword}) IN lower(p.title)) > 0
    ORDER BY p.id DESC
    LIMIT ${PAGE_SIZE} OFFSET ${(currentPage - 1) * PAGE_SIZE}`;

  const posts: PostSummary[] = rows.map((row) => ({
    ...toPost(row),
    commentCount: Number(row.comment_count),
  }));

  return { posts, totalCount, totalPages, currentPage };
}

export async function getPost(id: number) {
  const sql = await db();
  const [postRows, commentRows] = await sql.transaction([
    sql`SELECT * FROM posts WHERE id = ${id}`,
    sql`SELECT * FROM comments WHERE post_id = ${id} ORDER BY id`,
  ]);
  if (postRows.length === 0) return null;
  return { post: toPost(postRows[0]), comments: commentRows.map(toComment) };
}

export async function createPost(input: Pick<Post, "title" | "content" | "author">) {
  const sql = await db();
  const [row] = await sql`
    INSERT INTO posts (title, content, author)
    VALUES (${input.title}, ${input.content}, ${input.author})
    RETURNING *`;
  return toPost(row);
}

export async function updatePost(id: number, input: Pick<Post, "title" | "content">) {
  const sql = await db();
  const [row] = await sql`
    UPDATE posts SET title = ${input.title}, content = ${input.content}, updated_at = now()
    WHERE id = ${id}
    RETURNING *`;
  return row ? toPost(row) : null;
}

export async function deletePost(id: number) {
  const sql = await db();
  // 댓글은 ON DELETE CASCADE로 함께 지워진다.
  const rows = await sql`DELETE FROM posts WHERE id = ${id} RETURNING id`;
  return rows.length > 0;
}

export async function createComment(input: Pick<Comment, "postId" | "author" | "content">) {
  const sql = await db();
  // 게시글이 없으면 아무것도 넣지 않고 null을 돌려준다.
  const [row] = await sql`
    INSERT INTO comments (post_id, author, content)
    SELECT id, ${input.author}, ${input.content} FROM posts WHERE id = ${input.postId}
    RETURNING *`;
  return row ? toComment(row) : null;
}

export async function deleteComment(id: number) {
  const sql = await db();
  const rows = await sql`DELETE FROM comments WHERE id = ${id} RETURNING id`;
  return rows.length > 0;
}
