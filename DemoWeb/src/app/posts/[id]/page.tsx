import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Pencil } from "lucide-react";

import { CommentSection } from "@/components/comment-section";
import { DeletePostButton } from "@/components/delete-post-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getPost } from "@/lib/db";
import { formatDateTime } from "@/lib/format";

export const dynamic = "force-dynamic";

type PostPageProps = { params: Promise<{ id: string }> };

async function loadPost(params: PostPageProps["params"]) {
  const { id } = await params;
  const postId = Number(id);
  if (!Number.isInteger(postId)) return null;
  return getPost(postId);
}

export async function generateMetadata({ params }: PostPageProps): Promise<Metadata> {
  const data = await loadPost(params);
  return { title: data?.post.title ?? "게시글을 찾을 수 없음" };
}

export default async function PostPage({ params }: PostPageProps) {
  const data = await loadPost(params);
  if (!data) notFound();
  const { post, comments } = data;
  const edited = post.updatedAt !== post.createdAt;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="-ml-3">
          <Link href="/">
            <ArrowLeft />
            목록으로
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader className="gap-3">
          <CardTitle className="text-xl leading-snug break-words sm:text-2xl">{post.title}</CardTitle>
          <div className="text-muted-foreground flex flex-wrap gap-x-3 gap-y-1 text-sm">
            <span className="text-foreground font-medium">{post.author}</span>
            <span>{formatDateTime(post.createdAt)}</span>
            {edited && <span>(수정됨 {formatDateTime(post.updatedAt)})</span>}
          </div>
        </CardHeader>
        <Separator />
        <CardContent>
          <div className="leading-relaxed break-words whitespace-pre-wrap" data-testid="post-content">
            {post.content}
          </div>
        </CardContent>
        <CardFooter className="justify-end gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/posts/${post.id}/edit`}>
              <Pencil />
              수정
            </Link>
          </Button>
          <DeletePostButton postId={post.id} />
        </CardFooter>
      </Card>

      <CommentSection
        postId={post.id}
        comments={comments.map((comment) => ({
          id: comment.id,
          author: comment.author,
          content: comment.content,
          createdAtLabel: formatDateTime(comment.createdAt),
        }))}
      />
    </div>
  );
}
