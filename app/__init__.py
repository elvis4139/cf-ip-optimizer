"""cf-ip-optimizer 自动测速程序（阶段 4.1 修订版：单轮测速 / 六榜独立发布）。

本阶段只做代码架构修订与离线测试：
不执行真实测速、不发网络请求、不启动容器、不创建 Cron、不上传 GitHub、
不修改 EdgeTunnel、不更新正式订阅文件。

已废弃的旧两轮逻辑（HTTPing 初筛 + 按地区分别下载）不得再出现：
任何模块都不得构造第二条 CFST 命令，也不得读取第二轮 Colo 做分类。
"""

from __future__ import annotations

__version__ = "4.1.4-r3"
__stage__ = "4.1-R3"

# 4.1-R3：CSV 证据绑定 / source 白名单 / freshness 异常收敛 / 两 JSON 独立
# 异常边界 / lexists 识别断开符号链接 / 凭据扫描补强 / 生产归档失败不得 success。
# 阶段边界不变：仍禁止真实测速、容器启动、Cron、GitHub 与任何外部发布。

__all__ = [
    "config", "cfst", "region", "ranking", "output", "safety", "pipeline", "main",
]
