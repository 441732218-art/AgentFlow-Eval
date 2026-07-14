/* Lightweight command palette — Ctrl/Cmd+K */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Modal, Input, List, Typography, Tag, Space, Divider } from "antd";
import {
  DashboardOutlined,
  UnorderedListOutlined,
  PlusCircleOutlined,
  BarChartOutlined,
  SettingOutlined,
  SearchOutlined,
  MoonOutlined,
  SunOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTasks } from "@/hooks";
import { isDarkTheme, useThemeStore } from "@/stores/useThemeStore";

const { Text } = Typography;

export const OPEN_COMMAND_PALETTE = "af:open-command-palette";

export function openCommandPalette(initialQuery = "") {
  window.dispatchEvent(
    new CustomEvent(OPEN_COMMAND_PALETTE, { detail: { query: initialQuery } })
  );
}

type CommandItem = {
  key: string;
  label: string;
  icon: React.ReactNode;
  group: string;
  path?: string;
  action?: () => void;
  keywords?: string;
};

const NAV_COMMANDS: CommandItem[] = [
  {
    key: "nav-dashboard",
    label: "总览 Dashboard",
    icon: <DashboardOutlined />,
    group: "导航",
    path: "/",
    keywords: "home overview 首页",
  },
  {
    key: "nav-tasks",
    label: "任务列表",
    icon: <UnorderedListOutlined />,
    group: "导航",
    path: "/tasks",
    keywords: "tasks list 任务",
  },
  {
    key: "nav-create",
    label: "创建任务",
    icon: <PlusCircleOutlined />,
    group: "导航",
    path: "/tasks/create",
    keywords: "new create 新建",
  },
  {
    key: "nav-reports",
    label: "评测报告",
    icon: <BarChartOutlined />,
    group: "导航",
    path: "/reports",
    keywords: "reports 报告",
  },
  {
    key: "nav-settings",
    label: "设置",
    icon: <SettingOutlined />,
    group: "导航",
    path: "/settings",
    keywords: "settings config 配置",
  },
];

