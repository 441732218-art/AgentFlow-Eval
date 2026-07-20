# AgentFlow Desktop (Electron)

Native installers for **Windows / macOS / Linux**. The shell loads the built SPA and talks to a local or remote API.

## Prerequisites

- Node.js 18+
- Backend API reachable (default `http://127.0.0.1:8000`)
- Frontend built with Electron base:

```powershell
cd frontend
npm ci
npm run build:electron
```

## Install desktop deps & package

```powershell
cd frontend
npm run build:electron

cd ..\desktop
npm ci

# Windows: disable code-sign discovery (avoids winCodeSign symlink admin errors)
$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
npm run dist:win

# Linux / macOS (run on matching OS)
# npm run dist:linux
# npm run dist:mac
```

## CI: GitHub Actions (macOS)

正式 **macOS `.dmg` / `.zip`** 在 GitHub 的 `macos-latest` runner 上构建（不能在 Windows/Linux 容器交叉编译）。

| 触发 | 说明 |
|------|------|
| **Actions → Desktop macOS → Run workflow** | 手动打一次 mac 包 |
| `push` 到 `frontend/**` / `desktop/**` | PR / 相关路径变更时构建 |
| `v*` tag | 构建并把 dmg/zip 挂到 Release（若 tag 推送） |

工作流文件：`.github/workflows/desktop-macos.yml`

1. 打开仓库 **Actions** 页  
2. 选择 **Desktop macOS**  
3. **Run workflow**（分支选 `main`）  
4. 跑完后在该 run 的 **Artifacts** 下载 `AgentFlow-macOS-<sha>`

默认 **未签名**（无需 Apple 证书）。若要 Gatekeeper 友好分发，需在仓库 Secrets 配置 Apple 签名/公证后再改 workflow。

Windows outputs (unsigned, fine for internal delivery):

| File | Use |
|------|-----|
| `release/AgentFlow-*-win-x64.exe` | NSIS 安装程序（可选目录） |
| `release/AgentFlow-*-win-portable.exe` | 绿色免安装 |
| `release/win-unpacked/` | 解压目录，直接运行 exe |

Artifacts: `desktop/release/`

| OS | Artifacts |
|----|-----------|
| Windows | NSIS installer + portable `.exe` |
| macOS | `.dmg` + `.zip` |
| Linux | `.AppImage` + `.deb` |

## Dev mode

```powershell
# Terminal 1: API
cd backend; uvicorn app.main:app --port 8000

# Terminal 2: Vite
cd frontend; npm run dev

# Terminal 3: Electron
cd desktop; npm start
```

Env:

| Variable | Default | Meaning |
|----------|---------|---------|
| `AGENTFLOW_API_URL` | `http://127.0.0.1:8000` | Backend base |
| `AGENTFLOW_UI_URL` | (empty) | Force remote UI URL |
| `AGENTFLOW_DEV_URL` | `http://127.0.0.1:5173` | Dev Vite URL |

## Mobile

Desktop Electron does **not** target phones. Use the **PWA** build (`npm run build:pwa` in `frontend`) and install from browser (Android Chrome / iOS Safari Add to Home Screen / desktop Chromium).
