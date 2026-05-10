import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Fraunces, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  axes: ["opsz", "SOFT"],
  display: "swap",
});

const body = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["300", "400", "500", "600"],
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sri Studio",
  description: "AI Reel generator with voice-cloned narration",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${body.variable} ${mono.variable}`}
    >
      <body className="min-h-screen font-body antialiased">
        <header className="border-b border-neutral-800 px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="font-display text-xl font-medium tracking-tight text-white hover:text-amber-300 transition"
          >
            Sri Studio
          </Link>
          <nav className="font-mono text-xs uppercase tracking-[0.18em]">
            <Link
              href="/runs"
              className="text-neutral-400 hover:text-amber-300 transition"
            >
              Past runs
            </Link>
          </nav>
        </header>
        <main className="max-w-3xl mx-auto px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
