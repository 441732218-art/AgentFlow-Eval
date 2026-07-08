import { Layout, Input, Space } from "antd";
import { MenuFoldOutlined, MenuUnfoldOutlined, BellOutlined } from "@ant-design/icons";

const { Header: AntHeader } = Layout;
const { Search } = Input;

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

export const Header: React.FC<HeaderProps> = ({ collapsed, onToggle }) => {
  return (
    <AntHeader
      style={{
        background: "#fff",
        padding: "0 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid #f0f0f0",
        height: 64,
      }}
    >
      <Space>
        {(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined)({
          onClick: onToggle,
          style: { fontSize: 18, cursor: "pointer", color: "#666" },
        })}
      </Space>
      <Space size="middle">
        <Search placeholder="Search tasks..." style={{ width: 250 }} />
        <BellOutlined style={{ fontSize: 18, cursor: "pointer", color: "#666" }} />
      </Space>
    </AntHeader>
  );
};
