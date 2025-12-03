# Nginx 部署教程

本文档介绍如何使用 Nginx 部署 Mul_in_ONE 项目,包括前端静态文件服务和后端 API 反向代理配置。

## 前置条件

- 已安装 Nginx (推荐使用官方 Debian/Ubuntu 包)
- 后端服务已启动并运行在 8000 端口
- 前端构建产物已准备就绪

## 1. 安装 Nginx

### 安装官方 Nginx

```bash
# 更新包列表
sudo apt update

# 安装 nginx
sudo apt install -y nginx

# 验证安装
systemctl status nginx
```

## 2. 部署前端

### 2.1 克隆前端构建产物

```bash
# 进入网站根目录
cd /home/mio/www

# 克隆 build-artifacts 分支(包含前端构建产物)
git clone -b build-artifacts https://github.com/KirisameLonnet/Mul_in_ONE.git Mul_in_ONE-build-artifacts
```

### 2.2 设置目录权限

Nginx 需要有权限访问网站目录:

```bash
# 设置目录权限
chmod 755 /home/mio
chmod 755 /home/mio/www
chmod -R 755 /home/mio/www/Mul_in_ONE-build-artifacts
```

## 3. 配置 Nginx

### 3.1 创建站点配置文件

创建 `/etc/nginx/sites-available/mul-in-one` 文件:

> 该配置文件为最基础的http80端口无ssl配置，需要域名解析与https访问，ssl加密等自行修改，本配置只作演示baseline方案
```nginx
server {
    listen 80;
    server_name 154.9.254.118;  # 替换为您的域名或 IP
    
    # API 反向代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # WebSocket 支持
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
    
    # Persona avatars 静态文件
    location /persona-avatars/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # 前端静态文件根目录
    root /home/mio/www/Mul_in_ONE-build-artifacts;
    index index.html;
    
    # 前端路由处理 (SPA 应用)
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # 前端 assets 缓存
    location /assets {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # 日志文件
    access_log /var/log/nginx/mul-in-one-access.log;
    error_log /var/log/nginx/mul-in-one-error.log;
}
```

### 3.2 启用站点配置

```bash
# 创建软链接启用站点
sudo ln -sf /etc/nginx/sites-available/mul-in-one /etc/nginx/sites-enabled/mul-in-one

# 测试配置文件语法
sudo nginx -t

# 重载 Nginx 配置
sudo systemctl reload nginx
```

## 4. 验证部署

### 4.1 检查服务状态

```bash
# 检查 Nginx 状态
sudo systemctl status nginx

# 检查后端服务
ps aux | grep uvicorn
```

### 4.2 测试访问

```bash
# 测试前端
curl -I http://YOUR_IP_OR_DOMAIN

# 测试 API (应返回 405 Method Not Allowed,因为 login 需要 POST)
curl -I http://YOUR_IP_OR_DOMAIN/api/auth/login
```

打开浏览器访问 `http://YOUR_IP_OR_DOMAIN`,应该能看到前端页面并正常使用。

## 5. 常见问题

### 5.1 权限被拒绝 (Permission Denied)

**现象**: Nginx 错误日志显示 `stat() failed (13: Permission denied)`

**解决方案**:
```bash
# 确保用户主目录可执行
chmod 755 /home/mio
chmod 755 /home/mio/www
chmod -R 755 /home/mio/www/Mul_in_ONE-build-artifacts
```

### 5.2 API 请求返回 405 错误

**现象**: 前端调用 API 时收到 405 Not Allowed

**原因**: Nginx 没有正确配置反向代理,API 请求被当作静态文件处理

**解决方案**: 确保配置文件中 `location /api/` 块在 `location /` 之前,并且正确配置了反向代理。

### 5.3 Immutable 文件无法删除

**现象**: 删除文件时提示 `Operation not permitted`,即使使用 sudo

**解决方案**:
```bash
# 检查文件属性
lsattr /path/to/file

# 移除 immutable 属性
sudo chattr -i /path/to/file

# 然后再删除
sudo rm /path/to/file
```

### 5.4 WebSocket 连接失败

**现象**: 实时消息功能无法工作

**解决方案**: 确保配置了 `/ws/` location 块,并设置了正确的 WebSocket 相关头部:
- `Upgrade` 和 `Connection` 头
- `proxy_read_timeout` 设置为足够长的时间

## 6. 配置说明

### 6.1 路由优先级

Nginx 按照以下顺序匹配 location:

1. `/api/` - API 请求转发到后端
2. `/ws/` - WebSocket 请求转发到后端
3. `/persona-avatars/` - 头像静态文件转发到后端
4. `/assets` - 前端静态资源(启用长期缓存)
5. `/` - 其他所有请求(SPA 路由回退到 index.html)

### 6.2 缓存策略

- **API 请求**: 禁用缓存 (`proxy_cache_bypass`)
- **前端 assets**: 1年缓存,适合带哈希的静态资源
- **index.html**: 不缓存,确保能获取最新版本

### 6.3 日志位置

- 访问日志: `/var/log/nginx/mul-in-one-access.log`
- 错误日志: `/var/log/nginx/mul-in-one-error.log`

查看日志:
```bash
# 实时查看访问日志
sudo tail -f /var/log/nginx/mul-in-one-access.log

# 查看错误日志
sudo tail -f /var/log/nginx/mul-in-one-error.log
```


## 7. 管理命令

```bash
# 启动 Nginx
sudo systemctl start nginx

# 停止 Nginx
sudo systemctl stop nginx

# 重启 Nginx
sudo systemctl restart nginx

# 重载配置(无缝重载,不中断服务)
sudo systemctl reload nginx

# 测试配置文件
sudo nginx -t

# 查看 Nginx 状态
sudo systemctl status nginx
```