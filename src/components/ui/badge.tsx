import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  tone = "neutral",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "accent" | "warn" | "ok" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide",
        tone === "neutral" && "bg-muted text-muted-foreground",
        tone === "accent" && "bg-accent/15 text-accent",
        tone === "warn" && "bg-warn/15 text-warn",
        tone === "ok" && "bg-ok/15 text-ok",
        className,
      )}
      {...props}
    />
  );
}
