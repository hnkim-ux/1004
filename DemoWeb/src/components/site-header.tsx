import Link from "next/link";
import { MessageSquareText, PenLine } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="bg-background/80 sticky top-0 z-40 border-b backdrop-blur">
      <div className="mx-auto flex h-14 max-w-4xl items-center justify-between gap-2 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <MessageSquareText className="size-5" />
          <span>DemoWeb 게시판</span>
        </Link>
        <div className="flex items-center gap-2">
          <Button asChild size="sm">
            <Link href="/posts/new">
              <PenLine />
              <span className="hidden sm:inline">글쓰기</span>
            </Link>
          </Button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
