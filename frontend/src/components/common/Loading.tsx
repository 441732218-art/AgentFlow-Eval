/* (c) 2026 AgentFlow-Eval */

import { Spin } from "antd";
import { PageSkeleton } from "@/components/ui/PageSkeleton";

const Loading: React.FC<{ tip?: string; skeleton?: boolean }> = ({
  tip = "加载中...",
  skeleton = false,
}) => {
  if (skeleton) return <PageSkeleton variant="simple" />;
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: 200,
      }}
    >
      <Spin tip={tip} size="large" />
    </div>
  );
};

export default Loading;
