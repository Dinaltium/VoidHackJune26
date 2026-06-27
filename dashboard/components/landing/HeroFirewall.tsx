// Looping "live firewall" hero scene: an agent's actions stream toward the gate;
// a benign one passes (green), a malicious one is stripped (red ✕). Pure CSS
// animation; a static, fully-legible composition shows under reduced-motion.
export function HeroFirewall() {
  return (
    <svg
      className="hero-scene"
      viewBox="0 0 560 320"
      role="img"
      aria-label="An AI agent's actions pass through the firewall; a malicious send_email is blocked while a safe read passes through."
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <radialGradient id="fwglow" cx="50%" cy="50%" r="60%">
          <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="var(--brand)" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* rails */}
      <line className="hs-rail" x1="156" y1="160" x2="240" y2="160" />
      <line className="hs-rail" x1="360" y1="160" x2="404" y2="160" />

      {/* nodes */}
      <g className="hs-node">
        <rect x="24" y="120" width="132" height="80" rx="14" />
        <text className="hs-title" x="90" y="156" textAnchor="middle">
          AI agent
        </text>
        <text className="hs-sub" x="90" y="176" textAnchor="middle">
          autonomous
        </text>
      </g>

      <ellipse className="hs-glow" cx="300" cy="160" rx="120" ry="120" fill="url(#fwglow)" />
      <g className="hs-gate">
        <rect x="240" y="64" width="120" height="192" rx="18" />
        <text className="hs-gate-label" x="300" y="92" textAnchor="middle">
          FIREWALL
        </text>
        <rect className="hs-scan" x="252" y="104" width="96" height="2" rx="1" />
      </g>

      <g className="hs-node">
        <rect x="404" y="120" width="132" height="80" rx="14" />
        <text className="hs-title" x="470" y="152" textAnchor="middle">
          tools · world
        </text>
        <text className="hs-sub" x="470" y="172" textAnchor="middle">
          email · http · shell
        </text>
      </g>

      {/* packets */}
      <g className="hs-pass">
        <circle r="8" cx="156" cy="160" />
        <text className="hs-pktlabel" x="156" y="140" textAnchor="middle">
          read_doc
        </text>
      </g>
      <g className="hs-block">
        <circle r="8" cx="156" cy="160" />
        <text className="hs-pktlabel" x="156" y="140" textAnchor="middle">
          send_email → attacker
        </text>
      </g>

      {/* block flash at the gate */}
      <g className="hs-flash" transform="translate(300 160)">
        <circle r="20" />
        <path d="M-7 -7 L7 7 M7 -7 L-7 7" />
      </g>
    </svg>
  );
}
