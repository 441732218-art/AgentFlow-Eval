/* (c) 2026 AgentFlow-Eval */
/* Step log panel */

import React from 'react';
import { Timeline, Tag, Typography } from 'antd';
import { BulbOutlined, ToolOutlined, EyeOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { TraceStep } from '../../../types';

const { Text } = Typography;

interface StepLogPanelProps { steps: TraceStep[]; }

const stepIcons: Record<string, React.ReactNode> = {
  thought: <BulbOutlined />, action: <ToolOutlined />,
  observation: <EyeOutlined />, final_answer: <CheckCircleOutlined />,
};
const stepColors: Record<string, string> = {
  thought: '#1677ff', action: '#faad14', observation: '#52c41a', final_answer: '#722ed1',
};
const stepLabels: Record<string, string> = {
  thought: 'Thought', action: 'Action', observation: 'Observation', final_answer: 'Final Answer',
};

const StepLogPanel: React.FC<StepLogPanelProps> = ({ steps }) => (
  <Timeline
    items={steps.map((step, idx) => ({
      key: idx,
      color: stepColors[step.type || step.role || 'thought'],
      dot: stepIcons[step.type || step.role || 'thought'],
      children: (
        <div>
          <Tag color={stepColors[step.type || step.role || 'thought']} style={{ marginBottom: 4 }}>
            {stepLabels[step.type || step.role || 'thought']}
          </Tag>
          {step.tool_name && <Text code style={{ marginLeft: 8 }}>{step.tool_name}</Text>}
          {step.tool_input && <div><Text type='secondary' style={{ fontSize: 12 }}>Input: {step.tool_input}</Text></div>}
          {(step.content || step.observation || '') && (
            <div style={{ marginTop: 4 }}>
              <Text style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>
                {((step.content || step.observation || '').length > 200
                  ? (step.content || step.observation || '').slice(0, 200) + '...'
                  : step.content || step.observation)}
              </Text>
            </div>
          )}
        </div>
      ),
    }))}
  />
);

export default StepLogPanel;
