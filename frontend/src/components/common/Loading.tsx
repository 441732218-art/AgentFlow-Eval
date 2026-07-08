/* (c) 2026 AgentFlow-Eval */

import { Spin } from "antd";

const Loading: React.FC<{ tip?: string }> = ({ tip = "加载中..." }) => (
  <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 200 }}>
    <Spin tip={tip} size="large" />
  </div>
);

export default Loading;
