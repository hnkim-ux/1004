import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PaginationProps = {
  currentPage: number;
  totalPages: number;
  query: string;
};

const WINDOW = 2;

function pageHref(page: number, query: string) {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (page > 1) params.set("page", String(page));
  const search = params.toString();
  return search ? `/?${search}` : "/";
}

export function Pagination({ currentPage, totalPages, query }: PaginationProps) {
  if (totalPages <= 1) return null;

  const start = Math.max(1, currentPage - WINDOW);
  const end = Math.min(totalPages, currentPage + WINDOW);
  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);

  const navClass = buttonVariants({ variant: "ghost", size: "icon" });
  const disabledClass = "pointer-events-none opacity-40";

  return (
    <nav aria-label="페이지 이동" className="flex items-center justify-center gap-1">
      <Link
        href={pageHref(currentPage - 1, query)}
        aria-label="이전 페이지"
        aria-disabled={currentPage === 1}
        tabIndex={currentPage === 1 ? -1 : undefined}
        className={cn(navClass, currentPage === 1 && disabledClass)}
      >
        <ChevronLeft />
      </Link>
      {pages.map((page) => (
        <Link
          key={page}
          href={pageHref(page, query)}
          aria-current={page === currentPage ? "page" : undefined}
          className={buttonVariants({
            variant: page === currentPage ? "default" : "ghost",
            size: "icon",
          })}
        >
          {page}
        </Link>
      ))}
      <Link
        href={pageHref(currentPage + 1, query)}
        aria-label="다음 페이지"
        aria-disabled={currentPage === totalPages}
        tabIndex={currentPage === totalPages ? -1 : undefined}
        className={cn(navClass, currentPage === totalPages && disabledClass)}
      >
        <ChevronRight />
      </Link>
    </nav>
  );
}
