"use client";

import { useEffect, useState } from "react";
import { getPolicy, resetStore, runDemo } from "@/lib/api";
import type { Policy } from "@/lib/types";
import { useEvents } from "@/lib/useEvents";
import { Controls } from "./Controls";
import { EventCard } from "./EventCard";
import { Header } from "./Header";
import { PolicyPanel } from "./PolicyPanel";
import { StatusLine } from "./StatusLine";

export function Dashboard() {
  const { events, stats, clear } = useEvents();
  const [policy, setPolicy] = useState<Policy | null>(null);

  useEffect(() => {
    getPolicy()
      .then(setPolicy)
      .catch(() => setPolicy(null));
  }, []);

  const onDemo = async () => {
    await runDemo().catch(() => undefined);
  };
  const onReset = async () => {
    await resetStore().catch(() => undefined);
    clear();
  };

  return (
    <main className="app">
      <Header active="feed" />
      <StatusLine stats={stats} />

      <div className="layout">
        <section className="panel" aria-label="Live activity">
          <div className="panel-head">
            <h2 className="panel-title">Live activity</h2>
            <span className="mono" style={{ color: "var(--faint)" }}>
              {events.length} event{events.length === 1 ? "" : "s"}
            </span>
          </div>

          {events.length === 0 ? (
            <div className="empty">
              <div>
                <strong>No agent activity yet</strong>
                Run the demo, or point an agent at <span className="mono">:8000/v1</span> to watch
                decisions stream in.
              </div>
            </div>
          ) : (
            <div className="feed">
              {events.map((event) => (
                <EventCard event={event} key={event.id} />
              ))}
            </div>
          )}
        </section>

        <aside className="sidebar">
          <Controls onDemo={onDemo} onReset={onReset} />
          <PolicyPanel policy={policy} onPolicyUpdated={setPolicy} />
        </aside>
      </div>
    </main>
  );
}
