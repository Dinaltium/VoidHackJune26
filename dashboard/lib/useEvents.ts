"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FIREWALL_URL } from "./api";
import type { FirewallEvent, Stats } from "./types";

type Connection = "connecting" | "live" | "down";

const EMPTY_STATS: Stats = { allow: 0, redact: 0, block: 0, total: 0 };

/** Subscribes to the firewall SSE stream and keeps a rolling event list + live tallies. */
export function useEvents(max = 60) {
  const [events, setEvents] = useState<FirewallEvent[]>([]);
  const [stats, setStats] = useState<Stats>(EMPTY_STATS);
  const [connection, setConnection] = useState<Connection>("connecting");
  const sourceRef = useRef<EventSource | null>(null);

  const tally = useCallback((action: FirewallEvent["action"]) => {
    setStats((s) => ({
      ...s,
      [action]: s[action] + 1,
      total: s.total + 1,
    }));
  }, []);

  useEffect(() => {
    const source = new EventSource(`${FIREWALL_URL}/events`);
    sourceRef.current = source;

    source.onopen = () => setConnection("live");
    source.onerror = () => setConnection("down");
    source.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as FirewallEvent;
        setEvents((prev) => [event, ...prev].slice(0, max));
        tally(event.action);
      } catch {
        /* ignore keepalive / malformed frames */
      }
    };

    return () => source.close();
  }, [max, tally]);

  const clear = useCallback(() => {
    setEvents([]);
    setStats(EMPTY_STATS);
  }, []);

  return { events, stats, connection, clear };
}
