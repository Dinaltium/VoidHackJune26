"use client";

import { type MotionValue, motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import { useRef } from "react";

/** A run of words sharing one squircle/text color. `block` overrides the cover
 *  color, `color` overrides the revealed text color (e.g. highlight a phrase). */
export type RevealPart = { text: string; block?: string; color?: string };
type Part = string | RevealPart;

interface WordSpec {
  word: string;
  block?: string;
  color?: string;
}

function RevealWord({
  spec,
  progress,
  range,
}: {
  spec: WordSpec;
  progress: MotionValue<number>;
  range: [number, number];
}) {
  const [start, end] = range;
  const mid = start + (end - start) * 0.55;
  // text draws in behind the cover, then the squircle lifts off to reveal it
  const textOpacity = useTransform(progress, [start, mid, end], [0, 1, 1]);
  const blockOpacity = useTransform(progress, [start, mid, end], [1, 1, 0]);

  return (
    <span className="sr-word">
      <motion.span className="sr-text" style={{ opacity: textOpacity, color: spec.color }}>
        {spec.word}
      </motion.span>
      <motion.span
        aria-hidden="true"
        className="sr-block"
        style={{ opacity: blockOpacity, background: spec.block }}
      />
    </span>
  );
}

export function ScrollReveal({ parts, className }: { parts: Part[]; className?: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.82", "start 0.28"] });

  const specs: WordSpec[] = parts.flatMap((p) => {
    const part: RevealPart = typeof p === "string" ? { text: p } : p;
    return part.text
      .split(" ")
      .filter(Boolean)
      .map((word) => ({ word, block: part.block, color: part.color }));
  });

  if (reduce) {
    return <p className={className}>{specs.map((s) => s.word).join(" ")}</p>;
  }

  return (
    <p ref={ref} className={className}>
      {specs.map((spec, i) => {
        const start = i / specs.length;
        const end = start + 1 / specs.length;
        return (
          // biome-ignore lint/suspicious/noArrayIndexKey: static word list, index is stable identity
          <RevealWord key={i} spec={spec} progress={scrollYProgress} range={[start, end]} />
        );
      })}
    </p>
  );
}
