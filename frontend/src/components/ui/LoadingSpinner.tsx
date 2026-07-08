import React from "react";
import { Spin } from "antd";

interface LoadingSpinnerProps {
  fullScreen?: boolean;
  size?: "sm" | "md" | "lg";
  tip?: string;
}

const sizeMap = { sm: "small", md: "default", lg: "large" } as const;

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  fullScreen = false,
  size = "md",
  tip,
}) => {
  const spinner = <Spin size={sizeMap[size]} tip={tip} />;
  if (fullScreen) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          width: "100vw",
        }}
      >
        {spinner}
      </div>
    );
  }
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: 48,
      }}
    >
      {spinner}
    </div>
  );
};
