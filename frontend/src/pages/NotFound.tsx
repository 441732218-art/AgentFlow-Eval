import { Button, Result, Space } from "antd";
import { useNavigate } from "react-router-dom";
import { HomeOutlined, UnorderedListOutlined } from "@ant-design/icons";

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="af-page" style={{ paddingTop: 48 }}>
      <div className="af-glass" style={{ maxWidth: 560, margin: "0 auto", padding: "32px 24px" }}>
        <Result
          status="404"
          title={<span className="af-gradient-text">404</span>}
          subTitle="页面不存在，或你没有访问权限。"
          extra={
            <Space wrap>
              <Button
                type="primary"
                icon={<HomeOutlined />}
                onClick={() => navigate("/")}
                style={{ background: "var(--af-gradient)", border: "none" }}
              >
                回到总览
              </Button>
              <Button icon={<UnorderedListOutlined />} onClick={() => navigate("/tasks")}>
                任务列表
              </Button>
            </Space>
          }
        />
      </div>
    </div>
  );
}
