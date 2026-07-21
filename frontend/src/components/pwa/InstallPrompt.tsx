/* PWA install banner — mobile + desktop Chromium */

import { Button } from "antd";
import { DownloadOutlined, CloseOutlined } from "@ant-design/icons";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";
import { useI18nStore } from "@/i18n";

export function InstallPrompt() {
  const { canInstall, showIosTip, promptInstall, dismiss } = useInstallPrompt();
  const locale = useI18nStore((s) => s.locale);
  const zh = locale !== "en";

  if (!canInstall && !showIosTip) return null;

  return (
    <div className="af-pwa-install af-no-print" role="dialog" aria-label="Install app">
      <DownloadOutlined style={{ fontSize: 22, color: "var(--af-primary)" }} />
      <div className="af-pwa-install__text">
        {zh ? "安装 AgentFlow 到本机" : "Install AgentFlow"}
        <small>
          {showIosTip
            ? zh
              ? "Safari：分享 → 添加到主屏幕"
              : "Safari: Share → Add to Home Screen"
            : zh
              ? "支持 Windows / macOS / Linux / Android 桌面快捷方式"
              : "Windows / macOS / Linux / Android shortcut"}
        </small>
      </div>
      {canInstall && (
        <Button type="primary" size="small" onClick={() => void promptInstall()}>
          {zh ? "安装" : "Install"}
        </Button>
      )}
      <Button
        type="text"
        size="small"
        icon={<CloseOutlined />}
        onClick={dismiss}
        aria-label="Dismiss"
      />
    </div>
  );
}