const SHORTCUTS = [
  { keys: "Ctrl / ⌘ + K", desc: "打开命令面板" },
  { keys: "Esc", desc: "关闭面板" },
  { keys: "↑ / ↓", desc: "选择命令" },
  { keys: "Enter", desc: "执行选中项" },
  { keys: "/", desc: "顶栏聚焦搜索（部分浏览器）" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const [showHelp, setShowHelp] = useState(false);
  const navigate = useNavigate();
  const { mode, toggle } = useThemeStore();
  const { data } = useTasks({ page: 1, page_size: 20 });

  const openWith = useCallback((query = "") => {
    setQ(query);
    setActive(0);
    setShowHelp(false);
    setOpen(true);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => {
          if (!v) {
            setQ("");
            setActive(0);
            setShowHelp(false);
          }
          return !v;
        });
      }
    };
    const onOpen = (e: Event) => {
      const detail = (e as CustomEvent<{ query?: string }>).detail;
      openWith(detail?.query ?? "");
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_COMMAND_PALETTE, onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_COMMAND_PALETTE, onOpen);
    };
  }, [openWith]);

  const actionCommands = useMemo<CommandItem[]>(
    () => [
      {
        key: "act-theme",
        label: isDarkTheme(mode) ? "切换到亮色主题" : "切换到深色主题",
        icon: isDarkTheme(mode) ? <SunOutlined /> : <MoonOutlined />,
        group: "操作",
        keywords: "theme dark light 主题 暗色 亮色 midnight emerald ocean sunset",
        action: () => toggle(),
      },
      {
        key: "act-help",
        label: "查看键盘快捷键",
        icon: <QuestionCircleOutlined />,
        group: "操作",
        keywords: "help shortcuts 快捷键 帮助",
        action: () => setShowHelp(true),
      },
    ],
    [mode, toggle]
  );

  const taskCommands = useMemo<CommandItem[]>(() => {
    return (data?.items ?? []).slice(0, 12).map((t) => ({
      key: `task-${t.id}`,
      label: t.name,
      icon: <ExperimentOutlined />,
      group: "最近任务",
      path: `/tasks/${t.id}`,
      keywords: `${t.status} ${t.created_by ?? ""} ${t.id}`,
    }));
  }, [data?.items]);

  const reportCommands = useMemo<CommandItem[]>(() => {
    return (data?.items ?? [])
      .filter((t) => ["completed", "failed", "timeout", "cancelled"].includes(t.status))
      .slice(0, 6)
      .map((t) => ({
        key: `report-${t.id}`,
        label: `报告 · ${t.name}`,
        icon: <FileTextOutlined />,
        group: "报告",
        path: `/reports/${t.id}`,
        keywords: `report ${t.status} ${t.id}`,
      }));
  }, [data?.items]);

  const allCommands = useMemo(
    () => [...NAV_COMMANDS, ...actionCommands, ...taskCommands, ...reportCommands],
    [actionCommands, taskCommands, reportCommands]
  );

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return allCommands;
    return allCommands.filter((c) => {
      const hay = `${c.label} ${c.key} ${c.path ?? ""} ${c.group} ${c.keywords ?? ""}`.toLowerCase();
      return hay.includes(s);
    });
  }, [allCommands, q]);

  useEffect(() => {
    setActive(0);
  }, [q, open]);

  const run = useCallback(
    (item: CommandItem) => {
      if (item.action) {
        item.action();
        if (item.key !== "act-help") setOpen(false);
        return;
      }
      if (item.path) {
        setOpen(false);
        navigate(item.path);
      }
    },
    [navigate]
  );

  const onListKeyDown = (e: React.KeyboardEvent) => {
    if (!filtered.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % filtered.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i - 1 + filtered.length) % filtered.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      run(filtered[active]);
    }
  };

  // Group labels for visual sectioning (preserve order of first appearance)
  const groups = useMemo(() => {
    const order: string[] = [];
    const map = new Map<string, CommandItem[]>();
    filtered.forEach((c) => {
      if (!map.has(c.group)) {
        map.set(c.group, []);
        order.push(c.group);
      }
      map.get(c.group)!.push(c);
    });
    return order.map((g) => ({ group: g, items: map.get(g)! }));
  }, [filtered]);

  let flatIndex = -1;

  return (
    <Modal
      open={open}
      onCancel={() => setOpen(false)}
      footer={null}
      closable={false}
      width={560}
      styles={{
        content: {
          padding: 12,
          borderRadius: 16,
          background: "var(--af-bg-surface)",
          border: "1px solid var(--af-border)",
          boxShadow: "var(--af-shadow-md)",
        },
      }}
      destroyOnClose
    >
      <Input
        autoFocus
        size="large"
        prefix={<SearchOutlined style={{ color: "var(--af-text-muted)" }} />}
        placeholder="搜索页面、任务、报告或操作…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={onListKeyDown}
        style={{ marginBottom: 8 }}
        suffix={<span className="af-kbd">Esc</span>}
      />

      {showHelp ? (
        <div style={{ padding: "8px 4px 4px" }}>
          <Text strong style={{ display: "block", marginBottom: 10 }}>
            键盘快捷键
          </Text>
          {SHORTCUTS.map((s) => (
            <div
              key={s.keys}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "8px 4px",
                borderBottom: "1px solid var(--af-border)",
              }}
            >
              <Text type="secondary" style={{ fontSize: 13 }}>
                {s.desc}
              </Text>
              <span className="af-kbd">{s.keys}</span>
            </div>
          ))}
          <div style={{ marginTop: 12, textAlign: "right" }}>
            <Text
              style={{ color: "var(--af-primary)", cursor: "pointer", fontSize: 13 }}
              onClick={() => setShowHelp(false)}
            >
              返回命令列表
            </Text>
          </div>
        </div>
      ) : (
        <>
          <div style={{ maxHeight: 380, overflow: "auto" }}>
            {groups.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center" }}>
                <Text type="secondary">无匹配结果</Text>
              </div>
            ) : (
              groups.map(({ group, items }) => (
                <div key={group} style={{ marginBottom: 6 }}>
                  <Text
                    type="secondary"
                    style={{
                      fontSize: 11,
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                      padding: "6px 10px 4px",
                      display: "block",
                    }}
                  >
                    {group}
                  </Text>
                  <List
                    size="small"
                    dataSource={items}
                    split={false}
                    renderItem={(item) => {
                      flatIndex += 1;
                      const idx = flatIndex;
                      const selected = idx === active;
                      return (
                        <List.Item
                          style={{
                            cursor: "pointer",
                            borderRadius: 10,
                            padding: "10px 12px",
                            border: "none",
                            background: selected ? "var(--af-primary-soft)" : "transparent",
                            outline: selected ? "1px solid var(--af-border-strong)" : "none",
                          }}
                          className="af-card-hover"
                          onClick={() => run(item)}
                          onMouseEnter={() => setActive(idx)}
                        >
                          <List.Item.Meta
                            avatar={
                              <span style={{ color: "var(--af-primary)", fontSize: 16 }}>
                                {item.icon}
                              </span>
                            }
                            title={<Text>{item.label}</Text>}
                            description={
                              item.path ? (
                                <Tag style={{ marginTop: 2, fontSize: 11 }}>{item.path}</Tag>
                              ) : (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  操作
                                </Text>
                              )
                            }
                          />
                        </List.Item>
                      );
                    }}
                  />
                </div>
              ))
            )}
          </div>

          <Divider style={{ margin: "8px 0" }} />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0 4px",
            }}
          >
            <Space size={8}>
              <span className="af-kbd">↑↓</span>
              <span className="af-kbd">Enter</span>
              <Text
                type="secondary"
                style={{ fontSize: 11, cursor: "pointer" }}
                onClick={() => setShowHelp(true)}
              >
                快捷键
              </Text>
            </Space>
            <Text type="secondary" style={{ fontSize: 11 }}>
              Ctrl / ⌘ + K
            </Text>
          </div>
        </>
      )}
    </Modal>
  );
}
