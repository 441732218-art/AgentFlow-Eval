/* Shared loading skeletons for SaaS pages */

import { Card, Col, Row, Skeleton, Space } from "antd";

type SkeletonVariant = "dashboard" | "cards" | "detail" | "report" | "form" | "simple";

interface PageSkeletonProps {
  variant?: SkeletonVariant;
  rows?: number;
}

export function PageSkeleton({ variant = "simple", rows = 6 }: PageSkeletonProps) {
  if (variant === "simple") {
    return (
      <div className="af-page">
        <Card className="af-glass">
          <Skeleton active paragraph={{ rows: 4 }} />
        </Card>
      </div>
    );
  }

  if (variant === "form") {
    return (
      <div className="af-page">
        <Row gutter={[20, 20]}>
          <Col xs={24} lg={14}>
            <Card className="af-glass">
              <Skeleton active paragraph={{ rows: 8 }} />
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card className="af-glass">
              <Skeleton active paragraph={{ rows: 6 }} />
            </Card>
          </Col>
        </Row>
      </div>
    );
  }

  if (variant === "dashboard") {
    return (
      <div className="af-page">
        <Skeleton.Input active style={{ width: 220, marginBottom: 20 }} size="large" />
        <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <Col xs={12} lg={6} key={i}>
              <Card className="af-glass">
                <Skeleton active paragraph={{ rows: 2 }} title={false} />
              </Card>
            </Col>
          ))}
        </Row>
        <Row gutter={[16, 16]}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Col xs={24} lg={8} key={i}>
              <Card className="af-glass">
                <Skeleton active paragraph={{ rows: 5 }} />
              </Card>
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  if (variant === "cards") {
    return (
      <div className="af-page">
        <Space style={{ marginBottom: 16 }} size="middle">
          <Skeleton.Input active style={{ width: 200 }} />
          <Skeleton.Button active />
          <Skeleton.Button active />
        </Space>
        <Row gutter={[16, 16]}>
          {Array.from({ length: rows }).map((_, i) => (
            <Col xs={24} sm={12} xl={8} key={i}>
              <Card className="af-glass">
                <Skeleton active avatar paragraph={{ rows: 3 }} />
              </Card>
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  if (variant === "detail") {
    return (
      <div className="af-page">
        <Card className="af-glass" style={{ marginBottom: 16 }}>
          <Skeleton active paragraph={{ rows: 2 }} />
        </Card>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <Col xs={12} md={6} key={i}>
              <Card className="af-glass">
                <Skeleton active paragraph={{ rows: 1 }} title={false} />
              </Card>
            </Col>
          ))}
        </Row>
        <Card className="af-glass">
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      </div>
    );
  }

  // report
  return (
    <div className="af-page">
      <Skeleton.Input active style={{ width: 280, marginBottom: 20 }} size="large" />
      <Card className="af-glass" style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col xs={24} md={8} style={{ textAlign: "center" }}>
            <Skeleton.Avatar active size={140} shape="circle" />
          </Col>
          <Col xs={24} md={16}>
            <Skeleton active paragraph={{ rows: 4 }} />
          </Col>
        </Row>
      </Card>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card className="af-glass">
            <Skeleton active paragraph={{ rows: 6 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card className="af-glass">
            <Skeleton active paragraph={{ rows: 6 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default PageSkeleton;
