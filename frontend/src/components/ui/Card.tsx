import React from "react";
import { Card as AntCard, type CardProps } from "antd";

interface AppCardProps extends CardProps {
  padding?: number | string;
}

export const Card: React.FC<AppCardProps> = ({
  padding = 24,
  children,
  bodyStyle,
  ...props
}) => (
  <AntCard
    {...props}
    bodyStyle={{ padding, ...bodyStyle }}
    style={{ borderRadius: 8, ...props.style }}
  >
    {children}
  </AntCard>
);
