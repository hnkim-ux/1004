import type { Metadata } from "next";

import { SiteHeader } from "@/components/site-header";
import { ThemeProvider } from "@/components/theme-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "DemoWeb 게시판", template: "%s | DemoWeb 게시판" },
  description: "Next.js App Router와 shadcn/ui로 만든 간단한 게시판",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // next-themes가 hydration 전에 html의 class를 바꾸므로 경고를 억제한다.
    <html lang="ko" suppressHydrationWarning>
      <body className="min-h-dvh antialiased">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <SiteHeader />
          <main className="mx-auto w-full max-w-4xl px-4 py-6 sm:py-8">{children}</main>
        </ThemeProvider>
      </body>
    </html>
  );
}
