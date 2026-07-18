/* Live Agent topology for Command Center — horizontal ReactFlow pipeline */

import { memo, useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Drawer, Descriptions, Tag, Space, Typography } from "antd";

const { Text } = Typography;

export type TopologyNodeMeta = {
  type?: string;
  kind?: string;
  running?: number;
  failed?: number;
  score?: number | null;
  input?: string;
  output?: string;
  token?: number;
  latency?: number | string;
  model?: string;
  error?: string;
};

export type TopologyNode = {
  id: string;
  label: string;
  status?: "ok" | "warn" | "error" | "idle" | string;
  kind?: string;
  meta?: TopologyNodeMeta;
};

export type TopologyEdge = {
  source: string;
  target: string;
  type?: string;
  label?: string;
};

export type TopologyLegendItem = {
  status: string;
  label: string;
};

type AgentTopologyFlowProps = {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  height?: number;
  /** horizontal (default) | vertical */
  layout?: "horizontal" | "vertical";
  legend?: TopologyLegendItem[];
  showMiniMap?: boolean;
};

type FlowNodeData = {
  label: string;
  status: string;
  kind?: string;
  meta?: TopologyNodeMeta;
  [key: string]: unknown;
};

const KIND_ICON: Record<string, string> = {
  ingress: "▶",
  agent: "◈",
  tool: "⚙",
  observe: "◉",
  judge: "★",
};

function statusClass(status: string): string {
  if (status === "ok") return "ok";
  if (status === "warn") return "warn";
  if (status === "error") return "error";
  return "idle";
}

function TopologyNodeView(props: NodeProps) {
  const data = props.data as FlowNodeData;
  const status = data.status || "idle";
  const kind = data.kind || data.meta?.type || "agent";
  const sc = statusClass(status);

  return (
    <div className={`ic-flow-node ic-flow-node--pipeline ${sc}`}>
      <Handle
        type="target"
        position={Position.Left}
        className="ic-flow-handle"
      />
      <div className="ic-flow-node__row">
        <span className={`ic-status-dot ${sc}`} />
        <span className="ic-flow-node__kind" aria-hidden>
          {KIND_ICON[kind] || "◆"}
        </span>
        <strong className="ic-flow-node__label">{data.label}</strong>
      </div>
      <div className="ic-flow-node__meta">
        {data.meta?.running != null ? (
          <span>run {data.meta.running}</span>
        ) : null}
        {data.meta?.latency != null && data.meta.latency !== "—" ? (
          <span>{String(data.meta.latency)}</span>
        ) : null}
        {data.meta?.score != null ? <span>sc {Number(data.meta.score).toFixed(1)}</span> : null}
        {data.meta?.failed ? <span className="ic-flow-node__err">fail {data.meta.failed}</span> : null}
      </div>
      {status === "error" || status === "warn" ? (
        <span className={`ic-flow-node__pulse ic-flow-node__pulse--${sc}`} />
      ) : null}
      <Handle
        type="source"
        position={Position.Right}
        className="ic-flow-handle"
      />
    </div>
  );
}

function TopologyNodeViewVertical(props: NodeProps) {
  const data = props.data as FlowNodeData;
  const status = data.status || "idle";
  const kind = data.kind || data.meta?.type || "agent";
  const sc = statusClass(status);

  return (
    <div className={`ic-flow-node ic-flow-node--pipeline ${sc}`}>
      <Handle type="target" position={Position.Top} className="ic-flow-handle" />
      <div className="ic-flow-node__row">
        <span className={`ic-status-dot ${sc}`} />
        <span className="ic-flow-node__kind">{KIND_ICON[kind] || "◆"}</span>
        <strong className="ic-flow-node__label">{data.label}</strong>
      </div>
      <div className="ic-flow-node__meta">
        {data.meta?.running != null ? <span>run {data.meta.running}</span> : null}
        {data.meta?.latency != null ? <span>{String(data.meta.latency)}</span> : null}
      </div>
      <Handle type="source" position={Position.Bottom} className="ic-flow-handle" />
    </div>
  );
}

const nodeTypesH = { topo: TopologyNodeView };
const nodeTypesV = { topo: TopologyNodeViewVertical };

function FitViewOnData({ nodeCount }: { nodeCount: number }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    const t = window.setTimeout(() => {
      void fitView({ padding: 0.2, duration: 280 });
    }, 80);
    return () => window.clearTimeout(t);
  }, [nodeCount, fitView]);
  return null;
}

