"use client";

import { MessageCircle, X } from "lucide-react";
import { useActionState, useTransition } from "react";

import { createCommentAction, deleteCommentAction, type FormState } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export type CommentView = {
  id: number;
  author: string;
  content: string;
  createdAtLabel: string;
};

export function CommentSection({ postId, comments }: { postId: number; comments: CommentView[] }) {
  return (
    <section aria-labelledby="comments-heading" className="flex flex-col gap-4">
      <h2 id="comments-heading" className="flex items-center gap-2 text-lg font-semibold">
        <MessageCircle className="size-5" />
        댓글 <span className="text-muted-foreground">{comments.length}</span>
      </h2>

      {comments.length === 0 ? (
        <p className="text-muted-foreground text-sm">아직 댓글이 없습니다. 첫 댓글을 남겨 보세요.</p>
      ) : (
        <ul className="divide-y rounded-lg border">
          {comments.map((comment) => (
            <CommentItem key={comment.id} postId={postId} comment={comment} />
          ))}
        </ul>
      )}

      <CommentForm postId={postId} />
    </section>
  );
}

function CommentItem({ postId, comment }: { postId: number; comment: CommentView }) {
  const [pending, startTransition] = useTransition();

  return (
    <li className="flex items-start gap-3 p-4" data-testid="comment">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
          <span className="font-medium">{comment.author}</span>
          <span className="text-muted-foreground text-xs">{comment.createdAtLabel}</span>
        </div>
        <p className="mt-1 text-sm break-words whitespace-pre-wrap">{comment.content}</p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="size-7"
        aria-label={`${comment.author}님의 댓글 삭제`}
        disabled={pending}
        onClick={() => {
          if (!window.confirm("댓글을 삭제할까요?")) return;
          startTransition(() => deleteCommentAction(postId, comment.id));
        }}
      >
        <X />
      </Button>
    </li>
  );
}

function CommentForm({ postId }: { postId: number }) {
  const [state, formAction, pending] = useActionState(
    (prev: FormState, formData: FormData) => createCommentAction(postId, prev, formData),
    {},
  );
  const errors = state.errors ?? {};

  return (
    // 등록에 성공하면 key가 바뀌어 폼이 다시 마운트되고 입력값이 초기화된다.
    <form key={state.submittedAt} action={formAction} className="flex flex-col gap-2" noValidate>
      {errors.form && (
        <p role="alert" className="text-destructive text-sm">
          {errors.form}
        </p>
      )}
      <Input
        name="author"
        placeholder="이름"
        aria-label="댓글 작성자 이름"
        defaultValue={state.values?.author}
        maxLength={20}
        aria-invalid={!!errors.author}
        className="sm:max-w-xs"
      />
      {errors.author && <p className="text-destructive text-sm">{errors.author}</p>}
      <Textarea
        name="content"
        placeholder="댓글을 입력하세요"
        aria-label="댓글 내용"
        defaultValue={state.values?.content}
        maxLength={500}
        aria-invalid={!!errors.content}
      />
      {errors.content && <p className="text-destructive text-sm">{errors.content}</p>}
      <div className="flex justify-end">
        <Button type="submit" size="sm" disabled={pending}>
          {pending ? "등록 중…" : "댓글 등록"}
        </Button>
      </div>
    </form>
  );
}
