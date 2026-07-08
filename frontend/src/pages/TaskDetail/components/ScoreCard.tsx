/* (c) 2026 AgentFlow-Eval */
/* Score card component */

import React from 'react';
import { Card, Progress, Descriptions, Tag } from 'antd';
import type { MetricScore } from '../../../types';

interface ScoreCardProps {
  metricScores: MetricScore[];
  loading?: boolean;
}

const metricLabels: Record<string, string> = {
  tool_accuracy: 'Tool Call Accuracy',
  answer_correctness: 'Answer Correctness',
  reasoning_coherence: 'Reasoning Coherence',
};

const metricColors: Record<string, string> = {
  tool_accuracy: '#1677ff',
  answer_correctness: '#52c41a',
  reasoning_coherence: '#722ed1',
};

const ScoreCard: React.FC<ScoreCardProps> = ({ metricScores, loading }) => {
  if (loading) return <Card loading title='Scoring Results'><p>Loading...</p></Card>;
  if (!metricScores.length) {
    return <Card title='Scoring Results'><p style={{ color: '#999' }}>No scores.</p></Card>;
  }
  const total = metricScores.reduce((sum, ms) => sum + ms.score, 0);
  return (
    <Card title='Scoring Results'>
      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        <Progress type='dashboard' percent={Math.round(total)} strokeColor='#1677ff' format={(p) => p + ' pts'} size={120} />
        <div style={{ marginTop: 8 }}><Tag color='blue'>Total Score</Tag></div>
      </div>
      {metricScores.map((ms) => (
        <div key={ms.id} style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span>{metricLabels[ms.metric_name] || ms.metric_name}</span>
            <span style={{ fontWeight: 600, color: metricColors[ms.metric_name] }}>{ms.score} pts</span>
          </div>
          <Progress percent={ms.score} strokeColor={metricColors[ms.metric_name]} size='small' showInfo={false} />
        </div>
      ))}
      {metricScores.length > 0 && metricScores[0].reason && (
        <Descriptions column={1} size='small' style={{ marginTop: 12 }}>
          <Descriptions.Item label='Evaluation Notes'>
            <span style={{ fontSize: 12, color: '#666', whiteSpace: 'pre-wrap' }}>{metricScores[0].reason}</span>
          </Descriptions.Item>
        </Descriptions>
      )}
    </Card>
  );
};

export default ScoreCard;
