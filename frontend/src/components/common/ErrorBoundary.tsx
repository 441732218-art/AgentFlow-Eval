/* (c) 2026 AgentFlow-Eval */
/* Global error boundary — Deep Space styled */

import React from "react";
import { Button, Result, Typography, Space } from "antd";
import { ReloadOutlined, HomeOutlined } from "@ant-design/icons";

const { Paragraph, Text } = Typography;

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

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleHome = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = "/";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            padding: 24,
            background: "var(--af-bg-base, #07090f)",
          }}
        >
          <div
            className="af-glass"
            style={{ maxWidth: 520, width: "100%", padding: "28px 20px" }}
          >
            <Result
              status="error"
              title={<span className="af-gradient-text">页面出现异常</span>}
              subTitle="已捕获前端运行时错误，可重试或返回首页。"
              extra={
                <Space wrap>
                  <Button
                    type="primary"
                    icon={<ReloadOutlined />}
                    onClick={this.handleReset}
                    style={{ background: "var(--af-gradient)", border: "none" }}
                  >
                    重试
                  </Button>
                  <Button icon={<HomeOutlined />} onClick={this.handleHome}>
                    回首页
                  </Button>
                </Space>
              }
            />
            {this.state.error?.message && (
              <Paragraph
                code
                copyable
                style={{
                  margin: "0 16px 8px",
                  fontSize: 12,
                  maxHeight: 120,
                  overflow: "auto",
                }}
              >
                <Text type="secondary">{this.state.error.message}</Text>
              </Paragraph>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
