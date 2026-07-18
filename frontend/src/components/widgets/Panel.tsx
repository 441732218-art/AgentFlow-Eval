import type { ReactNode } from "react";
import clsx from "clsx";

type PanelProps = {
  title?: ReactNode;
  extra?: ReactNode;
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
};

export function Panel({ title, extra, children, className, style, bodyStyle }: PanelProps) {
  return (
    <div className={clsx("ic-panel", className)} style={{ padding: 16, ...style }}>
      {(title || extra) && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 12,
            gap: 12,
          }}
        >
          <div className="ic-panel-title" style={{ marginBottom: 0 }}>
            {title}
          </div>
          {extra}
        </div>
      )}
      <div style={bodyStyle}>{children}</div>
    </div>
  );
}
