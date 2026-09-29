import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Col, Result, Row, Space, message } from "antd";
import { ArrowLeftOutlined, ReloadOutlined } from "@ant-design/icons";
import { Link, useParams } from "react-router-dom";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { useCan } from "@/auth";
import { intelligenceApi } from "../api/intelligence";
import type {
  AgentIntelligenceConsole,
  RecommendationListItem,
} from "../types/console";
import { AgentHeader } from "../components/AgentHeader";
import { QualityPostureCard } from "../components/QualityPostureCard";
import { QualityTrendChart } from "../components/QualityTrendChart";
import { InsightCardList } from "../components/InsightCardList";
import { RecommendationCardList } from "../components/RecommendationCardList";
import {
  ExplanationDrawer,
  type ExplanationDrawerPayload,
} from "../components/ExplanationDrawer";

function isForbidden(err: unknown): boolean {
  const status = (err as { status?: number })?.status;
  return status === 403;
}

export default function AgentConsolePage() {
  const { agentId = "" } = useParams<{ agentId: string }>();
  const canUpdate = useCan("intelligence:update");
  const canRead = useCan("intelligence:read");

  const [consoleData, setConsoleData] = useState<AgentIntelligenceConsole | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState<string | null>(null);
  const [qaSummary, setQaSummary] = useState<string | null>(null);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [drawerPayload, setDrawerPayload] = useState<ExplanationDrawerPayload | null>(null);

  const loadConsole = useCallback(async () => {
    if (!agentId.trim()) {
      setError("Missing agent id");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setForbidden(false);
    setQaError(null);
    setQaSummary(null);
    try {
      const [consolePayload, recPayload] = await Promise.all([
        intelligenceApi.getConsole(agentId.trim()),
        intelligenceApi.listRecommendations(agentId.trim()).catch(() => ({
          recommendations: [],
          count: 0,
        })),
      ]);
      setConsoleData(consolePayload);
      setRecommendations(recPayload.recommendations || []);
    } catch (err) {
      if (isForbidden(err)) {
        setForbidden(true);
        setError(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load intelligence console");
      }
      setConsoleData(null);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void loadConsole();
  }, [loadConsole]);

  const handleQaExplain = async () => {
    const ref = consoleData?.quality_explanation_ref;
    if (!ref) {
      setQaError("No quality assessment reference on this console projection.");
      return;
    }
    setQaLoading(true);
    setQaError(null);
    try {
      const explanation = await intelligenceApi.getQualityAssessmentExplanation(ref);
      setQaSummary(explanation.summary || explanation.posture || null);
      setDrawerPayload({
        title: "Quality assessment explanation",
        summary: explanation.summary,
        posture: explanation.posture,
        evidenceRefs: explanation.insight_refs,
        snapshotRefs: explanation.snapshot_refs,
        relatedIds: explanation.recommendation_refs?.map((item) => item.id),
      });
      setDrawerError(null);
      setDrawerOpen(true);
    } catch (err) {
      const msg =
        isForbidden(err)
          ? "Permission denied for quality explanation."
          : err instanceof Error
            ? err.message
            : "Quality explanation unavailable (assessment may not be registered).";
      setQaError(msg);
      setQaSummary(null);
    } finally {
      setQaLoading(false);
    }
  };

  const handleInsightExplain = async (insightId: string) => {
    setDrawerOpen(true);
    setDrawerLoading(true);
    setDrawerError(null);
    setDrawerPayload(null);
    try {
      const [detail, explanation] = await Promise.all([
        intelligenceApi.getInsight(insightId).catch(() => null),
        intelligenceApi.getInsightExplanation(insightId),
      ]);
      setDrawerPayload({
        title: `Insight ${insightId}`,
        summary:
          (typeof detail?.summary === "string" ? detail.summary : null) ||
          (typeof explanation.summary === "string" ? explanation.summary : null),
        reason: typeof explanation.reason === "string" ? explanation.reason : null,
        evidenceRefs: explanation.evidence_refs || detail?.evidence_refs,
        snapshotRefs: explanation.snapshot_refs,
      });
    } catch (err) {
      setDrawerError(
        isForbidden(err)
          ? "Permission denied"
          : err instanceof Error
            ? err.message
            : "Failed to load explanation",
      );
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleAcknowledge = async (insightId: string) => {
    setUpdatingId(insightId);
    try {
      await intelligenceApi.acknowledgeInsight(insightId);
      message.success("Insight acknowledged");
      await loadConsole();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Acknowledge failed");
    } finally {
      setUpdatingId(null);
    }
  };

  const handleResolve = async (insightId: string) => {
    setUpdatingId(insightId);
    try {
      await intelligenceApi.resolveInsight(insightId);
      message.success("Insight resolved");
      await loadConsole();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Resolve failed");
    } finally {
      setUpdatingId(null);
    }
  };

  if (forbidden || (!canRead && error === null && !loading && !consoleData)) {
    return (
      <PageShell title="Intelligence Console">
        <Result
          status="403"
          title="403"
          subTitle="You do not have intelligence:read permission for this console."
          extra={
            <Link to="/agents">
              <Button type="primary">Back to Agents</Button>
            </Link>
          }
        />
      </PageShell>
    );
  }

  if (loading && !consoleData) {
    return (
      <PageShell title="Intelligence Console">
        <PageSkeleton variant="detail" />
      </PageShell>
    );
  }

  if (error && !consoleData) {
    return (
      <PageShell title="Intelligence Console">
        <Result
          status="error"
          title="Failed to load console"
          subTitle={error}
          extra={
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => void loadConsole()}>
                Retry
              </Button>
              <Link to={`/agents/${encodeURIComponent(agentId)}`}>
                <Button icon={<ArrowLeftOutlined />}>Agent</Button>
              </Link>
            </Space>
          }
        />
      </PageShell>
    );
  }

  if (!consoleData) {
    return (
      <PageShell title="Intelligence Console">
        <Result status="info" title="No intelligence data" subTitle="Empty projection for this agent." />
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Intelligence Console"
      subtitle="Observe · Explain · Recommend — not a governance or runtime console"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void loadConsole()}>
            Refresh
          </Button>
          <Link to={`/agents/${encodeURIComponent(agentId)}`}>
            <Button icon={<ArrowLeftOutlined />}>Agent</Button>
          </Link>
        </Space>
      }
    >
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Alert
          type="info"
          showIcon
          message="Intelligence only"
          description="No approve, reject, deploy, execute, or AutoFix controls on this page."
        />
        <AgentHeader
          agentId={consoleData.agent_id || agentId}
          posture={consoleData.quality_posture}
          openInsightCount={consoleData.open_insight_count}
          generatedAt={consoleData.generated_at}
        />
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={10}>
            <QualityPostureCard
              posture={consoleData.quality_posture}
              explanationRef={consoleData.quality_explanation_ref}
              loadingExplain={qaLoading}
              explainError={qaError}
              explainSummary={qaSummary}
              onExplain={() => void handleQaExplain()}
            />
          </Col>
          <Col xs={24} lg={14}>
            <QualityTrendChart points={consoleData.trend_points || []} />
          </Col>
        </Row>
        <InsightCardList
          insights={consoleData.top_insights || []}
          updatingId={updatingId}
          canUpdate={canUpdate}
          onExplain={(id) => void handleInsightExplain(id)}
          onAcknowledge={(id) => void handleAcknowledge(id)}
          onResolve={(id) => void handleResolve(id)}
        />
        <RecommendationCardList
          recommendations={consoleData.top_recommendations || []}
          details={recommendations}
        />
      </Space>
      <ExplanationDrawer
        open={drawerOpen}
        loading={drawerLoading}
        error={drawerError}
        payload={drawerPayload}
        onClose={() => setDrawerOpen(false)}
      />
    </PageShell>
  );
}
