import type { ReactNode } from "react";
import { Typography } from "antd";
import clsx from "clsx";

const { Title, Paragraph } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  extra?: ReactNode;
  /** Show LIVE pulse badge (Command Center) */
  live?: boolean;
  liveLabel?: string;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  icon,
  extra,
  live,
  liveLabel = "Live",
  className,
}: PageHeaderProps) {
  return (
    <div className={clsx("ic-page-header", className)}>
      <div className="ic-page-header__main">
        {icon ? <div className="ic-page-header__icon">{icon}</div> : null}
        <div className="ic-page-header__text">
          <div className="ic-page-header__title-row">
            <Title level={3} className="ic-page-header__title">
              {title}
            </Title>
            {live ? (
              <span className="ic-live-badge">
                <span className="af-live-dot" /> {liveLabel}
              </span>
            ) : null}
          </div>
          {subtitle ? (
            <Paragraph type="secondary" className="ic-page-header__sub">
              {subtitle}
            </Paragraph>
          ) : null}
        </div>
      </div>
      {extra ? <div className="ic-page-header__extra">{extra}</div> : null}
    </div>
  );
}

/** Compact toolbar row under page header (filters / actions) */
export function PageToolbar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={clsx("ic-toolbar", className)}>{children}</div>;
}
