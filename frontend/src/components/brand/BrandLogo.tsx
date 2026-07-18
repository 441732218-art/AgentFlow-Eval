/**
 * AgentFlow Intelligence — brand mark + wordmark.
 * Assets: /assets/logo/*
 */

import clsx from "clsx";
import { isDarkTheme, useThemeStore } from "@/stores/useThemeStore";

export type BrandLogoVariant = "mark" | "full" | "lockup";

type BrandLogoProps = {
  variant?: BrandLogoVariant;
  /** Pixel height of the mark / full logo */
  size?: number;
  className?: string;
  /** Subtle core pulse (loading / splash) */
  animated?: boolean;
  /** Force dark|light asset (defaults to theme) */
  colorScheme?: "dark" | "light" | "auto";
  title?: string;
  onClick?: () => void;
};

const PATHS = {
  mark: "/assets/logo/logo.svg",
  dark: "/assets/logo/logo-dark.svg",
  light: "/assets/logo/logo-light.svg",
} as const;

export function BrandLogo({
  variant = "mark",
  size = 34,
  className,
  animated = false,
  colorScheme = "auto",
  title = "AgentFlow Intelligence",
  onClick,
}: BrandLogoProps) {
  const mode = useThemeStore((s) => s.mode);
  const dark =
    colorScheme === "auto"
      ? isDarkTheme(mode)
      : colorScheme === "dark";

  if (variant === "full") {
    const src = dark ? PATHS.dark : PATHS.light;
    const h = size;
    const w = Math.round(h * (420 / 96));
    return (
      <img
        src={src}
        alt={title}
        width={w}
        height={h}
        className={clsx("afi-logo", animated && "afi-logo--animated", className)}
        style={{ display: "block", height: h, width: w }}
        draggable={false}
        onClick={onClick}
      />
    );
  }

  if (variant === "lockup") {
    return (
      <div
        className={clsx("afi-logo-lockup", animated && "afi-logo--animated", className)}
        onClick={onClick}
        style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}
      >
        <img
          src={PATHS.mark}
          alt=""
          width={size}
          height={size}
          className="afi-logo afi-logo--mark"
          style={{
            display: "block",
            width: size,
            height: size,
            borderRadius: Math.round(size * 0.22),
            boxShadow: "var(--af-shadow-glow)",
            flexShrink: 0,
          }}
          draggable={false}
        />
        <div style={{ minWidth: 0, lineHeight: 1.15 }}>
          <div
            className="af-gradient-text"
            style={{
              fontWeight: 800,
              fontSize: Math.max(13, Math.round(size * 0.42)),
              letterSpacing: "-0.02em",
            }}
          >
            AgentFlow
          </div>
          <div className="ic-brand-sub" style={{ fontSize: Math.max(9, Math.round(size * 0.28)) }}>
            Intelligence
          </div>
        </div>
      </div>
    );
  }

  // mark
  return (
    <img
      src={PATHS.mark}
      alt={title}
      width={size}
      height={size}
      className={clsx("afi-logo afi-logo--mark", animated && "afi-logo--animated", className)}
      style={{
        display: "block",
        width: size,
        height: size,
        borderRadius: Math.round(size * 0.22),
        boxShadow: "var(--af-shadow-glow)",
      }}
      draggable={false}
      onClick={onClick}
    />
  );
}

export const BRAND = {
  name: "AgentFlow Intelligence",
  shortName: "AgentFlow",
  tagline: "Agent Observability & Evaluation Platform",
  paths: PATHS,
} as const;
