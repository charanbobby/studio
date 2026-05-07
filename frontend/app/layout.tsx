import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sri Studio",
  description: "AI Reel generator with voice-cloned narration",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-neutral-800 px-6 py-4">
          <h1 className="text-xl font-semibold">Sri Studio</h1>
        </header>
        <main className="max-w-3xl mx-auto px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
