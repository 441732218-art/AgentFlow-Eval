import { Card, Empty, Typography } from "antd";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { QualityTrendPoint } from "../types/console";

const { Text } = Typography;

type Props = {
  points: QualityTrendPoint[];
};

export function QualityTrendChart({ points }: Props) {
  if (!points.length) {
    return (
      <Card title="Quality trend" className="ic-panel" size="small">
        <Empty description="No historical trend points" />
      </Card>
    );
  }

  const data = points.map((point) => ({
    ...point,
    label: point.timestamp?.slice(0, 10) || point.agent_version || "—",
    delta: point.score_delta ?? 0,
  }));

  return (
    <Card
      title="Quality trend"
      className="ic-panel"
      size="small"
      extra={<Text type="secondary">{points.length} points</Text>}
    >
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="delta" name="score_delta" stroke="#1677ff" dot />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
