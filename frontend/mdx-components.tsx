import type { MDXComponents } from 'mdx/types';
import Link from 'next/link';

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    h1: ({ children }) => (
      <h1 className="font-[family-name:var(--font-display)] text-5xl font-medium tracking-tight text-white mt-2 mb-2">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="font-[family-name:var(--font-display)] text-3xl font-medium tracking-tight text-white mt-12 mb-4">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="font-[family-name:var(--font-display)] text-xl font-medium text-white mt-8 mb-3">
        {children}
      </h3>
    ),
    p: ({ children }) => (
      <p className="font-[family-name:var(--font-body),system-ui] text-base leading-relaxed text-neutral-300 my-4">
        {children}
      </p>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-white">{children}</strong>
    ),
    em: ({ children }) => <em className="italic text-amber-300">{children}</em>,
    ul: ({ children }) => (
      <ul className="list-disc list-outside pl-6 my-4 space-y-2 font-[family-name:var(--font-body),system-ui] text-neutral-300">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-outside pl-6 my-4 space-y-2 font-[family-name:var(--font-body),system-ui] text-neutral-300">
        {children}
      </ol>
    ),
    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
    a: ({ href, children }) => {
      const isExternal = typeof href === 'string' && /^https?:\/\//.test(href);
      const className =
        'text-amber-300 underline underline-offset-4 decoration-amber-700/60 hover:decoration-amber-300 hover:text-amber-200 transition';
      if (isExternal) {
        return (
          <a href={href} className={className} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        );
      }
      return (
        <Link href={href ?? '#'} className={className}>
          {children}
        </Link>
      );
    },
    code: ({ children }) => (
      <code className="rounded bg-neutral-900 border border-neutral-800 px-1.5 py-0.5 text-[0.85em] text-amber-200 font-[family-name:var(--font-mono),ui-monospace]">
        {children}
      </code>
    ),
    pre: ({ children }) => (
      <pre className="rounded-lg bg-neutral-900 border border-neutral-800 p-4 overflow-x-auto my-4 text-sm font-[family-name:var(--font-mono),ui-monospace]">
        {children}
      </pre>
    ),
    hr: () => <hr className="my-12 border-neutral-800" />,
    blockquote: ({ children }) => (
      <blockquote className="border-l-2 border-amber-500/60 pl-4 my-6 text-neutral-400 italic">
        {children}
      </blockquote>
    ),
    ...components,
  };
}
