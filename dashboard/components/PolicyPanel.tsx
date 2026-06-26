import type { Policy } from "@/lib/types";

function ChipRow({ items, kind }: { items: string[]; kind: "deny" | "allow" | "" }) {
  return (
    <div className="chips">
      {items.map((item) => (
        <span className={`chip ${kind}`.trim()} key={item}>
          {item}
        </span>
      ))}
    </div>
  );
}

export function PolicyPanel({ policy }: { policy: Policy | null }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <h2 className="panel-title">Active policy</h2>
        {policy ? (
          <span className="mono" style={{ color: "var(--faint)" }}>
            v{policy.version}
          </span>
        ) : null}
      </div>

      {policy === null ? (
        <p className="policy-desc">Policy unavailable — start the firewall on :8000.</p>
      ) : (
        <>
          <p className="policy-desc">{policy.description}</p>

          <div className="policy-group">
            <div className="policy-label">Denied tools</div>
            <ChipRow items={policy.tool_denylist} kind="deny" />
          </div>
          <div className="policy-group">
            <div className="policy-label">Allowed tools</div>
            <ChipRow items={policy.tool_allowlist} kind="allow" />
          </div>
          <div className="policy-group">
            <div className="policy-label">Egress allowlist</div>
            <ChipRow items={policy.egress_allowlist} kind="" />
          </div>
          <div className="policy-group">
            <div className="policy-label">Limits</div>
            <ChipRow
              items={[
                `injection ≥ ${policy.injection_threshold}`,
                `budget ${policy.token_budget_per_session} tok`,
              ]}
              kind=""
            />
          </div>
        </>
      )}
    </div>
  );
}
