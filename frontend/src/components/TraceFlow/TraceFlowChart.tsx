/* (c) 2026 AgentFlow-Eval */
/* Agent execution trace DAG visualization using ReactFlow */

import React, { useCallback, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Card, Tag, Typography, Space, Tooltip } from "antd";
import {
  BulbOutlined,
  ToolOutlined,
  EyeOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import type { TraceStep } from "@/types";

const { Text, Paragraph } = Typography;

const NODE_WIDTH = 220;
const NODE_HEIGHT = 88;
const VERTICAL_GAP = 80;

interface StepColors {
  bg: string;
  border: string;
  tag: string;
  icon: React.ReactNode;
  label: string;
}

const STEP_STYLES: Record<string, StepColors> = {
  thought: {
    bg: "rgba(56, 189, 248, 0.12)",
    border: "#38bdf8",
    tag: "processing",
    icon: <BulbOutlined />,
    label: "Thought",
  },
  action: {
    bg: "rgba(251, 191, 36, 0.12)",
    border: "#fbbf24",
    tag: "gold",
    icon: <ToolOutlined />,
    label: "Action",
  },
  observation: {
    bg: "rgba(52, 211, 153, 0.12)",
    border: "#34d399",
    tag: "success",
    icon: <EyeOutlined />,
    label: "Observation",
  },
  final_answer: {
    bg: "rgba(129, 140, 248, 0.14)",
    border: "#818cf8",
    tag: "purple",
    icon: <CheckCircleOutlined />,
    label: "Final Answer",
  },
};

const STEP_PRIORITY: Record<string, number> = {
  thought: 0,
  action: 1,
  observation: 2,
  final_answer: 3,
};

/* ---- Custom Node Component ---- */

interface AgentStepNodeData extends Record<string, unknown> {
  label: string;
  stepType: string;
  content: string;
  toolName?: string;
  toolInput?: string;
  index: number;
  isSelected: boolean;
}

const AgentStepNode: React.FC<{ data: AgentStepNodeData }> = ({ data }) => {
  const style = STEP_STYLES[data.stepType] || STEP_STYLES.thought;
  const displayContent = data.content || data.toolName || "(empty)";
  const truncated =
    displayContent.length > 80
      ? displayContent.slice(0, 80) + "..."
      : displayContent;

  return (
    <div
      style={{
        padding: "10px 14px",
        borderRadius: 10,
        border: "2px solid " + (data.isSelected ? style.border : style.border + "99"),
        background: data.isSelected ? style.bg : "var(--af-bg-surface)",
        minWidth: NODE_WIDTH,
        maxWidth: NODE_WIDTH,
        boxShadow: data.isSelected
          ? "0 0 0 3px " + style.border + "40, var(--af-shadow-md)"
          : "var(--af-shadow-sm)",
        cursor: "pointer",
        fontFamily: "var(--af-font)",
        color: "var(--af-text)",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: style.border }} />

      <Space style={{ marginBottom: 6, display: "flex", alignItems: "center" }}>
        <Tag
          color={style.tag}
          style={{ margin: 0, fontSize: 11, lineHeight: "18px", padding: "0 6px" }}
        >
          <Space size={4}>
            {style.icon}
            <span>{style.label}</span>
          </Space>
        </Tag>
        <Text style={{ fontSize: 10, color: "var(--af-text-muted)" }}>#{data.index + 1}</Text>
      </Space>

      {data.toolName && (
        <div style={{ marginBottom: 4 }}>
          <Text
            code
            style={{
              fontSize: 11,
              background: "var(--af-bg-muted)",
              padding: "1px 5px",
              borderRadius: 3,
            }}
          >
            {data.toolName}
          </Text>
        </div>
      )}

      <Tooltip title={displayContent} placement="right">
        <Paragraph
          style={{
            margin: 0,
            fontSize: 12,
            color: "var(--af-text-secondary)",
            lineHeight: "1.4",
            display: "-webkit-box",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {truncated}
        </Paragraph>
      </Tooltip>

      <Handle type="source" position={Position.Bottom} style={{ background: style.border }} />
    </div>
  );
};

const nodeTypes = { agentStep: AgentStepNode as React.ComponentType<any> };

/* ---- Layout Algorithm ---- */

function computeLayout(steps: TraceStep[], containerWidth: number) {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const centerX = Math.max(containerWidth / 2, 200);

  steps.forEach((step, idx) => {
    const stepType = step.type || step.role || "thought";
    const x = Math.round(centerX - NODE_WIDTH / 2);
    const y = idx * (NODE_HEIGHT + VERTICAL_GAP) + 20;

    nodes.push({
      id: "s-" + idx,
      type: "agentStep",
      position: { x, y },
      data: {
        label: STEP_STYLES[stepType]?.label || stepType,
        stepType,
        content: step.content || step.tool_input || "",
        toolName: step.tool_name,
        toolInput: step.tool_input,
        index: idx,
        isSelected: false,
      },
    } as Node);

    if (idx > 0) {
      const prevType = steps[idx - 1].type || steps[idx - 1].role || "thought";
      const prevP = STEP_PRIORITY[prevType] ?? 0;
      const currP = STEP_PRIORITY[stepType] ?? 0;
      const edgeColor = prevP <= currP ? "#64748b" : "#f87171";

      edges.push({
        id: "e-" + (idx - 1),
        source: "s-" + (idx - 1),
        target: "s-" + idx,
        type: "smoothstep",
        animated: true,
        style: { stroke: edgeColor, strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: edgeColor,
        },
        label: "Step " + idx,
        labelStyle: { fontSize: 10, fill: "#94a3b8" },
        labelBgStyle: { fill: "var(--af-bg-surface)", fillOpacity: 0.9 },
        labelBgPadding: [4, 2],
        labelBgBorderRadius: 3,
      } as Edge);
    }
  });

  return { nodes, edges };
}

const defaultEdgeOptions = {
  type: "smoothstep",
  style: { stroke: "#bbb", strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: "#bbb" },
};

/* ---- Main Component ---- */

interface TraceFlowChartProps {
  steps: TraceStep[];
  containerWidth?: number;
}

const TraceFlowChart: React.FC<TraceFlowChartProps> = ({
  steps,
  containerWidth = 600,
}) => {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([] as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([] as Edge[]);

  React.useEffect(() => {
    const result = computeLayout(steps, containerWidth);
    setNodes(result.nodes);
    setEdges(result.edges);
  }, [steps, containerWidth, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedId((prev) => (prev === node.id ? null : node.id));
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          data: { ...n.data, isSelected: n.id === node.id && selectedId !== node.id },
        }))
      );
    },
    [selectedId, setNodes],
  );

  const onPaneClick = useCallback(() => {
    setSelectedId(null);
    setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, isSelected: false } })));
  }, [setNodes]);

  const selectedStep = selectedId
    ? steps[parseInt(selectedId.replace("s-", ""), 10)]
    : null;

  const selectedStyle = selectedStep
    ? STEP_STYLES[selectedStep.type || selectedStep.role || "thought"]
    : null;

  const flowHeight = Math.max(300, steps.length * (NODE_HEIGHT + VERTICAL_GAP) + 60);

  if (steps.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: 60,
          border: "2px dashed var(--af-border)",
          borderRadius: 12,
          background: "var(--af-bg-muted)",
        }}
      >
        <Text type="secondary">暂无执行步骤可视化</Text>
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          height: flowHeight,
          width: "100%",
          border: "1px solid var(--af-border)",
          borderRadius: 12,
          background: "var(--af-bg-elevated)",
          overflow: "hidden",
        }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          defaultEdgeOptions={defaultEdgeOptions}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.4}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          panOnDrag={false}
          zoomOnScroll={true}
          selectNodesOnDrag={false}
          colorMode="system"
        >
          <Background color="var(--af-border-strong)" gap={20} />
          <Controls
            showInteractive={false}
            style={{
              borderRadius: 8,
              boxShadow: "var(--af-shadow-sm)",
            }}
          />
          <MiniMap
            style={{
              borderRadius: 6,
              border: "1px solid var(--af-border)",
              background: "var(--af-bg-surface)",
            }}
            nodeColor={(n: any) => {
              const t = n.data?.stepType || "thought";
              return STEP_STYLES[t]?.border || "#1677ff";
            }}
            maskColor="rgba(0,0,0,0.06)"
          />
        </ReactFlow>
      </div>

      {selectedStep && selectedStyle && (
        <Card
          size="small"
          style={{ marginTop: 16, border: "1px solid " + selectedStyle.border + "30" }}
          title={(
            <Space>
              {selectedStyle.icon}
              <span>{selectedStyle.label} #{selectedId?.replace("s-", "")}</span>
            </Space>
          )}
          extra={<Tag color={selectedStyle.tag}>Step {selectedId?.replace("s-", "")}</Tag>}
        >
          {selectedStep.tool_name && (
            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 12 }}>Tool: </Text>
              <Text code>{selectedStep.tool_name}</Text>
            </div>
          )}
          {selectedStep.tool_input && (
            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 12 }}>Input: </Text>
              <Text code style={{ fontSize: 12, wordBreak: "break-all" }}>
                {selectedStep.tool_input}
              </Text>
            </div>
          )}
          {(selectedStep.content || selectedStep.observation || selectedStep.action_input) && (
            <div>
              <Text strong style={{ fontSize: 12 }}>Content: </Text>
              <Paragraph
                style={{
                  fontSize: 13,
                  color: "#333",
                  whiteSpace: "pre-wrap",
                  background: "#f9f9f9",
                  padding: 12,
                  borderRadius: 6,
                  marginTop: 4,
                  marginBottom: 0,
                  maxHeight: 200,
                  overflow: "auto",
                }}
              >
                {selectedStep.content || selectedStep.observation || selectedStep.action_input}
              </Paragraph>
            </div>
          )}
          {!selectedStep.content && !selectedStep.tool_name && !selectedStep.tool_input && (
            <Text type="secondary" style={{ fontSize: 12 }}>(No additional data)</Text>
          )}
        </Card>
      )}
    </div>
  );
};

export default TraceFlowChart;
