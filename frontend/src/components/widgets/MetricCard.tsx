import { memo } from "react";
import clsx from "clsx";

export type MetricTone = "cyan" | "success" | "warning" | "danger" | "purple";

type MetricCardProps = {
  label: string;
  value: string | number;
  hint?: string;
  tone?: MetricTone;
  icon?: React.ReactNode;
  onClick?: () => void;
};

export const MetricCard = memo(function MetricCard({
  label,
  value,
  hint,
  tone = "cyan",
  icon,
  onClick,
}: MetricCardProps) {
  return (
    <div
      className={clsx("ic-metric", `ic-metric--${tone}`)}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      style={{ cursor: onClick ? "pointer" : "default" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div className="ic-metric__label">{label}</div>
        {icon ? <span style={{ opacity: 0.85, fontSize: 18 }}>{icon}</span> : null}
      </div>
      <div className="ic-metric__value">{value}</div>
      {hint ? <div className="ic-metric__hint">{hint}</div> : null}
    </div>
  );
});
