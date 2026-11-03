"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import * as db from "@/lib/db";

export type FormState = {
  errors?: Partial<Record<"title" | "content" | "author" | "form", string>>;
  values?: Partial<Record<"title" | "content" | "author", string>>;
  // 댓글 폼처럼 성공 후 입력값을 비워야 하는 경우 폼을 다시 마운트하는 데 쓴다.
  submittedAt?: number;
};

const LIMITS = { title: 100, author: 20, content: 5000, comment: 500 };

function field(formData: FormData, name: string) {
  const value = formData.get(name);
  // 브라우저는 textarea 줄바꿈을 CRLF로 보내므로 LF로 맞춘다.
  return typeof value === "string" ? value.replace(/\r\n?/g, "\n").trim() : "";
}

function validatePost(formData: FormData, { withAuthor }: { withAuthor: boolean }) {
  const values = {
    title: field(formData, "title"),
    content: field(formData, "content"),
    author: withAuthor ? field(formData, "author") : "",
  };
  const errors: FormState["errors"] = {};

  if (!values.title) errors.title = "제목을 입력해 주세요.";
  else if (values.title.length > LIMITS.title) errors.title = `제목은 ${LIMITS.title}자 이하로 입력해 주세요.`;

  if (!values.content) errors.content = "내용을 입력해 주세요.";
  else if (values.content.length > LIMITS.content)
    errors.content = `내용은 ${LIMITS.content}자 이하로 입력해 주세요.`;

  if (withAuthor) {
    if (!values.author) errors.author = "작성자 이름을 입력해 주세요.";
    else if (values.author.length > LIMITS.author)
      errors.author = `작성자 이름은 ${LIMITS.author}자 이하로 입력해 주세요.`;
  }

  return { values, errors };
}

export async function createPostAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const { values, errors } = validatePost(formData, { withAuthor: true });
  if (Object.keys(errors).length > 0) return { errors, values };

  const post = await db.createPost(values);
  revalidatePath("/");
  redirect(`/posts/${post.id}`);
}

export async function updatePostAction(
  id: number,
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const { values, errors } = validatePost(formData, { withAuthor: false });
  if (Object.keys(errors).length > 0) return { errors, values };

  const post = await db.updatePost(id, { title: values.title, content: values.content });
  if (!post) return { errors: { form: "게시글을 찾을 수 없습니다. 이미 삭제되었을 수 있습니다." }, values };

  revalidatePath("/");
  revalidatePath(`/posts/${id}`);
  redirect(`/posts/${id}`);
}

export async function deletePostAction(id: number) {
  await db.deletePost(id);
  revalidatePath("/");
  redirect("/");
}

export async function createCommentAction(
  postId: number,
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const values = { author: field(formData, "author"), content: field(formData, "content") };
  const errors: FormState["errors"] = {};

  if (!values.author) errors.author = "이름을 입력해 주세요.";
  else if (values.author.length > LIMITS.author) errors.author = `이름은 ${LIMITS.author}자 이하로 입력해 주세요.`;

  if (!values.content) errors.content = "댓글 내용을 입력해 주세요.";
  else if (values.content.length > LIMITS.comment)
    errors.content = `댓글은 ${LIMITS.comment}자 이하로 입력해 주세요.`;

  if (Object.keys(errors).length > 0) return { errors, values };

  const comment = await db.createComment({ postId, ...values });
  if (!comment) return { errors: { form: "게시글을 찾을 수 없습니다." }, values };

  revalidatePath(`/posts/${postId}`);
  revalidatePath("/");
  // 이름은 다음 댓글에서도 그대로 쓰도록 남겨 둔다.
  return { values: { author: values.author }, submittedAt: Date.now() };
}

export async function deleteCommentAction(postId: number, commentId: number) {
  await db.deleteComment(commentId);
  revalidatePath(`/posts/${postId}`);
  revalidatePath("/");
}
