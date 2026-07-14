import type { ReactNode } from "react";
import { Space, Typography } from "antd";

const { Title, Paragraph } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  extra?: ReactNode;
}

export function PageHeader({ title, subtitle, icon, extra }: PageHeaderProps) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: 16,
        marginBottom: 20,
        flexWrap: "wrap",
      }}
    >
      <Space align="start" size={14}>
        {icon && (
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: "var(--af-gradient)",
              display: "grid",
              placeItems: "center",
              color: "#fff",
              boxShadow: "var(--af-shadow-glow)",
              flexShrink: 0,
            }}
          >
            {icon}
          </div>
        )}
        <div>
          <Title level={3} style={{ margin: 0, letterSpacing: "-0.02em" }}>
            {title}
          </Title>
          {subtitle && (
            <Paragraph type="secondary" style={{ margin: "4px 0 0", maxWidth: 560 }}>
              {subtitle}
            </Paragraph>
          )}
        </div>
      </Space>
      {extra && <div>{extra}</div>}
    </div>
  );
}
