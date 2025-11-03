# 🖥️ NetBoot-Python

一个使用 Python 编写的轻量级 **PXE / NetBoot 服务框架**，用于通过网络引导操作系统（如 Windows PE、Linux Live 系统等）。  
支持 **DHCP Proxy、TFTP、HTTP Boot**，可快速搭建自动化安装或远程维护环境。

---

> [!NOTE]
> 
> **当前项目仍处于 Demo 阶段 **  
> 本仓库目前尚未完全适配生产环境（目前在PD虚拟机efi模式下还存在问题！！！）

---

## 📦 功能特性

- 🧩 **DHCP Proxy**：无需修改原 DHCP 服务即可提供 PXE 启动选项。  
- 📡 **TFTP 服务**：提供 iPXE 引导脚本与启动镜像（`boot.ipxe`, `ipxe.efi` 等）。  
- 🌐 **HTTP 服务**：支持从 HTTP 提供 WinPE 或系统镜像文件。  
- ⚙️ **可配置化架构**：`config.py` 文件集中管理端口、路径等配置。  
- 📜 **日志管理模块**：`logutil.py` 提供统一日志输出与级别控制。  
- 🧠 **模块化设计**：独立的 `tftp_server.py`、`dhcp_proxy.py`、`http_server.py` 模块，易于扩展。  

---

## 🧰 目录结构说明

| 路径 | 说明 |
|------|------|
| `main.py` | 程序入口，启动各服务模块 |
| `config.py` | 配置文件（端口、IP、路径等） |
| `dhcp_proxy.py` | 实现 PXE 所需的 DHCP Proxy 功能 |
| `tftp_server.py` | 提供 TFTP 文件传输服务 |
| `http_server.py` | 启动 HTTP 文件服务器 |
| `netutil.py` | 网络工具函数封装 |
| `logutil.py` | 日志输出与调试支持 |
| `srv/tftp/` | TFTP 根目录（存放引导脚本和二进制文件） |
| `srv/http/winpe/` | HTTP 提供的 WinPE 或系统镜像目录 |
| `requirements.txt` | Python 依赖列表 |

---

## 🚀 快速开始

### 1️⃣ 环境要求

- Python ≥ 3.8  
- 运行于 Linux 或 macOS（Windows 可能需要管理员权限）  
- 需具备 root 权限以监听低端口（如 67/69）

### 2️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 3️⃣ 修改配置

编辑 `config.py`，根据你的网络环境调整：
```python
#这个暂时不用修改
```

### 4️⃣ 启动服务

```bash
# Windows 建议使用管理员模式运行
# macOS / Linux 请使用 sudo 或 root 权限
python main.py --ip 192.168.73.1 --http 8080 --log-level INFO
```

启动后，你将在控制台看到类似输出：

```bash
[INFO] DHCP Proxy listening on 0.0.0.0:67
[INFO] TFTP Server started on port 69
[INFO] HTTP Server running on port 8080
```

> [!WARNING]
>
> - 参数 `--ip` 必须填写 **本机的实际局域网 IP 地址**，**而不是网关地址（如 192.168.1.1）**。
> - 启动后，客户端 PXE 请求会直接访问此 IP 的 TFTP/HTTP 服务。
> - 当前项目仍处于 **Demo 演示状态**，需要手动修改 `srv/tftp/boot.ipxe` 文件中引用的服务器地址，以保持与实际 IP 一致。
>
> ```bash
> #示例
> # 修改 boot.ipxe 中的地址
> set base-url http://192.168.73.1:8080/winpe
> ```



---

## 🧪 典型使用场景

- 快速部署 Windows PE 启动环境  
- PXE 自动安装 Linux 系统  
- 本地局域网网络引导实验  
- DevOps / 装机房自动化环境支持  

---

## 🧱 示例目录结构（可部署）

```
srv/
├── tftp/
│   ├── undionly.kpxe
│   ├── ipxe.efi
│   ├── boot.ipxe
│   └── ...
└── http/
    └── winpe/
        └── boot.wim
```

---

## 🧾 日志与调试

日志默认输出到控制台，也可通过 `logutil.py` 配置为文件输出。
示例：
```python
log("TFTP request from 192.168.1.25", level="INFO")
```

---

## ⚠️ 注意事项

- 若使用 macOS，请关闭系统自带的防火墙或放行端口 67/69/8080。  
- Windows 用户运行需管理员权限。  
- 若 `boot.wim` 文件超过 GitHub 100MB 限制，请使用 **Git LFS** 或外部文件存储。  

---

## 📜 许可证

本项目基于 **MIT License** 开源，欢迎自由修改与分发。

---

## 👨‍💻 作者

**Liu Jiayun / L-LizhouYi**  
📧 Email: [liulang@eeho.cn](mailto:liulang@eeho.cn)  
🌐 GitHub: [https://github.com/L-LizhouYi](https://github.com/L-LizhouYi)
