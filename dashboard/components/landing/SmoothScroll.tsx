"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { type LenisRef, ReactLenis } from "lenis/react";
import { type ReactNode, useEffect, useRef } from "react";

gsap.registerPlugin(ScrollTrigger);

/** Lenis smooth scrolling driven by the GSAP ticker (so scrubbed/pinned
 *  ScrollTriggers stay in lockstep). Wraps the landing only. */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const lenisRef = useRef<LenisRef>(null);

  useEffect(() => {
    // drive Lenis from GSAP's ticker — added unconditionally; the callback
    // no-ops until the Lenis instance is mounted.
    const update = (time: number) => {
      lenisRef.current?.lenis?.raf(time * 1000);
    };
    gsap.ticker.add(update);
    gsap.ticker.lagSmoothing(0);

    const id = window.setTimeout(() => {
      lenisRef.current?.lenis?.on("scroll", ScrollTrigger.update);
    }, 0);

    return () => {
      gsap.ticker.remove(update);
      window.clearTimeout(id);
      lenisRef.current?.lenis?.off("scroll", ScrollTrigger.update);
    };
  }, []);

  return (
    <ReactLenis root ref={lenisRef} options={{ autoRaf: false, lerp: 0.1, smoothWheel: true }}>
      {children}
    </ReactLenis>
  );
}
