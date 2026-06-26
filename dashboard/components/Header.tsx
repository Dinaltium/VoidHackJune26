type Connection = "connecting" | "live" | "down";

const LABEL: Record<Connection, string> = {
  connecting: "Connecting…",
  live: "Live",
  down: "Disconnected",
};

export function Header({ connection }: { connection: Connection }) {
  return (
    <header className="header">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            role="img"
            aria-label="Shield"
          >
            <title>Shield</title>
            <path d="M12 2 4 6v6c0 5 3.5 8 8 10 4.5-2 8-5 8-10V6z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
        </span>
        <div>
          <h1>Agent Firewall</h1>
          <p>Guards what the agent does — not just what the model says.</p>
        </div>
      </div>
      <div className="conn" data-state={connection} role="status" aria-live="polite">
        <span className="conn-dot" />
        {LABEL[connection]}
      </div>
    </header>
  );
}
