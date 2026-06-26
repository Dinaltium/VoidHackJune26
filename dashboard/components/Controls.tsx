"use client";

import { useState } from "react";

interface Props {
  onDemo: () => Promise<void>;
  onReset: () => Promise<void>;
}

export function Controls({ onDemo, onReset }: Props) {
  const [busy, setBusy] = useState(false);

  const wrap = (fn: () => Promise<void>) => async () => {
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-head">
        <h2 className="panel-title">Demo</h2>
      </div>
      <p className="policy-desc">
        Replay a spread of attacks — credential exfil, bad egress, secret leak, indirect injection,
        runaway cost — through the live engine.
      </p>
      <div className="controls">
        <button type="button" className="btn btn--primary" onClick={wrap(onDemo)} disabled={busy}>
          {busy ? "Running…" : "Run demo attack"}
        </button>
        <button type="button" className="btn btn--ghost" onClick={wrap(onReset)} disabled={busy}>
          Reset
        </button>
      </div>
    </div>
  );
}
