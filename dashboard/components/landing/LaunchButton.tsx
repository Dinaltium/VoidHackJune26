"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { BgAnimateButton } from "@/components/ui/bg-animate-button";

export function LaunchButton({
  href,
  children,
  size = "lg",
  rounded = "xl",
}: {
  href: string;
  children: ReactNode;
  size?: "sm" | "lg" | "default";
  rounded?: "full" | "xl" | "2xl" | "3xl" | "sm" | "xs" | "base";
}) {
  const router = useRouter();
  return (
    <BgAnimateButton
      gradient="oxblood"
      animation="spin-slow"
      rounded={rounded}
      size={size}
      onClick={() => router.push(href)}
    >
      {children}
    </BgAnimateButton>
  );
}
