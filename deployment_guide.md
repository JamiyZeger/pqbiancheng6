# 腾讯云部署指南

本文档将指导您如何将此Flask应用部署到腾讯云服务器上，使其可以通过公网访问。

## 前提条件

- 已购买腾讯云服务器（CVM）
- 已获取服务器的公网IP地址
- 已获取服务器的登录凭证（密码或密钥）

## 部署步骤

### 1. 连接到腾讯云服务器

#### Windows用户
- 使用PuTTY或其他SSH客户端连接
- 主机名：您的服务器公网IP
- 端口：22
- 用户名：root或其他管理员账号

#### Mac/Linux用户
```bash
ssh username@服务器公网IP
```

### 2. 安装必要的软件包

```bash
# 更新软件包列表
sudo apt update  # Ubuntu/Debian系统
# 或
sudo yum update  # CentOS系统

# 安装Python和pip
sudo apt install python3 python3-pip  # Ubuntu/Debian系统
# 或
sudo yum install python3 python3-pip  # CentOS系统

# 安装Git（用于克隆代码）
sudo apt install git  # Ubuntu/Debian系统
# 或
sudo yum install git  # CentOS系统
```

### 3. 创建应用目录并上传代码

方法一：使用Git（如果您的代码在Git仓库中）
```bash
mkdir -p /var/www/flask_app
cd /var/www/flask_app
git clone 您的Git仓库URL .
```

方法二：直接上传文件
- 使用SFTP工具（如FileZilla）将本地项目文件上传到服务器的`/var/www/flask_app`目录

### 4. 安装Python依赖

```bash
cd /var/www/flask_app
pip3 install -r requirements.txt
```

### 5. 配置防火墙和安全组

1. 登录腾讯云控制台
2. 进入云服务器CVM实例详情页
3. 点击「安全组」
4. 添加入站规则：
   - 协议：TCP
   - 端口：5002（或您计划使用的端口）
   - 来源：0.0.0.0/0（允许所有IP访问）或限定特定IP范围

### 6. 使用Screen保持应用在后台运行

```bash
# 安装screen
sudo apt install screen  # Ubuntu/Debian系统
# 或
sudo yum install screen  # CentOS系统

# 创建新的screen会话
screen -S flask_app

# 在screen会话中启动应用
cd /var/www/flask_app
python3 app.py

# 按Ctrl+A，然后按D，将会分离screen会话并保持应用在后台运行
```

### 7. 设置应用开机自启动（可选）

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/flask_app.service
```

添加以下内容：

```
[Unit]
Description=Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/flask_app
ExecStart=/usr/bin/python3 /var/www/flask_app/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable flask_app
sudo systemctl start flask_app
```

### 8. 配置Nginx作为反向代理（推荐）

安装Nginx：

```bash
sudo apt install nginx  # Ubuntu/Debian系统
# 或
sudo yum install nginx  # CentOS系统
```

创建Nginx配置文件：

```bash
sudo nano /etc/nginx/sites-available/flask_app
```

添加以下内容：

```
server {
    listen 80;
    server_name 您的服务器IP或域名;

    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

创建符号链接并重启Nginx：

```bash
# Ubuntu/Debian系统
sudo ln -s /etc/nginx/sites-available/flask_app /etc/nginx/sites-enabled/
sudo nginx -t  # 测试配置
sudo systemctl restart nginx

# CentOS系统
sudo ln -s /etc/nginx/sites-available/flask_app /etc/nginx/conf.d/
sudo nginx -t  # 测试配置
sudo systemctl restart nginx
```

## 访问您的应用

完成以上步骤后，您可以通过以下方式访问应用：

- 如果配置了Nginx：http://您的服务器IP或域名
- 如果只开放了应用端口：http://您的服务器IP:5002

## 故障排查

1. 检查应用是否正在运行：
```bash
ps aux | grep python
```

2. 检查端口是否正在监听：
```bash
netstat -tuln | grep 5002
```

3. 检查防火墙设置：
```bash
# Ubuntu/Debian系统
sudo ufw status

# CentOS系统
sudo firewall-cmd --list-all
```

4. 查看应用日志：
```bash
# 如果使用systemd
sudo journalctl -u flask_app

# 如果使用screen
screen -r flask_app
```

## 注意事项

1. 生产环境中，建议将应用的`debug`模式关闭，修改`app.py`中的：
```python
app.run(host='0.0.0.0', port=5002, debug=False)
```

2. 考虑使用HTTPS增强安全性，可以通过Nginx配置SSL证书实现。

3. 定期备份数据文件（users.xlsx, accounts.xlsx, logs.xlsx）。

4. 确保服务器安全设置得当，定期更新系统和软件包。