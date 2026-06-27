"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Header } from "@/components/Header";
import {
  type ExecutedAction,
  getScenarios,
  type MissionResult,
  type MissionStep,
  runMission,
  type Scenario,
} from "@/lib/mission";

function fmtArgs(argsJson: string): string {
  try {
    const o = JSON.parse(argsJson || "{}") as Record<string, unknown>;
    return Object.entries(o)
      .map(([k, v]) => `${k}: ${String(v).slice(0, 60)}`)
      .join(" · ");
  } catch {
    return argsJson;
  }
}

function Verdict({ result }: { result: MissionResult }) {
  if (result.breached) {
    return (
      <div className="verdict verdict--breach">
        <span className="verdict-mark">✕</span>
        <div>
          <strong>Breach — {result.summary.dangerous_executed} dangerous action(s) executed</strong>
          <p>Unguarded, the agent acted on the injected instructions. Data left the building.</p>
        </div>
      </div>
    );
  }
  if (result.summary.blocked > 0) {
    return (
      <div className="verdict verdict--held">
        <span className="verdict-mark">🛡</span>
        <div>
          <strong>Firewall held — {result.summary.blocked} action(s) blocked</strong>
          <p>The agent was hijacked, but every dangerous call was stripped before it ran.</p>
        </div>
      </div>
    );
  }
  return (
    <div className="verdict verdict--clean">
      <span className="verdict-mark">✓</span>
      <div>
        <strong>Completed — no risky actions</strong>
        <p>The task finished within policy; nothing was blocked.</p>
      </div>
    </div>
  );
}

