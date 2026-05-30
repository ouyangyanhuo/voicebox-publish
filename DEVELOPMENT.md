# Voicebox 开发指南

## 环境要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ (推荐 3.12) | ML 依赖兼容性 |
| Bun | >= 1.3.8 | JS 包管理器和运行时 |
| Rust | stable | Tauri 桌面构建 |
| just | 最新 | 命令运行器 |

### 安装 just

```powershell
# Windows (Scoop)
scoop install just

# Windows (Cargo)
cargo install just

# macOS
brew install just
```

### 安装 Bun

```powershell
# Windows (PowerShell)
powershell -c "irm bun.sh/install.ps1 | iex"

# macOS / Linux
curl -fsSL https://bun.sh/install | bash
```

## 首次安装

```powershell
just setup
```

这个命令会：
1. 在 `backend/venv/` 创建 Python 虚拟环境
2. 安装所有 Python 依赖（包括 PyTorch、Transformers、FastAPI 等）
3. 安装所有 JS 依赖（`bun install`）
4. Windows 上自动检测 GPU：
   - NVIDIA → 安装 CUDA 版 PyTorch
   - Intel Arc → 安装 XPU 版 PyTorch
   - 其他 → CPU 版 PyTorch

## 启动开发

### 完整桌面开发（推荐）

```powershell
just dev
```

启动 Python 后端（端口 17493）+ Tauri 桌面应用。

### 只启动后端

```powershell
just dev-backend
```

适合只需要调试 API 或运行测试的场景。

### 只启动前端

```powershell
just dev-frontend
```

后端必须已经在运行。

### 浏览器版开发

```powershell
just dev-web
```

启动后端 + 浏览器版 Vite 应用，不需要 Tauri。

### 停止所有开发进程

```powershell
just kill
```

## 代码检查

```powershell
just check          # JS/TS (Biome) + Python (ruff) 全量检查
just lint           # 只检查
just format         # 只格式化
just fix            # 自动修复
bun run typecheck   # TypeScript 类型检查
```

## 测试

```powershell
just test           # 运行后端 pytest 测试套件
```

## 构建

```powershell
just build          # CPU 服务端二进制 + Tauri 安装包
just build-local    # Windows: CPU + CUDA + Tauri 安装包
just build-web      # 只构建 Web 版
```

## 清理

```powershell
just clean          # 清理构建产物
just clean-python   # 清理 Python venv 和缓存
just clean-all      # 全部清理（包括 node_modules、cargo）
```

## 项目结构

```
voicebox/
├── app/          # 共享 React 前端（组件、状态、路由）
├── tauri/        # Tauri 桌面壳（Rust + 原生功能）
├── web/          # 浏览器版入口
├── backend/      # Python FastAPI 后端（TTS/STT/LLM）
├── landing/      # 营销网站
├── docs/         # 文档站
├── scripts/      # 构建脚本
└── data/         # 开发数据目录（SQLite、音频、缓存）
```

## 后端 API

启动后访问：
- API: `http://127.0.0.1:17493`
- 文档: `http://127.0.0.1:17493/docs`

## 常见问题

### Python venv 找不到

运行 `just setup` 重新创建虚拟环境。

### Tauri 编译失败

确保已安装 Rust 工具链和 Tauri 依赖：
```powershell
rustup update
cargo install tauri-cli
```

### GPU 相关问题

`just setup` 会自动检测 GPU。如需手动切换：
```powershell
# NVIDIA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# CPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```
