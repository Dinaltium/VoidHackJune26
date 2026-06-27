"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { BgAnimateButton } from "@/components/ui/bg-animate-button";

export function LaunchButton({ href, children }: { href: string; children: ReactNode }) {
  const router = useRouter();
  return (
    <BgAnimateButton
      gradient="oxblood"
      animation="spin-slow"
      rounded="xl"
      size="lg"
      onClick={() => router.push(href)}
    >
      {children}
    </BgAnimateButton>
  );
}
