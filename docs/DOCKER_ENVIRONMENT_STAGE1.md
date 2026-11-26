# Docker 环境基础层（Stage 1）

**状态：** 已提交代码；尚未在 NAS 构建或运行  
**主测速工具：** CFST v2.3.5  
**目标平台：** QNAP TS-453Dmini / Intel J4125 / linux/amd64

## 本阶段交付

- `Dockerfile`：下载官方 CFST v2.3.5 Linux amd64 预编译包，校验 SHA-256 后安装到运行镜像。
- `compose.yaml`：提供手动调用的 CFST 服务，独立 bridge 网络、只读根文件系统、非 root 用户和输入/输出目录映射。
- `.dockerignore` / `.gitignore`：排除本地测量数据、输出文件和密钥。
- 根目录 `README.md`：构建、查看帮助和目录说明。

## CFST 固定版本与校验

- Release：`https://github.com/XIU2/CloudflareSpeedTest/releases/tag/v2.3.5`
- Asset：`cfst_linux_amd64.tar.gz`
- SHA-256：`c4c8fc76b4e1bf2bdb5ced8b765956d82dda7bc4eb59df5c04053f0f7db98d90`

校验值来自官方 GitHub v2.3.5 Release 页面列出的资产摘要。Docker build 会执行 SHA-256 校验，校验失败即停止构建。

## 设计约束

1. 不在 NAS 上编译 Go，也不要求安装 git/go/gcc/make。
2. 容器目标架构固定为 linux/amd64。
3. 容器以 UID 1000、GID 100 运行，以匹配 NAS 文件访问身份。
4. 容器 rootfs 只读；仅 `/output` 挂载可写，`/work` 和 `/tmp` 使用 tmpfs。
5. 输入目录只读挂载；输出目录独立挂载。
6. Compose 服务放在 `manual` profile 下，不会因普通 `docker compose up` 自动启动。
7. 容器环境清空 HTTP_PROXY、HTTPS_PROXY、ALL_PROXY，并设置 NO_PROXY=*。
8. 不配置 host network，不发布端口，不修改 NAS、路由器、Mihomo、AdGuard 或 Docker daemon 网络配置。
9. 当前不实现调度、通知、GitHub 发布或 EdgeTunnel 自动覆盖。

## NAS 手动验证命令

在 NAS 项目目录中执行：

```bash
docker compose --profile manual build cfst
docker compose --profile manual run --rm cfst -h
```

第二条只查看 CFST 帮助，不会开始测速。

候选列表放在：

```text
data/input/ip.txt
```

输出目录：

```text
data/output/
```

## 尚未实现

- CFST 参数配置与正式测速命令。
- CSV 表头/编码兼容解析和完整性校验。
- TCP/TLS/HTTP/Trace/下载数据模型。
- 质量过滤、复测、稳定性评价和最终排序。
- EdgeTunnel 订阅行生成与原子更新。
- 定时任务、通知和 GitHub 自动发布。

这些功能需在参数和数据契约确认后分阶段实现。当前代码提交不代表已在 NAS 部署或通过运行测试。
