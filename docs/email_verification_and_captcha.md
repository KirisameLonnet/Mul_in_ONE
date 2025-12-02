# 邮箱验证和人机验证配置指南

本文档说明如何配置邮箱验证和 Cloudflare Turnstile 人机验证功能。

## 1. 邮箱验证配置

### 后端环境变量

在 `.envrc` 或环境配置中添加以下 SMTP 邮件服务器配置：

```bash
# SMTP 邮件服务器配置
export SMTP_HOST="smtp.gmail.com"              # SMTP 服务器地址
export SMTP_PORT="587"                          # SMTP 端口（通常是 587 或 465）
export SMTP_USER="your-email@gmail.com"        # 发件人邮箱
export SMTP_PASSWORD="your-app-password"       # 邮箱密码或应用专用密码
export SMTP_FROM_EMAIL="your-email@gmail.com"  # 发件人地址（可选，默认同 SMTP_USER）
export SMTP_FROM_NAME="Mul-in-ONE"             # 发件人名称（可选）
```

### 常见邮件服务提供商配置

#### Gmail

```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-16-digit-app-password"  # 需要启用两步验证并生成应用专用密码
```

**Gmail 设置步骤：**

1. 启用两步验证：https://myaccount.google.com/security
2. 生成应用专用密码：https://myaccount.google.com/apppasswords
3. 使用生成的 16 位密码作为 `SMTP_PASSWORD`

#### Outlook/Hotmail

```bash
export SMTP_HOST="smtp-mail.outlook.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@outlook.com"
export SMTP_PASSWORD="your-password"
```

#### QQ 邮箱

```bash
export SMTP_HOST="smtp.qq.com"
export SMTP_PORT="587"
export SMTP_USER="your-qq@qq.com"
export SMTP_PASSWORD="your-authorization-code"  # QQ 邮箱授权码，非登录密码
```

**QQ 邮箱设置步骤：**

1. 登录 QQ 邮箱网页版
2. 设置 -> 账户 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
3. 开启"POP3/SMTP服务"或"IMAP/SMTP服务"
4. 生成授权码

### 测试邮件发送

启动后端后，注册新用户会自动发送验证邮件。查看后端日志确认邮件是否发送成功：

```bash
./scripts/start_backend.sh
# 查看日志
tail -f logs/backend.log
```

## 2. Cloudflare Turnstile 配置 （未经测试）

Cloudflare Turnstile 是一个免费的、注重隐私的验证码替代方案。

### 2.1 获取 Turnstile 密钥

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 选择你的域名（或创建一个新账户）
3. 导航到 "Turnstile" 页面
4. 点击 "Add Site" 创建新站点
5. 获取 **Site Key** 和 **Secret Key**

### 2.2 后端配置

在 `.envrc` 中添加：

```bash
# Cloudflare Turnstile 配置
export TURNSTILE_SECRET_KEY="your-secret-key-here"
```

### 2.3 前端配置

在 `src/mio_frontend/mio-frontend/.env` 中添加：

```bash
# Cloudflare Turnstile Site Key
VITE_TURNSTILE_SITE_KEY=your-site-key-here
```

### 2.4 开发环境配置

在开发环境中，可以使用 Cloudflare 提供的测试密钥（总是通过验证）：

**测试 Site Key（始终通过）：**

```
1x00000000000000000000AA
```

**测试 Secret Key：**

```
1x0000000000000000000000000000000AA
```

**测试 Site Key（始终失败）：**

```
2x00000000000000000000AB
```

**测试 Secret Key：**

```
2x0000000000000000000000000000000AA
```

### 2.5 禁用 Turnstile（开发模式）

如果不想在开发时使用 Turnstile，只需不设置环境变量：

- 前端：不设置 `VITE_TURNSTILE_SITE_KEY`，验证码组件不会显示
- 后端：不设置 `TURNSTILE_SECRET_KEY`，服务器会跳过验证

## 3. 功能说明

### 邮箱验证流程

1. 用户注册后，系统自动发送验证邮件
2. 用户点击邮件中的验证链接
3. 系统验证 token 并标记邮箱为已验证
4. 用户可以正常使用所有功能

**API 端点：**

- `POST /api/auth/register` - 注册（会触发邮件发送）
- `POST /api/auth/verify` - 验证邮箱
- `POST /api/auth/request-verify-token` - 重新发送验证邮件
- `POST /api/auth/forgot-password` - 忘记密码（发送重置邮件）
- `POST /api/auth/reset-password` - 重置密码

### Turnstile 验证流程

1. 用户在注册页面填写信息
2. Turnstile 组件显示并等待用户完成挑战
3. 用户提交表单时，前端获取 Turnstile token
4. 后端验证 token 是否有效
5. 验证通过后完成注册

**API 端点：**

- `POST /api/auth/register-with-captcha` - 带验证码的注册

## 4. 前端页面

新增页面：

- `/verify-email` - 邮箱验证页面（处理邮件中的验证链接）
- `/reset-password` - 密码重置页面（可选，需要另外实现）

更新页面：

- `/register` - 注册页面（已集成 Turnstile）

## 5. 安全建议

1. **生产环境必须配置真实的 Turnstile 密钥**，不要使用测试密钥
2. **SMTP 密码使用应用专用密码**，不要使用账户主密码
3. **定期轮换 Secret Key**
4. **监控异常注册行为**，必要时调整 Turnstile 安全级别
5. **使用 HTTPS** 确保 token 传输安全

## 6. 故障排查

### 邮件发送失败

检查：

1. SMTP 配置是否正确
2. 是否启用了应用专用密码
3. 防火墙是否允许 SMTP 端口
4. 查看后端日志获取详细错误信息

### Turnstile 验证失败

检查：

1. Site Key 和 Secret Key 是否匹配
2. 域名是否在 Cloudflare Turnstile 站点配置中
3. 网络连接是否正常
4. 浏览器控制台是否有错误

### 开发环境快速测试

```bash
# 使用测试密钥（无需真实配置）
export TURNSTILE_SECRET_KEY="1x0000000000000000000000000000000AA"
export VITE_TURNSTILE_SITE_KEY="1x00000000000000000000AA"

# 跳过邮件发送（不设置 SMTP）
# 用户可以直接使用，无需验证邮箱
```

## 7. 依赖包

后端需要安装：

```bash
# 已包含在 pyproject.toml 中
httpx  # 用于 Turnstile API 调用
```

前端无需额外安装包，Turnstile 使用 CDN 加载。
