import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Sri Studio",
  description: "AI Reel generator with voice-cloned narration",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-neutral-800 px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-xl font-semibold hover:text-neutral-300">
            Sri Studio
          </Link>
          <nav className="text-sm">
            <Link href="/runs" className="text-neutral-400 hover:text-neutral-100">
              Past runs
            </Link>
          </nav>
        </header>
        <main className="max-w-3xl mx-auto px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
