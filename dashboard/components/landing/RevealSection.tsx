"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useRef } from "react";
import { cn } from "@/lib/utils";

gsap.registerPlugin(ScrollTrigger, useGSAP);

export type RevealPart = { text: string; block?: string; color?: string };
type Part = string | RevealPart;

interface WordSpec {
  word: string;
  block?: string;
  color?: string;
}

function flatten(parts: Part[]): WordSpec[] {
  return parts.flatMap((p) => {
    const part: RevealPart = typeof p === "string" ? { text: p } : p;
    return part.text
      .split(" ")
      .filter(Boolean)
      .map((word) => ({ word, block: part.block, color: part.color }));
  });
}

interface Props {
  parts: Part[];
  className?: string;
  /** how much scroll the section pins for — higher = slower, more scroll. */
  length?: number;
  /** scroll-distance gap between consecutive words — higher = slower cascade. */
  stagger?: number;
}

/** A full-height section that pins while you scroll: the squircle covers lift
 *  word-by-word to reveal the text, all without the section moving. */
export function RevealSection({ parts, className, length = 1, stagger = 0.6 }: Props) {
  const ref = useRef<HTMLElement>(null);
  const specs = flatten(parts);

  useGSAP(
    () => {
      const root = ref.current;
      if (!root) return;
      const blocks = root.querySelectorAll<HTMLElement>("[data-block]");
      const texts = root.querySelectorAll<HTMLElement>("[data-text]");

      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        gsap.set(texts, { opacity: 1 });
        gsap.set(blocks, { opacity: 0 });
        return;
      }

      gsap.set(texts, { opacity: 0 });
      gsap.set(blocks, { opacity: 1 });

      const dist = Math.round(window.innerHeight * 1.15 * length) + 240;
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: root,
          start: "top top",
          end: `+=${dist}`,
          pin: true,
          scrub: 0.6,
          anticipatePin: 1,
        },
      });
      tl.to(texts, { opacity: 1, ease: "none", duration: stagger, stagger }, 0);
      tl.to(blocks, { opacity: 0, ease: "none", duration: stagger, stagger }, stagger * 0.3);
    },
    { scope: ref },
  );

  return (
    <section ref={ref} className={cn("reveal-section", className)}>
      <p className="lp-manifesto">
        {specs.map((spec, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: static word list, index is stable identity
          <span className="sr-word" key={i}>
            <span className="sr-text" data-text style={{ color: spec.color }}>
              {spec.word}
            </span>
            <span
              className="sr-block"
              data-block
              aria-hidden="true"
              style={{ background: spec.block }}
            />
          </span>
        ))}
      </p>
    </section>
  );
}
