/* (c) 2026 AgentFlow-Eval */
/* Task detail page - evaluation results, trace flow, and scores */

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Col, Descriptions, Row, Tag, Button, message, Space, Spin } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, BarChartOutlined } from '@ant-design/icons';
import { useTaskStore } from '../../stores/useTaskStore';
import { useTraceStore } from '../../stores/useTraceStore';
import { formatDateTime, getStatusColor, formatDuration, formatTokens } from '../../utils/format';
import TraceFlowChart from './components/TraceFlowChart';
import ScoreCard from './components/ScoreCard';
import StepLogPanel from './components/StepLogPanel';

const TaskDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { currentTask, currentReport, loading: taskLoading, fetchTask, executeTask, fetchReport } = useTaskStore();
  const { loading: traceLoading, currentTrace, currentJudgeResult, fetchTrace, fetchTraces, judgeTrace } = useTraceStore();
  const [activeTraceId, setActiveTraceId] = useState<string | null>(null);

  useEffect(() => {
    if (id) { fetchTask(id); fetchReport(id); }
  }, [id, fetchTask, fetchReport]);

  useEffect(() => {
    if (currentReport?.details?.length) {
      fetchTraces(currentReport.details[0].suite_id);
    }
  }, [currentReport, fetchTraces]);

  const handleExecute = async () => {
    if (!id) return;
    try { await executeTask(id); message.success('Task submitted.'); }
    catch { message.error('Execute failed.'); }
  };

  const handleJudge = async (traceId: string) => {
    try { await judgeTrace(traceId); message.success('Score complete.'); }
    catch { message.error('Judge failed.'); }
  };

  const handleSelectTrace = async (traceId: string) => {
    setActiveTraceId(traceId);
    await fetchTrace(traceId);
  };

  if (taskLoading && !currentTask) return <Spin size='large' style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <>
      <Card title={'Task: ' + (currentTask?.name || '')}
        extra={<Space>
          <Button type='primary' icon={<PlayCircleOutlined />} onClick={handleExecute} disabled={currentTask?.status === 'running'}>Run</Button>
          <Button icon={<ReloadOutlined />} onClick={() => id && (fetchTask(id), fetchReport(id))}>Refresh</Button>
        </Space>}
        style={{ marginBottom: 16 }}>
        <Descriptions column={3} size='small'>
          <Descriptions.Item label='Status'>
            <Tag color={getStatusColor(currentTask?.status || 'pending')}>{currentTask?.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label='Suites'>{currentTask?.test_suite_count || 0}</Descriptions.Item>
          <Descriptions.Item label='Created'>{formatDateTime(currentTask?.created_at)}</Descriptions.Item>
          {currentReport?.summary && <>
            <Descriptions.Item label='Score'>
              <span style={{ fontWeight: 600, color: '#1677ff', fontSize: 18 }}>{currentReport.summary.overall_score}</span>
            </Descriptions.Item>
            <Descriptions.Item label='Tokens'>{formatTokens(currentReport.summary.total_tokens)}</Descriptions.Item>
            <Descriptions.Item label='Avg Time'>{formatDuration(currentReport.summary.avg_time_per_trace_ms)}</Descriptions.Item>
          </>}
        </Descriptions>
      </Card>

      {currentReport?.summary && (
        <Card title='Score Overview' style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            {Object.entries(currentReport.summary.dimension_scores || {}).map(([key, val]) => (
              <Col span={8} key={key}>
                <Card size='small' title={
                  key === 'tool_accuracy' ? 'Tool Accuracy' :
                  key === 'answer_correctness' ? 'Answer Correctness' : 'Reasoning Coherence'
                }>
                  <span style={{ fontSize: 24, fontWeight: 600, color: '#1677ff' }}>{val}</span>
                  <span style={{ color: '#999', marginLeft: 4 }}>/ 100</span>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {currentReport?.details?.map((detail) => (
        <Card key={detail.suite_id} size='small'
          title={'Suite: ' + detail.user_query.slice(0, 50) + '...'}
          style={{ marginBottom: 8 }}
          extra={<Space>
            <Button size='small' icon={<BarChartOutlined />}
              onClick={() => { const tid = detail.traces?.[0]?.trace_id; if (tid) handleJudge(tid); }}>Judge</Button>
            <Button size='small' type={activeTraceId === detail.traces?.[0]?.trace_id ? 'primary' : 'default'}
              onClick={() => { const tid = detail.traces?.[0]?.trace_id; if (tid) handleSelectTrace(tid); }}>Trace</Button>
          </Space>}>
          <Descriptions size='small' column={4}>
            <Descriptions.Item label='Status'>
              <Tag color={getStatusColor(detail.traces?.[0]?.status || 'pending')}>{detail.traces?.[0]?.status || 'N/A'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label='Tokens'>{formatTokens(detail.traces?.[0]?.total_tokens || 0)}</Descriptions.Item>
            <Descriptions.Item label='Time'>{formatDuration(detail.traces?.[0]?.response_time_ms || 0)}</Descriptions.Item>
            <Descriptions.Item label='Score'>
              {Object.values(detail.traces?.[0]?.scores || {}).reduce((a: number, b: number) => a + b, 0) || '-'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      ))}

      {currentTrace && (
        <Row gutter={16}>
          <Col span={16}>
            <Card title='Execution DAG' style={{ marginBottom: 16 }}>
              <TraceFlowChart steps={currentTrace.steps} />
            </Card>
          </Col>
          <Col span={8}>
            <ScoreCard metricScores={currentTrace.metric_scores || []} loading={traceLoading} />
          </Col>
        </Row>
      )}

      {currentTrace && (
        <Card title='Step Log' extra={<Space>
          <Tag>Tokens: {formatTokens(currentTrace.total_tokens)}</Tag>
          <Tag>Time: {formatDuration(currentTrace.response_time_ms)}</Tag>
        </Space>}>
          <StepLogPanel steps={currentTrace.steps} />
        </Card>
      )}

      {currentJudgeResult && (
        <Card title='LLM Judge Details' style={{ marginTop: 16 }}>
          <Descriptions column={1}>
            <Descriptions.Item label='Total'>
              <span style={{ fontSize: 24, fontWeight: 600, color: '#1677ff' }}>{currentJudgeResult.total}</span>
              <span style={{ color: '#999' }}>/100</span>
            </Descriptions.Item>
            {Object.entries(currentJudgeResult.scores).map(([key, val]) => (
              <Descriptions.Item key={key} label={
                key === 'tool_accuracy' ? 'Tool Accuracy' :
                key === 'answer_correctness' ? 'Answer Correctness' : 'Reasoning Coherence'
              }>{val} pts</Descriptions.Item>
            ))}
            <Descriptions.Item label='Token Cost'>{currentJudgeResult.token_cost}</Descriptions.Item>
            <Descriptions.Item label='Evaluation Notes'>
              <div style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 6 }}>
                {currentJudgeResult.reason}
              </div>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </>
  );
};

export default TaskDetail;
