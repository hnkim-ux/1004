"use client";

import Link from "next/link";
import { useActionState } from "react";

import type { FormState } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type PostFormProps = {
  action: (prev: FormState, formData: FormData) => Promise<FormState>;
  initial?: { title: string; content: string; author: string };
  submitLabel: string;
  cancelHref: string;
  // 수정 화면에서는 작성자를 바꾸지 않는다.
  authorEditable: boolean;
};

export function PostForm({ action, initial, submitLabel, cancelHref, authorEditable }: PostFormProps) {
  const [state, formAction, pending] = useActionState(action, {});
  const values = { ...initial, ...state.values };
  const errors = state.errors ?? {};

  return (
    <form action={formAction} className="flex flex-col gap-5" noValidate>
      {errors.form && (
        <p role="alert" className="text-destructive text-sm">
          {errors.form}
        </p>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor="author">작성자</Label>
        <Input
          id="author"
          name="author"
          defaultValue={values.author}
          maxLength={20}
          disabled={!authorEditable}
          aria-invalid={!!errors.author}
          aria-describedby={errors.author ? "author-error" : undefined}
          className="sm:max-w-xs"
        />
        {errors.author && (
          <p id="author-error" className="text-destructive text-sm">
            {errors.author}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="title">제목</Label>
        <Input
          id="title"
          name="title"
          defaultValue={values.title}
          maxLength={100}
          aria-invalid={!!errors.title}
          aria-describedby={errors.title ? "title-error" : undefined}
        />
        {errors.title && (
          <p id="title-error" className="text-destructive text-sm">
            {errors.title}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="content">내용</Label>
        <Textarea
          id="content"
          name="content"
          defaultValue={values.content}
          maxLength={5000}
          className="min-h-60"
          aria-invalid={!!errors.content}
          aria-describedby={errors.content ? "content-error" : undefined}
        />
        {errors.content && (
          <p id="content-error" className="text-destructive text-sm">
            {errors.content}
          </p>
        )}
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" asChild>
          <Link href={cancelHref}>취소</Link>
        </Button>
        <Button type="submit" disabled={pending}>
          {pending ? "저장 중…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
