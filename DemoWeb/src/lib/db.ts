import { promises as fs } from "node:fs";
import path from "node:path";

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

const DATA_DIR = path.join(process.cwd(), "data");
const DB_FILE = path.join(DATA_DIR, "db.json");

// 쓰기 작업을 한 줄로 세워 read-modify-write 경합을 막는다.
// dev 모드의 HMR로 모듈이 다시 로드돼도 같은 큐를 쓰도록 globalThis에 둔다.
const globalForDb = globalThis as unknown as { demowebWriteQueue?: Promise<unknown> };

async function readDb(): Promise<Database> {
  try {
    const raw = await fs.readFile(DB_FILE, "utf8");
    return JSON.parse(raw) as Database;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    const seed = createSeed();
    await writeDb(seed);
    return seed;
  }
}

async function writeDb(db: Database) {
  await fs.mkdir(DATA_DIR, { recursive: true });
  // 임시 파일에 쓴 뒤 rename 해서, 쓰는 도중 중단돼도 파일이 반쯤 깨지지 않게 한다.
  const tmp = `${DB_FILE}.${process.pid}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(db, null, 2), "utf8");
  await fs.rename(tmp, DB_FILE);
}

function mutate<T>(fn: (db: Database) => T): Promise<T> {
  const run = async () => {
    const db = await readDb();
    const result = fn(db);
    await writeDb(db);
    return result;
  };
  const next = (globalForDb.demowebWriteQueue ?? Promise.resolve()).then(run, run);
  globalForDb.demowebWriteQueue = next.catch(() => undefined);
  return next;
}

export const PAGE_SIZE = 10;

export async function listPosts({ query, page }: { query: string; page: number }) {
  const db = await readDb();
  const keyword = query.trim().toLowerCase();
  const filtered = db.posts
    .filter((post) => !keyword || post.title.toLowerCase().includes(keyword))
    .sort((a, b) => b.id - a.id);

  const totalCount = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const currentPage = Math.min(Math.max(1, page), totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;

  const posts: PostSummary[] = filtered.slice(start, start + PAGE_SIZE).map((post) => ({
    ...post,
    commentCount: db.comments.filter((comment) => comment.postId === post.id).length,
  }));

  return { posts, totalCount, totalPages, currentPage };
}

export async function getPost(id: number) {
  const db = await readDb();
  const post = db.posts.find((p) => p.id === id);
  if (!post) return null;
  const comments = db.comments
    .filter((comment) => comment.postId === id)
    .sort((a, b) => a.id - b.id);
  return { post, comments };
}

export function createPost(input: Pick<Post, "title" | "content" | "author">) {
  return mutate((db) => {
    const now = new Date().toISOString();
    const post: Post = { id: db.nextPostId++, ...input, createdAt: now, updatedAt: now };
    db.posts.push(post);
    return post;
  });
}

export function updatePost(id: number, input: Pick<Post, "title" | "content">) {
  return mutate((db) => {
    const post = db.posts.find((p) => p.id === id);
    if (!post) return null;
    Object.assign(post, input, { updatedAt: new Date().toISOString() });
    return post;
  });
}

export function deletePost(id: number) {
  return mutate((db) => {
    const before = db.posts.length;
    db.posts = db.posts.filter((p) => p.id !== id);
    db.comments = db.comments.filter((c) => c.postId !== id);
    return db.posts.length !== before;
  });
}

export function createComment(input: Pick<Comment, "postId" | "author" | "content">) {
  return mutate((db) => {
    if (!db.posts.some((p) => p.id === input.postId)) return null;
    const comment: Comment = {
      id: db.nextCommentId++,
      ...input,
      createdAt: new Date().toISOString(),
    };
    db.comments.push(comment);
    return comment;
  });
}

export function deleteComment(id: number) {
  return mutate((db) => {
    const before = db.comments.length;
    db.comments = db.comments.filter((c) => c.id !== id);
    return db.comments.length !== before;
  });
}
