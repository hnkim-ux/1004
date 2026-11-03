import Link from "next/link";
import { MessageCircle, Search } from "lucide-react";

import { Pagination } from "@/components/pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { listPosts } from "@/lib/db";
import { formatDate } from "@/lib/format";

// 게시글은 요청마다 JSON 파일에서 읽는다.
export const dynamic = "force-dynamic";

type HomeProps = {
  searchParams: Promise<{ q?: string | string[]; page?: string | string[] }>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  const query = (first(params.q) ?? "").trim();
  const page = Number.parseInt(first(params.page) ?? "1", 10) || 1;

  const { posts, totalCount, totalPages, currentPage } = await listPosts({ query, page });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">게시글</h1>
          <p className="text-muted-foreground text-sm">
            {query ? (
              <>
                <span className="text-foreground font-medium">&ldquo;{query}&rdquo;</span> 검색 결과{" "}
                {totalCount}건
              </>
            ) : (
              <>전체 {totalCount}건</>
            )}
          </p>
        </div>

        <form action="/" role="search" className="flex w-full gap-2 sm:w-auto">
          <Input
            type="search"
            name="q"
            defaultValue={query}
            placeholder="제목 검색"
            aria-label="제목 검색"
            className="sm:w-64"
          />
          <Button type="submit" variant="secondary">
            <Search />
            <span className="sr-only sm:not-sr-only">검색</span>
          </Button>
        </form>
      </div>

      {posts.length === 0 ? (
        <div className="text-muted-foreground flex flex-col items-center gap-3 rounded-lg border border-dashed py-16 text-center">
          <p>{query ? "검색 결과가 없습니다." : "아직 게시글이 없습니다."}</p>
          {query ? (
            <Button variant="outline" asChild>
              <Link href="/">전체 목록 보기</Link>
            </Button>
          ) : (
            <Button asChild>
              <Link href="/posts/new">첫 글 쓰기</Link>
            </Button>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <div className="bg-muted/50 text-muted-foreground hidden grid-cols-[4rem_1fr_7rem_7rem] gap-4 px-4 py-2 text-xs font-medium md:grid">
            <span className="text-center">번호</span>
            <span>제목</span>
            <span>작성자</span>
            <span>작성일</span>
          </div>
          <ul className="divide-y">
            {posts.map((post) => (
              <li key={post.id}>
                <Link
                  href={`/posts/${post.id}`}
                  className="hover:bg-accent/60 flex flex-col gap-1 px-4 py-3 transition-colors md:grid md:grid-cols-[4rem_1fr_7rem_7rem] md:items-center md:gap-4"
                >
                  <span className="text-muted-foreground hidden text-center text-sm md:block">{post.id}</span>
                  <span className="flex min-w-0 items-center gap-2 font-medium">
                    <span className="truncate">{post.title}</span>
                    {post.commentCount > 0 && (
                      <span
                        className="text-muted-foreground inline-flex shrink-0 items-center gap-0.5 text-xs"
                        aria-label={`댓글 ${post.commentCount}개`}
                      >
                        <MessageCircle className="size-3.5" />
                        {post.commentCount}
                      </span>
                    )}
                  </span>
                  <span className="text-muted-foreground flex gap-2 text-xs md:contents md:text-sm">
                    <span className="truncate">{post.author}</span>
                    <span>{formatDate(post.createdAt)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Pagination currentPage={currentPage} totalPages={totalPages} query={query} />
    </div>
  );
}
