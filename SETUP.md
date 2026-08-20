# 课表查询网页 · 离线自动刷新部署指南

目标：你的电脑关机后，网页（GitHub Pages）仍可访问，且课表数据每天自动从企业微信在线表刷新。

## 整体原理
- 本仓库包含：`fetch_all_sheets.sh`（拉取在线表）、`build_webapp.py`（生成网页）、`.github/workflows/refresh.yml`（定时任务）。
- 企业微信凭证以加密形式存为仓库 Secret `WECOM_CONFIG`，GitHub Actions 每次运行时还原到 `~/.config/wecom` 即可免扫码拉数据。
- 工作流每天北京时间 02:00 自动运行：拉表 → 构建 → 部署到 GitHub Pages。
- 你的电脑开不开机都不影响（GitHub 的服务器在跑）。

## 已为你准备好的文件（本机 `schedule-github/` 目录）
- `fetch_all_sheets.sh` / `build_webapp.py` / `.github/workflows/refresh.yml` / `pack_credentials.sh`
- `WECOM_CONFIG_SECRET.txt` —— **已在你本机生成**，这就是要填进 GitHub 的密钥值（此文件已被排除，不会进仓库）
- `webapp/`、`sheet_data/` —— 已构建好的网页与数据

---

# 详细 5 步（你还没有 GitHub 账号，从第 1 步开始）

## 第 1 步：注册 GitHub 账号
1. 打开 https://github.com
2. 点右上角 **Sign up**（注册）
3. 填邮箱 → 设密码 → 取用户名（username，例如 `yama-schedule`）→ 验证人机 → 点 Create account
4. 去邮箱收验证邮件，点 **Verify email address** 完成激活

## 第 2 步：新建仓库
1. 登录后，点右上角 **“+” → New repository**
2. Repository name（仓库名）：填 `schedule-web`（随意，记住它）
3. 可见性：**选 Public**（GitHub Pages 免费托管需要 Public）
4. 其它都**不要勾**（尤其不要勾 Add a README / .gitignore）
5. 点 **Create repository**

## 第 3 步：把企业微信凭证填进仓库密钥（最关键）
1. 打开本机文件 `C:\Users\Yama\WorkBuddy\2026-08-13-18-40-30\schedule-github\WECOM_CONFIG_SECRET.txt`
2. 用记事本打开，**全选复制全部内容**（是一长串字母数字，别漏头漏尾）
3. 回到 GitHub 刚建的仓库页面：
   - 点 **Settings**（右上角）→ 左侧 **Secrets and variables → Actions**
   - 点绿色按钮 **New repository secret**
   - Name 填：`WECOM_CONFIG`（必须一字不差）
   - Secret 框里**粘贴**刚才复制的内容
   - 点 **Add secret**
4. 看到列表里多了一行 `WECOM_CONFIG` 即成功

> 这个值只是你本机 wecom 凭证的加密打包，仅用于 CI 还原，不会以明文暴露给任何人。

## 第 4 步：把代码推送到 GitHub
下面给**两条路**，选一条你能顺手做的：

### 路径 A（推荐，最省事，不用记命令）：用 GitHub Desktop
1. 下载安装 GitHub Desktop：https://desktop.github.com/
2. 安装后登录你的 GitHub 账号（会自动弹浏览器授权）
3. 菜单 **File → Add Local Repository…**，选择文件夹
   `C:\Users\Yama\WorkBuddy\2026-08-13-18-40-30\schedule-github`
4. 它会识别到已有仓库（里面已经有提交记录）
5. 点右上角 **Publish repository**（发布仓库）
   - Name 填 `schedule-web`（和第 2 步一致）
   - 取消勾选 “Keep this code private”（要 Public）
   - 点 Publish
6. 等进度条走完，代码就上 GitHub 了

### 路径 B（命令行）：用 Git + 访问令牌
> 注意：GitHub 现在**不支持用账号密码推代码**，需要“Personal Access Token (PAT)”。
1. 装 Git（若已有可跳过）：https://git-scm.com/downloads ，一路 Next 安装
2. 生成令牌：GitHub 网页右上角头像 → **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**
   - Note 填 `schedule-push`
   - Expiration 选 **No expiration**（或自选）
   - 勾选 `repo`（全部子项）
   - 最底部 **Generate token** → **复制**这串 `ghp_xxx`（只显示一次！）
3. 在本机打开终端（PowerShell 或 Git Bash），执行：
   ```powershell
   cd C:\Users\Yama\WorkBuddy\2026-08-13-18-40-30\schedule-github
   git remote add origin https://github.com/你的用户名/schedule-web.git
   git branch -M main
   git push -u origin main
   ```
   - 用户名处填你第 1 步取的 username
   - 弹窗要密码时，**粘贴刚才的 PAT**（不是你的登录密码）

## 第 5 步：开启 GitHub Pages（让网页能被访问）
1. 回到 GitHub 仓库页面，点 **Settings**
2. 左侧 **Pages**
3. Build and deployment → Source 选 **GitHub Actions**
4. 保存（Save）
5. 此时 Actions 会自动跑一次：点仓库顶部 **Actions** 标签，能看到 `Refresh Schedule` 正在运行
6. 跑完（绿色对勾）后，Pages 地址会出现在 Settings → Pages 页面，形如：
   ```
   https://你的用户名.github.io/schedule-web/
   ```
   这个地址就是 **24 小时可访问、每天北京时间 02:00 自动刷新**的课表查询网页。

---

## 日常与维护
- **立即刷新一次**：仓库 **Actions → Refresh Schedule → Run workflow**（即使没到凌晨也能手动跑）
- **改刷新频率**：编辑 `.github/workflows/refresh.yml` 里的 `cron`（时间是 UTC，北京时间 = UTC+8，例如北京 02:00 = `0 18 * * *`）
- **凭证过期**：若某天 Actions 变红（数据停在旧版），通常是企业微信令牌过期。你下次开电脑执行 `wecom-cli auth init` 重新扫码，再跑 `pack_credentials.sh` 重新生成 `WECOM_CONFIG_SECRET.txt`，并回到第 3 步更新 Secret 即可。CI 每天用一次会自然续期，正常很少需要。
- **增删老师**：改 `fetch_all_sheets.sh` 的 `SHEETS` 与 `build_webapp.py` 的 `SHEET_MAP`，提交推送。

## 本地预览（可选）
```bash
cd schedule-github
bash fetch_all_sheets.sh
python3 build_webapp.py
# 用浏览器打开 webapp/index.html 即可本地预览
```
