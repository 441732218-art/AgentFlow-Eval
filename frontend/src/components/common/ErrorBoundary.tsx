/* (c) 2026 AgentFlow-Eval */
/* 全局错误边界组件 */

import React from "react";
import { Button, Result } from "antd";

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<
  React.PropsWithChildren,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面出现错误"
          subTitle={this.state.error?.message || "未知错误"}
          extra={
            <Button type="primary" onClick={this.handleReset}>
              重试
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
