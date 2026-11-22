"""配置加载与校验。仅使用 Python 标准库。

所有路径基于本文件位置用 pathlib 解析，不依赖当前工作目录；
适配容器内以 UID 1000 / GID 0 运行。不读取、不打印任何 Token、密码或环境变量。

新任务书要点：
  * 单轮测速：settings.json 中不得再出现 httping_url / httping_count / max_merged；
  * 六个 TXT 固定，禁止 merged.txt / global_top15.txt；
  * 地区映射独立维护在 regions.json，未确认 Colo 一律 UNKNOWN；
  * 六个文件独立校验、独立原子更新，不做整体事务。

4.1-R1 补充：
  * REGION_FILES / GLOBAL_FILE 为 six 个固定榜单的唯一名称来源（ranking / safety 共用）；
  * loss_unit 固定 ratio，但解析规则由 cfst.parse_loss 严格实现（不按数值大小猜测）；
  * download_count 保持可调（1~10000），当前初始 100；-dn 是下载测速候选数，非总扫描数。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# 项目根 = app/ 的父目录；不依赖 cwd
PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"
CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
REGIONS_PATH = CONFIG_DIR / "regions.json"
SAMPLES_DIR = PROJECT_ROOT / "samples"

TARGET_REGIONS = ("HK", "JP", "SG", "KR", "US")
UNKNOWN = "UNKNOWN"
REGION_FILES = tuple(code + ".txt" for code in TARGET_REGIONS)
GLOBAL_FILE = "global_top25.txt"
EXPECTED_RESULT_FILES = REGION_FILES + (GLOBAL_FILE,)
FORBIDDEN_RESULT_FILES = ("merged.txt", "global_top15.txt", "global_top10.txt")
FIXED_REGION_NAMES = {
    "HK": "HongKong", "JP": "Japan", "SG": "Singapore",
    "KR": "SouthKorea", "US": "UnitedStates", "UNKNOWN": "Unknown",
}

# 旧两轮测速配置键：出现即视为架构未清理干净
OBSOLETE_SETTING_KEYS = ("httping_url", "httping_count", "max_merged",
                         "first_round", "second_round")

_INT_RANGES = {
    "port": (1, 65535),
    "concurrency": (1, 1000),
    "latency_count": (1, 100),
    "download_count": (1, 10000),
    "download_duration": (1, 3600),
    "cfst_timeout_sec": (60, 86400),
    "region_top_n": (1, 100),
    "global_top_n": (1, 1000),
}
_STR_FIELDS = (
    "run_mode", "download_url", "cfst_binary", "ip_file",
    "speed_unit", "timezone", "loss_unit", "csv_path", "output_dir", "log_dir",
)
REQUIRED_SETTINGS = tuple(_INT_RANGES) + _STR_FIELDS + ("result_files", "schema_version")
_COLO_RE = re.compile(r"^[A-Z0-9]{2,10}$")


class ConfigError(ValueError):
    """配置缺失、类型或范围非法、Colo 映射冲突。"""


def _read_json(path: Path) -> dict:
    """读取 JSON，兼容 UTF-8 BOM；错误信息不含文件内容，避免泄露敏感配置。"""
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise ConfigError("配置文件不存在: %s" % path) from exc
    except json.JSONDecodeError as exc:
        raise ConfigError("JSON 解析失败: %s : %s" % (path, exc)) from exc
    except UnicodeDecodeError as exc:
        raise ConfigError("配置文件编码不是 UTF-8: %s" % path) from exc
    if not isinstance(data, dict):
        raise ConfigError("配置文件顶层必须是 JSON 对象: %s" % path)
    return data


def load_settings(path=None) -> dict:
    """读取并校验 settings.json，返回配置字典。"""
    p = Path(path) if path is not None else SETTINGS_PATH
    data = _read_json(p)

    missing = [k for k in REQUIRED_SETTINGS if k not in data]
    if missing:
        raise ConfigError("settings.json 缺少必填字段: %s" % ", ".join(missing))
    obsolete = [k for k in OBSOLETE_SETTING_KEYS if k in data]
    if obsolete:
        raise ConfigError("settings.json 仍含已废弃的两轮测速配置: %s" % ", ".join(obsolete))

    for key, (low, high) in _INT_RANGES.items():
        value = data[key]
        if type(value) is not int:  # bool 是 int 的子类，必须显式排除
            raise ConfigError("%s 必须是整数，实际为 %s" % (key, type(value).__name__))
        if not (low <= value <= high):
            raise ConfigError("%s 超出允许范围 %d~%d : %d" % (key, low, high, value))

    for key in _STR_FIELDS:
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise ConfigError("%s 必须是非空字符串" % key)

    if data["run_mode"] != "single_pass":
        raise ConfigError("run_mode 必须为 single_pass（禁止两轮测速）")
    if data["speed_unit"] != "MB/s":
        raise ConfigError("speed_unit 必须为 MB/s，禁止把 MB/s 与 Mbps 混用")
    if data["timezone"] != "Asia/Shanghai":
        raise ConfigError("timezone 必须为 Asia/Shanghai")
    if data["loss_unit"] != "ratio":
        raise ConfigError("loss_unit 必须为 ratio（CFST -tlr 范围为 0.00~1.00）")
    if not data["download_url"].startswith("https://speed.cloudflare.com/__down"):
        raise ConfigError("download_url 必须是 Cloudflare 官方下载测速地址")
    if not data["ip_file"].endswith("ip.txt"):
        raise ConfigError("ip_file 必须是完整 IPv4 地址段文件 ip.txt")
    if data["region_top_n"] != 5 or data["global_top_n"] != 25:
        raise ConfigError("region_top_n 必须为 5、global_top_n 必须为 25")

    files = data["result_files"]
    if not isinstance(files, list) or tuple(files) != EXPECTED_RESULT_FILES:
        raise ConfigError("result_files 必须恰好是六个固定 TXT: %s" % (EXPECTED_RESULT_FILES,))
    if any(name in FORBIDDEN_RESULT_FILES for name in files):
        raise ConfigError("result_files 不得包含任何合并订阅文件")
    return data


def load_regions(path=None) -> dict:
    """读取并校验 regions.json，返回配置字典。

    校验重点：五个地区固定存在、英文名固定、Colo 格式合法、
    同一 Colo 不得映射到多个地区、confirmed/pending/excluded 互不冲突、
    只有 confirmed 中的 Colo 才能进入地区映射。
    """
    p = Path(path) if path is not None else REGIONS_PATH
    data = _read_json(p)

    regions = data.get("regions")
    if not isinstance(regions, dict):
        raise ConfigError("regions.json 缺少 regions 对象")
    if tuple(sorted(regions)) != tuple(sorted(TARGET_REGIONS)):
        raise ConfigError("regions 必须且只能包含 HK/JP/SG/KR/US 五个地区")

    names = data.get("region_names")
    if not isinstance(names, dict) or any(
        names.get(k) != v for k, v in FIXED_REGION_NAMES.items()
    ):
        raise ConfigError("region_names 必须包含五个地区与 UNKNOWN 的固定英文名称")

    owner = {}
    for code, colos in regions.items():
        if not isinstance(colos, list):
            raise ConfigError("地区 %s 的 Colo 必须是数组" % code)
        for colo in colos:
            if not isinstance(colo, str) or not _COLO_RE.fullmatch(colo):
                raise ConfigError("地区 %s 的 Colo 格式非法: %r" % (code, colo))
            if colo in owner:
                raise ConfigError("Colo %s 同时映射到 %s 与 %s" % (colo, owner[colo], code))
            owner[colo] = code

    confirmed = data.get("confirmed", {})
    pending = data.get("pending", {})
    excluded = data.get("excluded", {})
    for bucket_name, group in (("confirmed", confirmed),
                               ("pending", pending), ("excluded", excluded)):
        if not isinstance(group, dict):
            raise ConfigError("%s 必须是对象" % bucket_name)

    def _keys(group):
        return {str(k).strip().upper() for k in group}

    c, p_, e = _keys(confirmed), _keys(pending), _keys(excluded)
    if c & p_ or c & e or p_ & e:
        raise ConfigError("confirmed / pending / excluded 存在互相冲突的 Colo")
    if set(owner) & (p_ | e):
        raise ConfigError("pending / excluded 中的 Colo 不得出现在 regions 映射中")
    if set(owner) - c:
        raise ConfigError("regions 中的每个 Colo 都必须在 confirmed 中有真实证据")

    policy = data.get("unknown_policy")
    if not isinstance(policy, str) or "UNKNOWN" not in policy:
        raise ConfigError("regions.json 必须声明 unknown_policy 并明确 UNKNOWN 归类")
    return data


def colo_map(regions_config: dict) -> dict:
    """由 regions 配置生成 {Colo: 地区} 反向映射（仅已确认映射）。"""
    return {
        colo.upper(): code
        for code, colos in regions_config["regions"].items()
        for colo in colos
    }


def region_names(regions_config: dict) -> dict:
    return dict(regions_config["region_names"])


def asset_paths(settings: dict) -> dict:
    """返回关键路径（不创建任何目录/文件）。"""
    return {
        "cfst_binary": PROJECT_ROOT / settings["cfst_binary"],
        "ip_file": PROJECT_ROOT / settings["ip_file"],
        "csv_path": PROJECT_ROOT / settings["csv_path"],
        "output_dir": PROJECT_ROOT / settings["output_dir"],
        "log_dir": PROJECT_ROOT / settings["log_dir"],
    }


def validate_all(settings_path=None, regions_path=None):
    """一次性加载并交叉校验两份配置，返回 (settings, regions)。"""
    settings = load_settings(settings_path)
    regions = load_regions(regions_path)
    if len(settings["result_files"]) != 6:
        raise ConfigError("结果文件必须恰好六个")
    return settings, regions
