import type { MDXComponents } from 'mdx/types';
import Link from 'next/link';

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    h1: ({ children }) => (
      <h1 className="text-4xl font-bold text-white mt-2 mb-2 tracking-tight">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-2xl font-semibold text-white mt-12 mb-4 tracking-tight">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-xl font-semibold text-white mt-8 mb-3">
        {children}
      </h3>
    ),
    p: ({ children }) => (
      <p className="text-base leading-relaxed text-neutral-300 my-4">
        {children}
      </p>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-white">{children}</strong>
    ),
    em: ({ children }) => <em className="italic">{children}</em>,
    ul: ({ children }) => (
      <ul className="list-disc list-outside pl-6 my-4 space-y-2 text-neutral-300">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-outside pl-6 my-4 space-y-2 text-neutral-300">
        {children}
      </ol>
    ),
    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
    a: ({ href, children }) => {
      const isExternal = typeof href === 'string' && /^https?:\/\//.test(href);
      const className =
        'text-sky-400 underline underline-offset-4 decoration-sky-700 hover:decoration-sky-400 hover:text-sky-300 transition';
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
      <code className="rounded bg-neutral-900 border border-neutral-800 px-1.5 py-0.5 text-sm text-neutral-200 font-mono">
        {children}
      </code>
    ),
    pre: ({ children }) => (
      <pre className="rounded-lg bg-neutral-900 border border-neutral-800 p-4 overflow-x-auto my-4 text-sm">
        {children}
      </pre>
    ),
    hr: () => <hr className="my-8 border-neutral-800" />,
    blockquote: ({ children }) => (
      <blockquote className="border-l-2 border-neutral-700 pl-4 my-6 text-neutral-400 italic">
        {children}
      </blockquote>
    ),
    ...components,
  };
}
