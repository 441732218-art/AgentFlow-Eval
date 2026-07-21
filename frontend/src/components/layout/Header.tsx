import { useState } from "react";
import { Layout, Input, Space, Button, Tooltip, Badge, Typography, Dropdown, Grid } from "antd";
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  MoonOutlined,
  SunOutlined,
  SearchOutlined,
  GlobalOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { isDarkTheme, useThemeStore } from "@/stores/useThemeStore";
import { NotificationDrawer } from "./NotificationDrawer";
import { openCommandPalette } from "@/components/CommandPalette";
import { useNotificationStore } from "@/stores/useNotificationStore";
import { useI18nStore, type Locale } from "@/i18n";
import { HeaderQuotaBadge } from "@/components/billing/HeaderQuotaBadge";

const { Header: AntHeader } = Layout;
const { Text } = Typography;
const { useBreakpoint } = Grid;

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

export const Header: React.FC<HeaderProps> = ({ collapsed, onToggle }) => {
  const { mode, toggle } = useThemeStore();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const isPhone = !screens.md;
  const [notifyOpen, setNotifyOpen] = useState(false);
  const unread = useNotificationStore((s) => s.events.filter((e) => !e.read).length);
  const liveCount = useNotificationStore(
    (s) =>
      s.events.filter((e) =>
        ["running", "queued", "judging", "waiting_tool"].includes(e.status)
      ).length
  );
  const badgeCount = unread > 0 ? unread : liveCount;
  const t = useI18nStore((s) => s.t);
  const locale = useI18nStore((s) => s.locale);
  const setLocale = useI18nStore((s) => s.setLocale);

  return (
    <>
      <AntHeader
        className="af-no-print ic-header"
        style={{
          padding: isPhone ? "0 10px" : "0 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: isPhone ? 56 : 64,
          position: "sticky",
          top: 0,
          zIndex: 15,
          gap: 8,
        }}
      >
        <Space size={isPhone ? 4 : "middle"} style={{ minWidth: 0, flex: 1 }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={onToggle}
            aria-label="Toggle navigation"
            style={{ color: "var(--af-text-secondary)", minWidth: 40, minHeight: 40 }}
          />
          {!isPhone && (
            <Input
              readOnly
              className="ic-header__search"
              onClick={() => openCommandPalette()}
              prefix={<SearchOutlined style={{ color: "var(--af-text-muted)" }} />}
              placeholder={t("header.search")}
              suffix={
                <Text type="secondary" style={{ fontSize: 11 }}>
                  <span className="af-kbd">⌘K</span>
                </Text>
              }
              style={{
                width: screens.xl ? 300 : 220,
                maxWidth: "42vw",
                cursor: "pointer",
              }}
            />
          )}
          {isPhone && (
            <Button
              type="text"
              icon={<SearchOutlined />}
              onClick={() => openCommandPalette()}
              aria-label={t("header.search")}
              style={{ color: "var(--af-text-secondary)", minWidth: 40, minHeight: 40 }}
            />
          )}
        </Space>

        <Space size={isPhone ? 2 : 8} wrap={false}>
          {!isPhone && <HeaderQuotaBadge />}
          <Dropdown
            menu={{
              selectedKeys: [locale],
              items: [
                { key: "zh", label: t("settings.lang.zh"), onClick: () => setLocale("zh" as Locale) },
                { key: "en", label: t("settings.lang.en"), onClick: () => setLocale("en" as Locale) },
              ],
            }}
            placement="bottomRight"
          >
            <Tooltip title={t("settings.language")}>
              <Button
                type="text"
                icon={<GlobalOutlined />}
                style={{ color: "var(--af-text-secondary)", minWidth: 40, minHeight: 40 }}
              />
            </Tooltip>
          </Dropdown>
          <Tooltip
            title={isDarkTheme(mode) ? t("header.theme.dark") : t("header.theme.light")}
          >
            <Button
              type="text"
              icon={isDarkTheme(mode) ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggle}
              style={{ color: "var(--af-text-secondary)", minWidth: 40, minHeight: 40 }}
            />
          </Tooltip>
          <Tooltip title={t("header.notify")}>
            <Badge count={badgeCount} size="small" offset={[-2, 2]}>
              <Button
                type="text"
                icon={<BellOutlined />}
                onClick={() => setNotifyOpen(true)}
                style={{ color: "var(--af-text-secondary)", minWidth: 40, minHeight: 40 }}
              />
            </Badge>
          </Tooltip>
          {!isPhone && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "4px 10px 4px 4px",
                borderRadius: 999,
                border: "1px solid var(--af-border)",
                background: "var(--af-bg-muted)",
                cursor: "pointer",
              }}
              onClick={() => navigate("/settings")}
              title={t("nav.settings")}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: "var(--af-gradient)",
                  display: "grid",
                  placeItems: "center",
                  color: "#fff",
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                AF
              </div>
              <Text className="af-workspace-label" style={{ fontSize: 13 }}>
                {t("header.workspace")}
              </Text>
            </div>
          )}
        </Space>
      </AntHeader>

      <NotificationDrawer open={notifyOpen} onClose={() => setNotifyOpen(false)} />
    </>
  );
};
