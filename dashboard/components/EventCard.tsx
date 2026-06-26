import type { FirewallEvent } from "@/lib/types";

type Bucket = "allow" | "flag" | "block";

function visual(event: FirewallEvent): { bucket: Bucket; label: string } {
  if (event.action === "block") return { bucket: "block", label: "Block" };
  if (event.action === "redact") return { bucket: "flag", label: "Redact" };
  if (event.status === "flag") return { bucket: "flag", label: "Flag" };
  return { bucket: "allow", label: "Allow" };
}

function clockTime(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString([], { hour12: false });
}

export function EventCard({ event }: { event: FirewallEvent }) {
  const { bucket, label } = visual(event);
  const cls = bucket === "allow" ? "event" : `event event--${bucket}`;
  return (
    <article className={cls} data-action={event.action} data-testid="event-card">
      <span className={`badge ${bucket}`}>{label}</span>
      <div className="event-main">
        <h3 className="event-title">{event.title}</h3>
        {event.detail ? <p className="event-detail">{event.detail}</p> : null}
        <div className="event-meta">
          {event.rule ? <span className="mono">rule: {event.rule}</span> : null}
          <span className="mono">session: {event.session_id}</span>
          {event.receipt_id ? <span className="mono">{event.receipt_id}</span> : null}
          <span>{clockTime(event.ts)}</span>
        </div>
      </div>
    </article>
  );
}
