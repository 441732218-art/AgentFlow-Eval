import React from "react";
import { Button as AntButton, type ButtonProps as AntButtonProps } from "antd";

interface ButtonProps extends Omit<AntButtonProps, "size"> {
  size?: "sm" | "md" | "lg";
}

const sizeMap: Record<string, AntButtonProps["size"]> = {
  sm: "small",
  md: "middle",
  lg: "large",
};

export const Button: React.FC<ButtonProps> = ({
  size = "md",
  children,
  ...props
}) => (
  <AntButton {...props} size={sizeMap[size]}>
    {children}
  </AntButton>
);
