import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  text: string;
};

const components: Components = {
  a: ({ href, children, ...rest }) => {
    const external = href?.startsWith("http");
    return (
      <a
        href={href}
        className="text-[var(--accent)] underline decoration-[var(--accent)]/40 underline-offset-2 hover:decoration-[var(--accent)]"
        {...(external
          ? { target: "_blank", rel: "noopener noreferrer" as const }
          : {})}
        {...rest}
      >
        {children}
      </a>
    );
  },
  code: ({ className, children, ...props }) => {
    const inline = !className;
    if (inline) {
      return (
        <code
          className="rounded bg-[var(--bg-elevated)] px-1.5 py-0.5 font-mono text-[0.9em] text-[var(--accent)]"
          {...props}
        >
          {children}
        </code>
      );
    }
    return (
      <code className={`font-mono text-[0.9em] ${className ?? ""}`} {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="my-3 overflow-x-auto rounded-lg border border-[var(--surface-border)] bg-[var(--bg)] p-4">
      {children}
    </pre>
  ),
  h1: (props) => (
    <h1
      className="mt-5 text-xl font-semibold first:mt-0"
      style={{ fontFamily: "var(--font-fraunces), serif" }}
      {...props}
    />
  ),
  h2: (props) => <h2 className="mt-4 text-lg font-semibold" {...props} />,
  h3: (props) => <h3 className="mt-3 text-base font-semibold" {...props} />,
  ul: (props) => <ul className="my-2 list-disc space-y-1 pl-5" {...props} />,
  ol: (props) => <ol className="my-2 list-decimal space-y-1 pl-5" {...props} />,
  li: (props) => <li className="text-[var(--text)]/90 [&>p]:my-0" {...props} />,
  p: (props) => <p className="my-2" {...props} />,
  blockquote: (props) => (
    <blockquote
      className="my-3 border-l-2 border-[var(--accent)]/50 pl-4 text-[var(--muted)] italic"
      {...props}
    />
  ),
  hr: () => <hr className="my-6 border-[var(--surface-border)]" />,
  table: (props) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm" {...props} />
    </div>
  ),
  th: (props) => (
    <th
      className="border border-[var(--surface-border)] bg-[var(--surface)] px-3 py-2 font-medium"
      {...props}
    />
  ),
  td: (props) => (
    <td className="border border-[var(--surface-border)] px-3 py-2" {...props} />
  ),
  input: ({ type, checked, ...rest }) => {
    if (type === "checkbox") {
      return (
        <input
          type="checkbox"
          checked={checked}
          readOnly
          className="mr-2 align-middle accent-[var(--accent)]"
          {...rest}
        />
      );
    }
    return <input type={type} {...rest} />;
  },
};

export function MarkdownBody({ text }: Props) {
  return (
    <div className="issue-md text-sm leading-relaxed text-[var(--text)]/90">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