function TopologyInner({
  nodes,
  edges,
  height = 320,
  layout = "horizontal",
  legend,
  showMiniMap = true,
}: AgentTopologyFlowProps) {
  const [selected, setSelected] = useState<TopologyNode | null>(null);
  const horizontal = layout !== "vertical";

  const rfNodes: Node[] = useMemo(() => {
    if (horizontal) {
      const gapX = 200;
      const y = 80;
      return nodes.map((n, i) => ({
        id: n.id,
        type: "topo",
        position: { x: 24 + i * gapX, y },
        data: {
          label: n.label,
          status: n.status || "idle",
          kind: n.kind || n.meta?.type,
          meta: n.meta,
        },
      }));
    }
    const gapY = 100;
    return nodes.map((n, i) => ({
      id: n.id,
      type: "topo",
      position: { x: 100, y: 20 + i * gapY },
      data: {
        label: n.label,
        status: n.status || "idle",
        kind: n.kind || n.meta?.type,
        meta: n.meta,
      },
    }));
  }, [nodes, horizontal]);

  const rfEdges: Edge[] = useMemo(
    () =>
      edges.map((e, i) => {
        const isLoop = e.type === "loop";
        return {
          id: `e-${e.source}-${e.target}-${i}`,
          source: e.source,
          target: e.target,
          animated: true,
          label: e.label || (isLoop ? "loop" : undefined),
          labelStyle: {
            fill: isLoop ? "#FF3864" : "#8ba3c7",
            fontSize: 10,
            fontWeight: 600,
          },
          labelBgStyle: {
            fill: "rgba(5,8,22,0.85)",
            fillOpacity: 0.9,
          },
          labelBgPadding: [4, 6] as [number, number],
          labelBgBorderRadius: 4,
          style: {
            stroke: isLoop ? "#FF3864" : "#00D4FF",
            strokeWidth: isLoop ? 2 : 1.8,
            strokeDasharray: isLoop ? "6 4" : undefined,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isLoop ? "#FF3864" : "#00D4FF",
            width: 16,
            height: 16,
          },
          type: isLoop ? "smoothstep" : "smoothstep",
        };
      }),
    [edges]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const src = nodes.find((n) => n.id === node.id) || null;
      setSelected(src);
    },
    [nodes]
  );

  const defaultLegend: TopologyLegendItem[] = legend || [
    { status: "ok", label: "Healthy" },
    { status: "warn", label: "Degraded" },
    { status: "error", label: "Failure" },
    { status: "idle", label: "Idle" },
  ];

  return (
    <>
      <div className="ic-flow-wrap" style={{ height }}>
        <div className="ic-flow-legend">
          {defaultLegend.map((item) => (
            <span key={item.status} className="ic-flow-legend__item">
              <span className={`ic-status-dot ${statusClass(item.status)}`} />
              {item.label}
            </span>
          ))}
        </div>
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          nodeTypes={horizontal ? nodeTypesH : nodeTypesV}
          fitView
          proOptions={{ hideAttribution: true }}
          onNodeClick={onNodeClick}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          minZoom={0.4}
          maxZoom={1.6}
          defaultEdgeOptions={{ type: "smoothstep" }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            color="rgba(0,212,255,0.14)"
            gap={20}
            size={1}
          />
          <Controls showInteractive={false} className="ic-flow-controls" />
          {showMiniMap ? (
            <MiniMap
              className="ic-flow-minimap"
              nodeStrokeWidth={2}
              nodeColor={(n) => {
                const s = String((n.data as FlowNodeData)?.status || "idle");
                if (s === "ok") return "#00FF9D";
                if (s === "warn") return "#FFC857";
                if (s === "error") return "#FF3864";
                return "#5a7399";
              }}
              maskColor="rgba(5,8,22,0.75)"
              pannable
              zoomable
            />
          ) : null}
          <FitViewOnData nodeCount={nodes.length} />
        </ReactFlow>
      </div>

      <Drawer
        title={
          <Space>
            <span className={`ic-status-dot ${statusClass(selected?.status || "idle")}`} />
            {selected?.label || "Node"}
          </Space>
        }
        open={!!selected}
        onClose={() => setSelected(null)}
        width={380}
        className="ic-flow-drawer"
      >
        {selected ? (
          <>
            <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 12 }}>
              Click node metrics · pipeline stage detail
            </Text>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Status">
                <Tag
                  color={
                    selected.status === "error"
                      ? "error"
                      : selected.status === "warn"
                        ? "warning"
                        : selected.status === "ok"
                          ? "success"
                          : "default"
                  }
                >
                  {selected.status || "idle"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Kind">
                {selected.kind || selected.meta?.type || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Input">
                {selected.meta?.input || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Output">
                {selected.meta?.output || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Token">
                {selected.meta?.token ?? "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Latency">
                {selected.meta?.latency ?? "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Model">
                {selected.meta?.model || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Error">
                {selected.meta?.error || "—"}
              </Descriptions.Item>
              {selected.meta?.score != null ? (
                <Descriptions.Item label="Score">{selected.meta.score}</Descriptions.Item>
              ) : null}
              {selected.meta?.running != null ? (
                <Descriptions.Item label="Running">{selected.meta.running}</Descriptions.Item>
              ) : null}
              {selected.meta?.failed != null ? (
                <Descriptions.Item label="Failed">{selected.meta.failed}</Descriptions.Item>
              ) : null}
            </Descriptions>
          </>
        ) : null}
      </Drawer>
    </>
  );
}

export const AgentTopologyFlow = memo(function AgentTopologyFlow(
  props: AgentTopologyFlowProps
) {
  return (
    <ReactFlowProvider>
      <TopologyInner {...props} />
    </ReactFlowProvider>
  );
});
