/* Shared loading skeletons — Command Center density */

import { Col, Row, Skeleton, Space } from "antd";
import { BrandLogo } from "@/components/brand/BrandLogo";

type SkeletonVariant = "dashboard" | "cards" | "detail" | "report" | "form" | "simple";

interface PageSkeletonProps {
  variant?: SkeletonVariant;
  rows?: number;
}

function PanelSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="ic-panel" style={{ padding: 16 }}>
      <Skeleton active paragraph={{ rows }} title={{ width: "40%" }} />
    </div>
  );
}

function MetricSkeleton() {
  return (
    <div className="ic-metric ic-metric--cyan" style={{ minHeight: 96 }}>
      <Skeleton active paragraph={{ rows: 2 }} title={false} />
    </div>
  );
}

export function PageSkeleton({ variant = "simple", rows = 6 }: PageSkeletonProps) {
  if (variant === "simple") {
    return (
      <div className="ic-page">
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
          <BrandLogo variant="mark" size={40} animated />
        </div>
        <PanelSkeleton rows={4} />
      </div>
    );
  }

  if (variant === "form") {
    return (
      <div className="ic-page">
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <PanelSkeleton rows={8} />
          </Col>
          <Col xs={24} lg={10}>
            <PanelSkeleton rows={6} />
          </Col>
        </Row>
      </div>
    );
  }

  if (variant === "dashboard") {
    return (
      <div className="ic-page">
        <Skeleton.Input active style={{ width: 260, marginBottom: 18 }} size="large" />
        <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Col xs={12} sm={8} lg={4} key={i}>
              <MetricSkeleton />
            </Col>
          ))}
        </Row>
        <Row gutter={[14, 14]}>
          <Col xs={24} lg={8}>
            <PanelSkeleton rows={6} />
          </Col>
          <Col xs={24} lg={16}>
            <PanelSkeleton rows={6} />
          </Col>
        </Row>
      </div>
    );
  }

  if (variant === "cards") {
    return (
      <div className="ic-page">
        <Space style={{ marginBottom: 16 }} size="middle">
          <Skeleton.Input active style={{ width: 200 }} />
          <Skeleton.Button active />
          <Skeleton.Button active />
        </Space>
        <Row gutter={[14, 14]}>
          {Array.from({ length: rows }).map((_, i) => (
            <Col xs={24} sm={12} xl={8} key={i}>
              <PanelSkeleton rows={3} />
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  if (variant === "detail" || variant === "report") {
    return (
      <div className="ic-page">
        <Skeleton.Input active style={{ width: 280, marginBottom: 16 }} size="large" />
        <Row gutter={[14, 14]}>
          <Col xs={24} lg={16}>
            <PanelSkeleton rows={10} />
          </Col>
          <Col xs={24} lg={8}>
            <PanelSkeleton rows={6} />
          </Col>
        </Row>
      </div>
    );
  }

  return (
    <div className="ic-page">
      <PanelSkeleton rows={rows} />
    </div>
  );
}
