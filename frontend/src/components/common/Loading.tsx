/* (c) 2026 AgentFlow-Eval */

import { Spin } from "antd";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { BrandLogo } from "@/components/brand/BrandLogo";

const Loading: React.FC<{ tip?: string; skeleton?: boolean }> = ({
  tip = "加载中...",
  skeleton = false,
}) => {
  if (skeleton) return <PageSkeleton variant="simple" />;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        gap: 16,
        height: 220,
      }}
    >
      <BrandLogo variant="mark" size={44} animated />
      <Spin tip={tip} size="large" />
    </div>
  );
};

export default Loading;
