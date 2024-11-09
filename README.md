# FeedVault「Flask 订阅管理系统」

![img.png](img.png)

你好，我是悦创。

该项目是一个基于 Flask 的订阅管理系统，主要功能包括：

- 管理员后台管理用户账户、密码有效期
- 用户使用账户密码登录后，可以查看并访问专属的订阅链接
- 支持用户订阅链接的有效期管理

## 功能介绍

### 1. 本地文件读取

该系统可以读取本地的 `iggfeed.yaml` 文件内容，当用户成功登录后可以下载此文件。

### 2. 管理员后台管理

- **管理员登录**：管理员可以使用账户和密码登录后台管理系统。
- **用户管理**：管理员可以添加新用户，为用户设置密码及订阅有效期。
- **有效期管理**：管理员可以随时调整用户订阅的有效期，包括延长有效期。
- **用户删除**：支持手动删除指定用户。

### 3. 用户订阅链接

- **用户登录**：用户需通过用户名和密码登录系统。
- **专属订阅链接**：登录后，每个用户可以看到唯一的订阅链接及其有效期，链接内容为 `iggfeed.yaml` 文件的内容。
- **链接有效期**：当链接过期后，将无法访问。管理员可以在后台对链接有效期进行延长。

## 项目结构

```plaintext
your_project/
│
├── app.py                 # 主应用文件
├── config.py              # 配置文件
├── templates/             # 前端模板文件
│   ├── admin.html         # 管理员后台模板
│   ├── login.html         # 管理员登录模板
│   ├── user_login.html    # 用户登录模板
│   └── subscription.html  # 用户订阅页面模板
├── static/
│   └── style.css          # 样式文件
└── iggfeed.yaml           # 本地 YAML 文件
```

## 安装与运行

1. 克隆该项目：

   ```bash
   git clone https://github.com/your_username/your_project.git
   cd your_project
   ```

2. 安装依赖：

   ```bash
   pip install flask flask_sqlalchemy flask_bcrypt
   ```

3. 配置文件 `config.py`

   在 `config.py` 文件中配置数据库 URI 和密钥：

   ```python
   import os

   class Config:
       SECRET_KEY = os.urandom(24)
       SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
       SQLALCHEMY_TRACK_MODIFICATIONS = False
   ```

4. 创建数据库并运行应用：

   ```bash
   python app.py
   ```

5. 访问应用：

   - 管理员登录页面：`http://127.0.0.1:5000/login`
   - 用户登录页面：`http://127.0.0.1:5000/user_login`

## 使用说明

### 管理员操作

- 管理员可以登录后台，进行用户管理，包括添加用户、删除用户、延长用户订阅有效期。
- 默认管理员账号的用户名为 `admin`，密码为 `admin_password`，可以根据需要在 `app.py` 中修改。

### 用户操作

- 用户可以使用管理员设置的用户名和密码登录系统。
- 登录成功后，用户可以在订阅页面查看专属订阅链接以及有效期信息。

## 注意事项

- 默认管理员账号密码为 `admin/admin_password`，上线时建议进行修改。
- 可以根据需求自定义本地的 `iggfeed.yaml` 文件内容。
- 请确保正确配置 Flask 的 SECRET_KEY，以保证会话安全。

## 贡献

欢迎提交 issues 或者 pull requests 来贡献代码。感谢您的支持！

## 许可

该项目基于 MIT 许可。
