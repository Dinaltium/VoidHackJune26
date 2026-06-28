import Image from "next/image";
import Link from "next/link";
import { BackgroundImageTexture } from "@/components/ui/bg-image-texture";
import { ThemeToggleButton } from "@/components/ui/skiper-ui/skiper26";
import { HeroDefender } from "./HeroDefender";
import { LaunchButton } from "./LaunchButton";
import { RevealSection } from "./RevealSection";
import { SmoothScroll } from "./SmoothScroll";

const GITHUB = "https://github.com/Dinaltium/VoidHackJune26";

const PIPELINE = [
  { k: "1", name: "Deterministic rules", note: "tool + egress + secret · 0ms" },
  { k: "2", name: "Prompt Guard 2", note: "injection on tool results" },
  { k: "3", name: "PII redaction", note: "secrets masked in flight" },
  { k: "4", name: "Cost guard", note: "per-session budget" },
  { k: "5", name: "Safeguard reasoner", note: "policy-following, selective" },
];

function Shield() {
  return (
    <svg
      width="22"
      height="22"
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
  );
}

export function Landing() {
  return (
    <SmoothScroll>
      <BackgroundImageTexture variant="debut-light" opacity={0.8} className="lp">
        <nav className="lp-nav">
          <span className="lp-brand">
            <span className="lp-brand-mark">
              <Shield />
            </span>
            Agent Defender
          </span>
          <div className="lp-nav-right">
            <a href="#evidence">Evidence</a>
            <a href="#how">How it works</a>
            <a href="#proof">Proof</a>
            <a href={GITHUB} target="_blank" rel="noreferrer">
              GitHub
            </a>
            <ThemeToggleButton
              variant="rectangle"
              start="bottom-up"
              blur={false}
              className="size-9"
            />
            <LaunchButton href="/console" size="default">
              Launch console
            </LaunchButton>
          </div>
        </nav>

        {/* hero */}
        <header className="lp-hero">
          <div className="lp-hero-copy">
            <h1 className="lp-h1">Guard every action your AI&nbsp;agents take.</h1>
            <p className="lp-lede">
              Prompt injection is unsolved. Guardrails check what the model <em>says</em> — Agent
              Defender checks what the agent <em>does</em>, and strips the dangerous calls before
              they run.
            </p>
            <div className="lp-actions">
              <LaunchButton href="/console">Launch console</LaunchButton>
              <Link className="lp-ghost" href="/mission">
                See it block an attack →
              </Link>
            </div>
          </div>
          <div className="lp-hero-art">
            <HeroDefender />
          </div>
        </header>

        {/* manifesto — pinned scroll reveal */}
        <RevealSection
          length={1.1}
          parts={[
            "Guardrails check what the model says. We check what the agent",
            { text: "does", block: "var(--brand)", color: "var(--brand)" },
            "— and strip the dangerous calls before they ever reach the world.",
          ]}
        />

        {/* the gap */}
        <section className="lp-section">
          <h2 className="lp-h2">Guardrails read text. Damage happens in actions.</h2>
          <p className="lp-sub">
            A classifier can approve a prompt and still let the agent exfiltrate a secret in the
            very next call. The action is where the defender lives.
          </p>
          <div className="lp-versus">
            <article className="lp-vs lp-vs--bad">
              <div className="lp-vs-head">Text guardrail</div>
              <ol>
                <li>Reads the prompt, approves the words</li>
                <li className="bad">Agent emails the API key to an attacker</li>
              </ol>
              <span className="lp-tag bad">Breach</span>
            </article>
            <article className="lp-vs lp-vs--good">
              <div className="lp-vs-head">Agent Defender</div>
              <ol>
                <li>Inspects the action the model emitted</li>
                <li className="good">Strips send_email before the agent can run it</li>
              </ol>
              <span className="lp-tag good">Held</span>
            </article>
          </div>
        </section>

        {/* evidence — grounded in the threat research */}
        <section className="lp-section lp-evidence" id="evidence">
          <h2 className="lp-h2">This isn&apos;t hypothetical.</h2>
          <p className="lp-sub">
            The action layer is unguarded across the industry — and attackers are already through
            it. The research is consistent: assume injection will succeed, and govern the action.
          </p>
          <div className="lp-evidence-grid">
            <article className="lp-ev">
              <div className="lp-ev-stat">88%</div>
              <p className="lp-ev-body">
                of organizations running AI agents reported a security incident — missing or
                misconfigured guardrails a leading cause.
              </p>
              <span className="lp-ev-src mono">Gravitee AI security survey</span>
            </article>
            <article className="lp-ev">
              <div className="lp-ev-stat">#1</div>
              <p className="lp-ev-body">
                Prompt injection is the top risk on the OWASP GenAI Top 10 (2025) — found in 73% of
                production deployments reviewed.
              </p>
              <span className="lp-ev-src mono">OWASP GenAI Top 10 · 2025</span>
            </article>
            <article className="lp-ev">
              <div className="lp-ev-stat lp-ev-stat--glyph">✉</div>
              <p className="lp-ev-body">
                OpenAI&apos;s ChatGPT Atlas was hijacked by a hidden instruction in an email — it
                acted on the attacker&apos;s words instead of the user&apos;s task.
              </p>
              <span className="lp-ev-src mono">OpenAI Atlas red-team</span>
            </article>
          </div>
          <p className="lp-evidence-foot">
            Agent Defender implements the controls these reports recommend — an external policy
            engine, tool + argument allowlisting, output inspection, and a tamper-evident audit
            trail — enforced at the action layer. Figures compiled in{" "}
            <a href={`${GITHUB}/blob/main/docs/RESEARCH.md`} target="_blank" rel="noreferrer">
              docs/RESEARCH.md
            </a>
            .
          </p>
        </section>

        {/* how it works */}
        <section className="lp-section" id="how">
          <h2 className="lp-h2">One base_url. Every action checked.</h2>
          <p className="lp-sub">
            Point your agent at the defender — nothing else changes. Each tool call runs a
            deterministic-first pipeline; the model-backed layers light up only when they need to.
            Fail-closed by default.
          </p>

          <div className="lp-pipeline">
            {PIPELINE.map((s) => (
              <div className="lp-stage" key={s.k}>
                <span className="lp-stage-k mono">{s.k}</span>
                <span className="lp-stage-name">{s.name}</span>
                <span className="lp-stage-note">{s.note}</span>
              </div>
            ))}
          </div>

          <pre className="lp-code mono">
            <code>
              <span className="c-key">from</span> openai <span className="c-key">import</span>{" "}
              OpenAI
              {"\n"}
              client = OpenAI(base_url=
              <span className="c-str">&quot;https://your-defender/v1&quot;</span>){"\n"}
              <span className="c-com"># every tool call the agent makes is now governed</span>
            </code>
          </pre>
        </section>

        {/* proof */}
        <section className="lp-section" id="proof">
          <h2 className="lp-h2">Watch an agent get hijacked — and held.</h2>
          <p className="lp-sub">
            Mission Control runs a real LLM against a poisoned document. The model takes the bait;
            the defender strips every dangerous call and signs the decision. Toggle it off to watch
            the same agent breach.
          </p>
          <div className="lp-shots">
            <figure>
              <Image
                src="/shots/mission.png"
                alt="Mission Control showing the defender blocking three send_email attempts with a 'Firewall held' verdict"
                width={1440}
                height={900}
                sizes="(max-width: 820px) 100vw, 50vw"
              />
              <figcaption>Mission Control — agent hijacked, defender held.</figcaption>
            </figure>
            <figure>
              <Image
                src="/shots/console.png"
                alt="Live feed dashboard streaming blocked, redacted, and flagged defender decisions"
                width={1440}
                height={900}
                sizes="(max-width: 820px) 100vw, 50vw"
              />
              <figcaption>Live feed — every decision, as it happens.</figcaption>
            </figure>
          </div>
        </section>

        {/* audit */}
        <section className="lp-section lp-audit">
          <div>
            <h2 className="lp-h2">Every decision, signed.</h2>
            <p className="lp-sub">
              Each block is a tamper-evident receipt — HMAC-signed over the action, the rule that
              fired, and the reasoning. An audit trail you can verify, not a log you have to trust.
            </p>
          </div>
          <div className="lp-receipt mono">
            <div className="lp-receipt-row">
              <span>action</span>
              <span className="block">block</span>
            </div>
            <div className="lp-receipt-row">
              <span>rule</span>
              <span>deterministic_rules</span>
            </div>
            <div className="lp-receipt-row">
              <span>reason</span>
              <span>tool &apos;send_email&apos; is denied</span>
            </div>
            <div className="lp-receipt-row">
              <span>signature</span>
              <span>c2539dec…ad33</span>
            </div>
            <div className="lp-receipt-verified">✓ verified</div>
          </div>
        </section>

        {/* second reveal — theme tie-in */}
        <RevealSection
          length={1.1}
          parts={[
            "Most people only see interfaces. The defender is the",
            { text: "invisible operating layer", block: "var(--brand)", color: "var(--brand)" },
            "that decides what every agent is allowed to do.",
          ]}
        />

        {/* close */}
        <section className="lp-close">
          <h2 className="lp-close-h">The operating layer for AI agents.</h2>
          <div className="lp-actions">
            <LaunchButton href="/console">Launch console</LaunchButton>
            <a className="lp-ghost" href={GITHUB} target="_blank" rel="noreferrer">
              View on GitHub →
            </a>
          </div>
        </section>

        <footer className="lp-footer">
          <span>Agent Defender</span>
          <span className="mono">VoidHack June 2026 · The Operating Layer of the Internet</span>
        </footer>
      </BackgroundImageTexture>
    </SmoothScroll>
  );
}