function StepCard({ step, n }: { step: MissionStep; n: number }) {
  const has = step.executed.length > 0 || step.blocked.length > 0;
  return (
    <div className="step">
      <div className="step-rail">
        <span className="step-dot" />
      </div>
      <div className="step-body">
        <div className="step-head">Step {n}</div>
        {step.thought ? <p className="step-thought">{step.thought}</p> : null}
        {!has && !step.thought ? <p className="step-thought">Thinking…</p> : null}
        {step.blocked.map((b) => (
          <div className="call call--block" key={`b-${b.name}-${b.arguments}`}>
            <span className="call-badge block">Blocked</span>
            <code className="mono">
              {b.name}({fmtArgs(b.arguments)})
            </code>
            <span className="call-reason">{b.reasons.join("; ")}</span>
          </div>
        ))}
        {step.executed.map((c) => (
          <div className="call call--exec" key={`e-${c.name}-${c.arguments}`}>
            <span className="call-badge exec">Ran</span>
            <code className="mono">
              {c.name}({fmtArgs(c.arguments)})
            </code>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActionRow({ a }: { a: ExecutedAction }) {
  return (
    <li className={a.dangerous ? "impact-item danger" : "impact-item safe"}>
      <span className="mono impact-tool">{a.tool}</span>
      <span className="impact-summary">{a.summary}</span>
    </li>
  );
}

export function MissionControl() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioId, setScenarioId] = useState("");
  const [task, setTask] = useState("");
  const [doc, setDoc] = useState("");
  const [firewallOn, setFirewallOn] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<MissionResult | null>(null);
  const [visible, setVisible] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getScenarios()
      .then((s) => {
        setScenarios(s);
        if (s[0]) {
          setScenarioId(s[0].id);
          setTask(s[0].task);
          setDoc(s[0].document);
        }
      })
      .catch(() => setError("Can't reach the firewall on :8000 — start it first."));
  }, []);

  const pickScenario = (id: string) => {
    const s = scenarios.find((x) => x.id === id);
    setScenarioId(id);
    if (s) {
      setTask(s.task);
      setDoc(s.document);
    }
  };

  // reveal steps one at a time for a live feel
  useEffect(() => {
    if (!result) return;
    setVisible(0);
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(() => {
      setVisible((v) => {
        if (v >= result.steps.length) {
          if (timer.current) clearInterval(timer.current);
          return v;
        }
        return v + 1;
      });
    }, 650);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [result]);

  const run = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    setVisible(0);
    try {
      const r = await runMission({
        scenario: scenarioId,
        task,
        document: doc,
        firewall: firewallOn,
      });
      setResult(r);
    } catch {
      setError("Mission failed — is the firewall running and the Groq key set?");
    } finally {
      setRunning(false);
    }
  }, [scenarioId, task, doc, firewallOn]);

  const done = result !== null && visible >= result.steps.length;

  return (
    <main className="app">
      <Header active="mission" />

      <div className="mc-bar">
        <label className="mc-field">
          <span>Scenario</span>
          <select
            value={scenarioId}
            onChange={(e) => pickScenario(e.target.value)}
            disabled={running}
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className={`switch ${firewallOn ? "on" : "off"}`}
          onClick={() => setFirewallOn((v) => !v)}
          disabled={running}
          aria-pressed={firewallOn}
        >
          <span className="switch-track">
            <span className="switch-thumb" />
          </span>
          Firewall {firewallOn ? "ON" : "OFF"}
        </button>

        <button type="button" className="btn btn--primary mc-run" onClick={run} disabled={running}>
          {running ? "Running agent…" : "Run agent"}
        </button>
        <span className="mc-model mono">llama-3.3-70b</span>
      </div>

      {error ? <div className="mc-error">{error}</div> : null}

      <div className="mc-grid">
        <section className="mc-left">
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Task</h2>
            </div>
            <textarea
              className="mc-input"
              rows={2}
              value={task}
              onChange={(e) => setTask(e.target.value)}
              disabled={running}
            />
            <div className="panel-head" style={{ marginTop: 14 }}>
              <h2 className="panel-title">Knowledge source the agent will read</h2>
              <span className="mono" style={{ color: "var(--faint)" }}>
                edit to plant an attack
              </span>
            </div>
            <textarea
              className="mc-input mc-doc"
              rows={7}
              value={doc}
              onChange={(e) => setDoc(e.target.value)}
              disabled={running}
            />
          </div>

          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Execution</h2>
              {result ? (
                <span className="mono" style={{ color: "var(--faint)" }}>
                  {result.summary.steps} steps
                </span>
              ) : null}
            </div>
            {!result ? (
              <div className="empty">
                <div>
                  <strong>{running ? "Agent is working…" : "No run yet"}</strong>
                  Pick a scenario, toggle the firewall, and run the agent to watch it act.
                </div>
              </div>
            ) : (
              <div className="steps">
                {result.steps.slice(0, visible).map((s, i) => (
                  <StepCard step={s} n={i + 1} key={s.index} />
                ))}
                {done && result.final_answer ? (
                  <div className="final">
                    <span className="call-badge exec">Answer</span>
                    <p>{result.final_answer}</p>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </section>

        <aside className="mc-right">
          {result && done ? <Verdict result={result} /> : null}

          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Impact</h2>
            </div>
            {!result ? (
              <p className="policy-desc">Run a mission to see what the agent attempted.</p>
            ) : (
              <>
                <div className="policy-label">Blocked attempts</div>
                {result.blocked_actions.length ? (
                  <ul className="impact-list">
                    {result.blocked_actions.map((b) => (
                      <li className="impact-item blocked" key={`${b.name}-${b.arguments}`}>
                        <span className="mono impact-tool">{b.name}</span>
                        <span className="impact-summary">{fmtArgs(b.arguments)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="policy-desc">None.</p>
                )}

                <div className="policy-label" style={{ marginTop: 14 }}>
                  Actions executed
                </div>
                {result.executed_actions.length ? (
                  <ul className="impact-list">
                    {result.executed_actions.map((a) => (
                      <ActionRow a={a} key={`${a.tool}-${a.summary}`} />
                    ))}
                  </ul>
                ) : (
                  <p className="policy-desc">None — nothing reached the outside world.</p>
                )}
              </>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
