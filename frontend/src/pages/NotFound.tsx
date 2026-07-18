import { Button, Result, Space } from "antd";
import { useNavigate } from "react-router-dom";
import { HomeOutlined, UnorderedListOutlined } from "@ant-design/icons";
import { BrandLogo } from "@/components/brand/BrandLogo";

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="ic-page af-page" style={{ paddingTop: 48 }}>
      <div className="ic-panel" style={{ maxWidth: 560, margin: "0 auto", padding: "32px 24px" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 8 }}>
          <BrandLogo variant="mark" size={48} />
        </div>
        <Result
          status="404"
          title={<span className="af-gradient-text">404</span>}
          subTitle="页面不存在，或你没有访问权限。"
          extra={
            <Space wrap>
              <Button
                type="primary"
                icon={<HomeOutlined />}
                onClick={() => navigate("/dashboard")}
                className="ic-btn-gradient"
              >
                回到驾驶舱
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
