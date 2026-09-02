/* (c) 2026 AgentFlow-Eval */
/* Human review card — manual override / annotation for AI scores (Phase 3) */

import React, { useState } from "react";
import {
  Card,
  InputNumber,
  Input,
  Button,
  Tag,
  Space,
  Typography,
  Divider,
} from "antd";
import {
  AuditOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SendOutlined,
} from "@ant-design/icons";
import { COMMAND_PALETTE } from "@/theme/tokens";

const { Text, Paragraph } = Typography;

const HumanReviewCard: React.FC = () => {
  const [humanScore, setHumanScore] = useState<number | null>(92.5);
  const [comment, setComment] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = () => {
    setSubmitting(true);
    setTimeout(() => {
      console.log("Human review submitted:", {
        score: humanScore,
        comment,
      });
      setReviewed(true);
      setSubmitting(false);
    }, 600);
  };

  const accentColor = COMMAND_PALETTE.success; // emerald green

  return (
    <Card
      className="af-glass"
      size="small"
      style={{ marginTop: 16, borderColor: "rgba(0,255,157,0.18)" }}
      title={
        <Space>
          <AuditOutlined style={{ color: accentColor }} />
          <span>Human Review</span>
          <Tag
            color={reviewed ? "success" : "warning"}
            icon={reviewed ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
            style={{ marginLeft: 8 }}
          >
            {reviewed ? "Reviewed" : "Pending"}
          </Tag>
        </Space>
      }
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ display: "block", marginBottom: 6, fontSize: 12 }}>
          Human Score
        </Text>
        <InputNumber
          min={0}
          max={100}
          step={0.1}
          value={humanScore}
          onChange={(v) => setHumanScore(v)}
          disabled={reviewed}
          style={{
            width: "100%",
            color: accentColor,
            fontWeight: 700,
            fontSize: 18,
          }}
          inputMode="decimal"
        />
      </div>

      <Divider style={{ margin: "12px 0", borderColor: "rgba(0,255,157,0.1)" }} />

      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ display: "block", marginBottom: 6, fontSize: 12 }}>
          Reviewer Comments
        </Text>
        <Input.TextArea
          rows={3}
          placeholder="Enter review comments, e.g. tool calls correct but conclusion slightly off..."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          disabled={reviewed}
          maxLength={500}
          showCount
          style={{ resize: "none" }}
        />
      </div>

      <Button
        type="primary"
        icon={<SendOutlined />}
        block
        loading={submitting}
        disabled={reviewed || humanScore === null}
        onClick={handleSubmit}
        style={{
          background: reviewed ? undefined : accentColor,
          borderColor: reviewed ? undefined : accentColor,
          color: reviewed ? undefined : "#000",
          fontWeight: 600,
        }}
      >
        {reviewed ? "Review Submitted" : "Submit Review (Override AI)"}
      </Button>

      {reviewed && (
        <Paragraph
          type="secondary"
          style={{ fontSize: 11, textAlign: "center", marginTop: 10, marginBottom: 0 }}
        >
          Override recorded at {new Date().toLocaleString("zh-CN")}
        </Paragraph>
      )}
    </Card>
  );
};

export default HumanReviewCard;
