import type { ReactNode, CSSProperties } from "react";
import clsx from "clsx";
import { PageHeader } from "@/components/ui/PageHeader";

export type PageShellProps = {
  /** Optional standard header — when omitted, children own the title area */
  title?: string;
  subtitle?: string;
  icon?: ReactNode;
  extra?: ReactNode;
  live?: boolean;
  liveLabel?: string;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  /** Tight spacing for dense command views */
  dense?: boolean;
};

/**
 * Unified page wrapper for Intelligence Center + legacy business pages.
 * Applies Command Center animation, density, and optional PageHeader.
 */
export function PageShell({
  title,
  subtitle,
  icon,
  extra,
  live,
  liveLabel,
  children,
  className,
  style,
  dense,
}: PageShellProps) {
  return (
    <div
      className={clsx("ic-page", "af-page", dense && "ic-page--dense", className)}
      style={style}
    >
      {title ? (
        <PageHeader
          title={title}
          subtitle={subtitle}
          icon={icon}
          extra={extra}
          live={live}
          liveLabel={liveLabel}
        />
      ) : null}
      {children}
    </div>
  );
}
