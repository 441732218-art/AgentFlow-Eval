/* (c) 2026 AgentFlow-Eval */
/**
 * Full-screen gate when backend requires API key (AUTH_ENABLED) and requests 401.
 */
import { useState } from "react";
import { Alert, Button, Card, Input, Space, Typography } from "antd";
import { KeyOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { writeLocalApiKey } from "@/lib/settings-storage";
import { useAuth } from "@/auth";

const { Title, Paragraph, Text } = Typography;

type Props = {
  open: boolean;
  message?: string | null;
  onSaved: () => void;
};

export function ApiKeyGate({ open, message, onSaved }: Props) {
  const { refresh } = useAuth();
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (!open) return null;

  const submit = async () => {
    const trimmed = key.trim();
    if (!trimmed) {
      setErr("请输入 API Key（取自 backend API_KEYS 的 secret 段）");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      writeLocalApiKey(trimmed);
      await refresh();
      onSaved();
      // Hard reload so all React Query caches + interceptors pick up the key
      window.location.reload();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "保存失败");
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 2000,
        display: "grid",
        placeItems: "center",
        padding: 24,
        background:
          "radial-gradient(ellipse at 30% 20%, rgba(56,189,248,0.12), transparent 50%), " +
          "radial-gradient(ellipse at 70% 80%, rgba(129,140,248,0.1), transparent 45%), " +
          "rgba(7, 9, 15, 0.92)",
        backdropFilter: "blur(8px)",
      }}
    >
      <Card
        style={{
          width: "min(440px, 100%)",
          borderRadius: 16,
          border: "1px solid var(--af-border, #1e293b)",
          background: "var(--af-bg-elevated, #0f172a)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.45)",
        }}
        styles={{ body: { padding: 28 } }}
      >
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                display: "grid",
                placeItems: "center",
                background: "linear-gradient(135deg, #38bdf8, #818cf8)",
                color: "#0f172a",
                fontSize: 20,
              }}
            >
              <SafetyCertificateOutlined />
            </div>
            <div>
              <Title level={4} style={{ margin: 0 }}>
                需要 API Key
              </Title>
              <Text type="secondary" style={{ fontSize: 13 }}>
                后端已开启 AUTH_ENABLED，驾驶舱与 API 需鉴权
              </Text>
            </div>
          </div>

          <Alert
            type="warning"
            showIcon
            message={message || "Unauthorized"}
            description={
              <span>
                请填写 <Text code>backend/.env.docker</Text> 中{" "}
                <Text code>API_KEYS</Text> 的{" "}
                <strong>secret 段</strong>（冒号前部分）。例如{" "}
                <Text code>API_KEYS=af-xxx:admin:admin</Text> 则填{" "}
                <Text code>af-xxx</Text>。
              </span>
            }
          />

          <div>
            <Text style={{ display: "block", marginBottom: 8, fontSize: 13 }}>
              <KeyOutlined /> API Key
            </Text>
            <Input.Password
              size="large"
              placeholder="粘贴 secret（不含 :actor:role）"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              onPressEnter={() => void submit()}
              autoFocus
              autoComplete="off"
            />
          </div>

          {err && <Alert type="error" showIcon message={err} />}

          <Paragraph type="secondary" style={{ margin: 0, fontSize: 12 }}>
            密钥仅保存在本机 localStorage，刷新后仍有效。也可稍后在「设置」中修改。
          </Paragraph>

          <Button type="primary" size="large" block loading={busy} onClick={() => void submit()}>
            保存并进入驾驶舱
          </Button>
        </Space>
      </Card>
    </div>
  );
}
