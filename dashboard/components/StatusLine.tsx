import type { Stats } from "@/lib/types";

const ITEMS: { key: keyof Stats; cls: string; label: string }[] = [
  { key: "allow", cls: "allow", label: "Allowed" },
  { key: "redact", cls: "flag", label: "Redacted" },
  { key: "block", cls: "block", label: "Blocked" },
];

export function StatusLine({ stats }: { stats: Stats }) {
  return (
    <div className="statusline">
      {ITEMS.map((item) => (
        <div className="stat" key={item.key}>
          <div className="stat-top">
            <span className={`stat-dot ${item.cls}`} />
            {item.label}
          </div>
          <div className="stat-num">{stats[item.key]}</div>
        </div>
      ))}
    </div>
  );
}
