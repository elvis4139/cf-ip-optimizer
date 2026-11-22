# 阶段 4.1 关键源码审查材料（只读导出）

- 导出时间：2026-11-22 16:33 Asia/Shanghai
- 来源：NAS `/share/Container/cf-ip-optimizer/`，SSH 只读执行 `sed -n '1,420p'` / `cat`
- 本地副本与 NAS 文件 SHA256 逐个一致（阶段 4.1 已双向复核），下列内容逐字取自本地同哈希副本
- 六个 Python 文件共 890 行，全部 <= 420 行，无截断、无需补充剩余部分
- 本轮未修改任何代码或配置；data/ logs/ 仍为空

## 0 行数与 SHA256（NAS 实测）

```
app/cfst.py               236 行  d3f7325d64d8490dbc5ad439bfd1ed3710d359c66daafe438e0e9570b4aced94
app/pipeline.py           138 行  cfd4e221ee3928b89267699d3444c74d4f1a44d37f1ab5143a7ceaf975c8d2b7
app/ranking.py             98 行  0d80743f2dacc0fe7f18615d772b2f086b578853773ead173e7503ede2529e57
app/region.py              64 行  4ddb1f8c03e9a29ff8c3ac361e6921d64dc794905b21ca1f24f16db5465b78b1
app/safety.py             139 行  e231cdbefe5cba3d6b260b5bda6831e5407664ed525f945aa006768c53cc1aab
app/config.py             215 行  63eacb034085b573196ee9ebb62944c871a070561449ddfa8aa3e77f8764df94
config/settings.json       28 行  bc0f5af89e0399604b8f88ace6b98dd784b9ca12c2ea3f615528692b94bbca18
config/regions.json        42 行  998745250d900520000599da43b3c1f4ef59e92a077984295079b771e8d7f83a
```


## app/cfst.py  (236 行, sha256=d3f7325d64d8490dbc5ad439bfd1ed3710d359c66daafe438e0e9570b4aced94)

```python
"""单轮 CFST 命令构造与 CSV 解析。

依据 NAS 上 CFST v2.3.5 的 -h 与 samples/ 6 份历史 CSV 实证：
  * CSV 表头: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
  * 普通 TCPing + 下载模式（不加 -httping / -dd）确实同时输出速度、延迟、
    丢包率与地区码：samples/phase2-download-3ip.csv 与
    samples/phase2-download-cloudflare-108.csv 中可见 SIN/LAX 与 15.84/15.22 MB/s。
    -> 这是「单轮成立」的离线证据；完整真实 CSV 仍须阶段 4.4 验证。
  * -cfcolo 仅 HTTPing 模式可用；-dd 禁用下载测速；-tlr 说明丢包率范围 0.00~1.00。
  * 下载速度单位是 MB/s，不是 Mbps。

架构铁律：本模块只提供 build_command() 一个命令构造函数，
一次运行只产生一条命令、一份 CSV；不存在第一轮/第二轮命令构造器。
execute_cfst() 在阶段 4.1 是拒绝执行的占位，保证本阶段无法触发真实测速。
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from pathlib import Path

from .config import PROJECT_ROOT, asset_paths

CSV_HEADER = "IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码"
CSV_REQUIRED_FIELDS = ("IP 地址", "已发送", "已接收", "丢包率",
                       "平均延迟", "下载速度(MB/s)", "地区码")

# 按字段名解析，绝不依赖固定列序号
HEADER_ALIASES = {
    "ip": ("IP 地址", "IP地址", "IP Address", "IP", "ip"),
    "sent": ("已发送", "发送", "Sent", "sent"),
    "received": ("已接收", "接收", "Received", "received"),
    "loss": ("丢包率", "丢包", "Loss", "loss"),
    "latency": ("平均延迟", "延迟", "Average Latency", "latency"),
    "speed": (
        "下载速度(MB/s)", "下载速度（MB/s）", "下载速度 (MB/s)",
        "下载速度", "Download Speed (MB/s)", "speed",
    ),
    "colo": ("地区码", "Colo", "colo", "地区"),
}

FORBIDDEN_FLAGS = ("-httping", "-httping-code", "-dd", "-cfcolo")
NA_TEXTS = {"", "N/A", "NA", "NULL", "NONE", "-", "--", "UNKNOWN"}


class CsvError(ValueError):
    """CFST CSV 缺字段、结构不完整或编码无法识别。"""


@dataclass(frozen=True)
class CsvRow:
    """一条 CSV 原始记录（保留字符串原值，数值校验交给 ranking）。"""

    ip: str
    sent: str
    received: str
    loss: str
    latency: str
    speed: str
    colo: str


@dataclass
class CsvData:
    header: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    malformed_rows: list = field(default_factory=list)  # (行号, 原因)

    @property
    def total_rows(self) -> int:
        return len(self.rows) + len(self.malformed_rows)


def build_command(settings: dict, csv_out=None) -> list:
    """构造唯一一条完整 CFST 测速命令（参数列表，供 subprocess 使用）。

    不拼接 shell 字符串；不含 -httping / -httping-code / -dd / -cfcolo。
    """
    paths = asset_paths(settings)
    out = Path(csv_out) if csv_out is not None else paths["csv_path"]
    argv = [
        str(paths["cfst_binary"]),
        "-url", settings["download_url"],
        "-f", str(paths["ip_file"]),
        "-dn", str(settings["download_count"]),
        "-dt", str(settings["download_duration"]),
        "-n", str(settings["concurrency"]),
        "-t", str(settings["latency_count"]),
        "-tp", str(settings["port"]),
        "-o", str(out),
    ]
    violations = command_violations(argv, settings)
    if violations:
        raise CsvError("构造出非法 CFST 命令: %s" % "; ".join(violations))
    return argv


def command_violations(argv: list, settings: dict) -> list:
    """返回命令中的违规项；空列表代表合法。供离线测试逐条断言。"""
    problems = []
    tokens = [str(x) for x in argv]
    for flag in FORBIDDEN_FLAGS:
        if flag in tokens:
            problems.append("出现禁用参数 %s" % flag)
    if any(t.startswith("-httping") for t in tokens):
        problems.append("出现 -httping 系列参数")
    if tokens.count("-o") != 1:
        problems.append("CSV 输出参数 -o 数量不等于 1")
    if tokens.count("-url") != 1 or settings["download_url"] not in tokens:
        problems.append("未使用唯一官方 Cloudflare 下载地址")
    if "-f" not in tokens:
        problems.append("缺少 -f 完整 IPv4 文件")
    elif not tokens[tokens.index("-f") + 1].endswith("ip.txt"):
        problems.append("-f 未指向 ip.txt")
    if tokens[0] != str(PROJECT_ROOT / settings["cfst_binary"]):
        problems.append("CFST 二进制路径与配置不一致")
    return problems


def execute_cfst(argv: list, timeout_sec=None):
    """真实执行 CFST 的占位接口：阶段 4.1 禁止真实测速，调用即拒绝。

    后续阶段实现时使用 subprocess.run(argv, shell=False, timeout=..., ...)，
    argv 必须是参数列表；本阶段不存在任何可调用它的路径（--run 直接拒绝）。
    """
    raise NotImplementedError(
        "阶段 4.1 禁止执行真实 CFST 测速；须在阶段 4.4 获得用户明确授权后启用"
    )


def finite_float(text) -> float | None:
    """把字符串转为有限浮点数；N/A、空值、NaN、Infinity 一律返回 None。"""
    s = str(text).strip() if text is not None else ""
    if s.upper() in NA_TEXTS:
        return None
    try:
        value = float(s)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def parse_loss(text, unit: str = "ratio") -> float | None:
    """把丢包率归一化为 0.00~1.00 的比率。

    CFST -h 中 -tlr 的范围是 0.00~1.00，因此 CSV 的 0.00 表示 0% 丢包。
    兼容写法：'0.25'->0.25、'25%'->0.25、'25'(>1，视为百分数)->0.25。
    负数、N/A、NaN、Infinity、归一化后 >1 的值一律返回 None。
    注意：真实 CSV 的单位仍须在阶段 4.4 复核；此处按 -h 文档取 ratio。
    """
    s = str(text).strip() if text is not None else ""
    percent_sign = s.endswith("%")
    if percent_sign:
        s = s[:-1].strip()
    value = finite_float(s)
    if value is None or value < 0:
        return None
    if unit == "percent" or percent_sign or value > 1.0:
        value = value / 100.0
    if not (0.0 <= value <= 1.0):
        return None
    return value


def _decode(raw: bytes, path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CsvError("CSV 编码无法识别: %s" % path)


def parse_csv_text(text: str) -> CsvData:
    """按表头名解析 CFST CSV 文本，兼容 UTF-8 BOM、GBK 与中文表头。"""
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return CsvData()

    header = [cell.strip() for cell in rows[0]]
    index = {}
    for key, aliases in HEADER_ALIASES.items():
        position = next((header.index(a) for a in aliases if a in header), None)
        if position is None:
            raise CsvError("CSV 缺少字段 %s；实际表头: %s" % (key, header))
        index[key] = position

    data = CsvData(header=header)
    for line_no, row in enumerate(rows[1:], start=2):
        if len(row) < len(header):
            data.malformed_rows.append((line_no, "列数不足 %d" % len(header)))
            continue
        data.rows.append(CsvRow(
            ip=row[index["ip"]].strip(),
            sent=row[index["sent"]].strip(),
            received=row[index["received"]].strip(),
            loss=row[index["loss"]].strip(),
            latency=row[index["latency"]].strip(),
            speed=row[index["speed"]].strip(),
            colo=row[index["colo"]].strip(),
        ))
    return data


def parse_csv_file(path) -> CsvData:
    p = Path(path)
    if not p.is_file():
        raise CsvError("CSV 文件不存在: %s" % p)
    return parse_csv_text(_decode(p.read_bytes(), p))


def validate_csv_completeness(path):
    """判断一次完整测速的 CSV 是否可信。返回 (bool, 原因, CsvData|None)。"""
    p = Path(path)
    if not p.is_file():
        return False, "CSV 文件不存在", None
    if p.stat().st_size == 0:
        return False, "CSV 为空文件", None
    try:
        data = parse_csv_file(p)
    except CsvError as exc:
        return False, str(exc), None
    missing = [field for field in CSV_REQUIRED_FIELDS if field not in data.header]
    if missing:
        return False, "CSV 缺少表头字段: %s" % ", ".join(missing), data
    if data.malformed_rows:
        return False, "CSV 有 %d 行截断/列数不足" % len(data.malformed_rows), data
    if not data.rows:
        return False, "CSV 无数据行", data
    return True, "完整", data
```


## app/pipeline.py  (138 行, sha256=cfd4e221ee3928b89267699d3444c74d4f1a44d37f1ab5143a7ceaf975c8d2b7)

```python
"""一次完整 CFST 测速 -> 一份 CSV -> 六个独立 TXT 的编排（新增模块）。

本阶段（4.1）只在临时目录里用「模拟 runner」离线运行，runner 默认指向
cfst.execute_cfst()，而后者在 4.1 直接拒绝，因此不存在触发真实测速的路径。

关键隔离语义：
  * runner 失败 / 退出码非 0 / CSV 不完整 -> 六个文件全部 skipped，旧文件一个都不动；
  * 测速成功后，六个文件逐个 try/except 独立发布，单个失败不影响其他；
  * 测速成功但某地区无有效节点 -> render 为空字符串 -> 更新为空文件（情况 A）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import cfst, output, ranking, safety
from .config import (
    EXPECTED_RESULT_FILES, TARGET_REGIONS, asset_paths, colo_map, region_names,
)

CST = timezone(timedelta(hours=8), "Asia/Shanghai")


def _default_runner(command, csv_path, timeout_sec):
    """生产入口；阶段 4.1 调用即被拒绝。"""
    return cfst.execute_cfst(command, timeout_sec)


def _skipped(reason: str) -> dict:
    return {
        "status": "skipped", "node_count": None, "reason": reason,
        "atomic_replace": False,
    }


def run_once(settings: dict, regions: dict, *, runner=None, csv_path=None,
             output_dir=None, validator_overrides=None, replace_fn=None,
             now_iso=None) -> dict:
    """执行一次完整流程；返回运行状态字典（不打印任何敏感信息）。"""
    names = region_names(regions)
    cmap = colo_map(regions)
    paths = asset_paths(settings)
    csv_file = Path(csv_path) if csv_path is not None else paths["csv_path"]
    out_dir = Path(output_dir) if output_dir is not None else paths["output_dir"]
    validator_overrides = validator_overrides or {}
    run = runner or _default_runner

    status = {
        "run_time": now_iso or datetime.now(CST).isoformat(timespec="seconds"),
        "timezone": settings["timezone"],
        "run_mode": settings["run_mode"],
        "cfst_command": cfst.build_command(settings, csv_file),
        "cfst_exit_code": None,
        "csv_complete": False,
        "csv_total_rows": 0,
        "valid_ip_count": 0,
        "files": {},
        "failed_files": [],
        "skipped_files": [],
        "fastest_node": None,
        "measurement_success": False,
        "all_files_updated": False,
        "speed_unit": settings["speed_unit"],
    }

    # --- 阶段 A：一次完整测速；失败则六个文件全部不更新 ---
    try:
        exit_code = run(status["cfst_command"], csv_file, settings["cfst_timeout_sec"])
    except Exception as exc:
        reason = "CFST 执行异常（%s）: %s" % (type(exc).__name__, exc)
        status["files"] = {name: _skipped(reason) for name in EXPECTED_RESULT_FILES}
        status["skipped_files"] = list(EXPECTED_RESULT_FILES)
        status["failure_reason"] = reason
        return status
    status["cfst_exit_code"] = exit_code
    if exit_code != 0:
        reason = "CFST 退出码非 0 (%s)，完整测速失败" % exit_code
        status["files"] = {name: _skipped(reason) for name in EXPECTED_RESULT_FILES}
        status["skipped_files"] = list(EXPECTED_RESULT_FILES)
        status["failure_reason"] = reason
        return status

    complete, reason, csv_data = cfst.validate_csv_completeness(csv_file)
    status["csv_complete"] = complete
    if not complete:
        reason = "CSV 不完整: %s" % reason
        status["files"] = {name: _skipped(reason) for name in EXPECTED_RESULT_FILES}
        status["skipped_files"] = list(EXPECTED_RESULT_FILES)
        status["failure_reason"] = reason
        return status

    status["csv_total_rows"] = csv_data.total_rows
    status["measurement_success"] = True

    # --- 阶段 B：同一份 CSV 解析、一次排序、六榜取用 ---
    candidates = [
        c for c in (
            ranking.make_candidate(row, cmap, settings["loss_unit"])
            for row in csv_data.rows
        ) if c is not None
    ]
    status["valid_ip_count"] = len(candidates)
    boards = ranking.select_boards(candidates, settings)
    contents = output.render_all_boards(boards, settings, names)
    status["fastest_node"] = output.fastest_node_of(boards, settings, names)

    # --- 阶段 C：六个文件各自校验、各自原子替换，互不阻塞 ---
    for name in EXPECTED_RESULT_FILES:
        try:
            content = contents[name]
            expected_lines = content.splitlines()
            override = validator_overrides.get(name)
            default_validator = lambda text, _n=name, _e=expected_lines: safety.validate_txt(
                text, filename=_n, expected_lines=_e, settings=settings,
                names=names,
                max_lines=(settings["global_top_n"] if _n == safety.GLOBAL_FILE
                           else settings["region_top_n"]),
            )
            validator = override or default_validator
            result = safety.publish_one(out_dir / name, content, validator,
                                        replace_fn=replace_fn)
        except Exception as exc:
            result = {
                "status": "failed", "node_count": None,
                "reason": "生成/渲染异常（%s）: %s" % (type(exc).__name__, exc),
                "atomic_replace": False,
            }
        status["files"][name] = result
        if result["status"] == "failed":
            status["failed_files"].append(name)
        elif result["status"] == "skipped":
            status["skipped_files"].append(name)

    status["all_files_updated"] = (
        all(status["files"][n]["status"] == "updated" for n in EXPECTED_RESULT_FILES)
    )
    return status
```


## app/ranking.py  (98 行, sha256=0d80743f2dacc0fe7f18615d772b2f086b578853773ead173e7503ede2529e57)

```python
"""六榜排名（同一份 CSV，一次排序，多榜取用）。

排序规则（六个榜单完全一致）：
  1. 下载速度 MB/s 降序
  2. 平均延迟 ms 升序
  3. 丢包率（0~1 比率）升序
  4. 全部相同时以 IP 地址作为最后的稳定排序条件

有效记录：IP 合法、速度 > 0、延迟与丢包率为有限非负数、无 NaN/Infinity/负数、
N/A 速度不算有效成绩。未知 Colo 可以进入全球榜，但不得进入任何地区榜。
不做跨文件去重，也不做合并；地区榜不足 5 条就输出实际条数，不拿别地区 IP 凑数。
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from .cfst import finite_float, parse_loss
from .config import TARGET_REGIONS, UNKNOWN
from .region import classify, normalize_colo


@dataclass(frozen=True)
class Candidate:
    ip: str
    speed: float          # MB/s
    latency: float        # ms
    loss: float           # 0.00~1.00 比率
    colo: str             # 规范化后的 Colo（N/A -> UNKNOWN）
    region: str           # HK/JP/SG/KR/US 或 UNKNOWN


def is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(str(value).strip())
        return True
    except (ValueError, TypeError):
        return False


def _ip_sort_key(value: str):
    try:
        return (int(ipaddress.ip_address(value)),)
    except (ValueError, TypeError):
        return (0,)


def make_candidate(row, colo_map: dict, loss_unit: str = "ratio") -> Candidate | None:
    """把一条原始 CSV 行转为有效候选；任何字段不合格即返回 None。"""
    ip = str(row.ip).strip()
    if not is_valid_ip(ip):
        return None
    speed = finite_float(row.speed)
    if speed is None or speed <= 0:
        return None
    latency = finite_float(row.latency)
    if latency is None or latency < 0:
        return None
    loss = parse_loss(row.loss, loss_unit)
    if loss is None:
        return None
    colo = normalize_colo(row.colo)
    return Candidate(
        ip=ip,
        speed=speed,
        latency=latency,
        loss=loss,
        colo=colo,
        region=classify(colo, colo_map),
    )


def sort_candidates(candidates) -> list:
    """统一排序：速度降序 -> 延迟升序 -> 丢包率升序 -> IP 稳定升序。"""
    return sorted(
        candidates,
        key=lambda c: (-c.speed, c.latency, c.loss, _ip_sort_key(c.ip)),
    )


def select_boards(candidates, settings: dict) -> dict:
    """由同一份已排序候选生成六个榜单内容（键为固定文件名）。

    不跨文件去重：global_top25.txt 与地区榜可以包含同一个 IP。
    """
    ranked = sort_candidates(candidates)
    boards = {}
    for code in TARGET_REGIONS:
        boards[code + ".txt"] = [
            c for c in ranked if c.region == code
        ][:settings["region_top_n"]]
    boards["global_top25.txt"] = ranked[:settings["global_top_n"]]
    return boards


def board_stats(boards: dict) -> dict:
    return {name: len(items) for name, items in boards.items()}
```


## app/region.py  (64 行, sha256=4ddb1f8c03e9a29ff8c3ac361e6921d64dc794905b21ca1f24f16db5465b78b1)

```python
"""Colo 到目标地区的映射（单轮 CSV 直接归类，不再有两轮映射）。

重要：Colo 是本轮 CFST CSV 的地区码，即 Cloudflare Anycast 落点机场码，
不是 IP 的地理归属；同一 IP 在不同网络、不同时间可能落到不同节点。
本模块只按 regions.json 中已确认的映射归类，未确认代码一律 UNKNOWN；
绝不根据 IP 段、国家常识或历史样本猜测地区。
"""

from __future__ import annotations

import re

from .config import UNKNOWN

NA_VALUES = {"", "N/A", "NA", "NONE", "NULL", "-", "--", "UNKNOWN"}
_COLO_TOKEN_RE = re.compile(r"^[A-Z0-9]{2,10}$")


def normalize_colo(colo) -> str:
    """规范化 Colo；N/A、空值等归为 UNKNOWN。"""
    if colo is None:
        return UNKNOWN
    text = str(colo).strip().upper()
    if text in NA_VALUES:
        return UNKNOWN
    return text


def classify(colo, colo_map: dict) -> str:
    """返回 HK/JP/SG/KR/US 之一，或 UNKNOWN；绝不猜测。"""
    code = normalize_colo(colo)
    if code == UNKNOWN:
        return UNKNOWN
    return colo_map.get(code, UNKNOWN)


def colo_token(colo) -> str:
    """节点备注中使用的 Colo 标记。

    合法机场码原样大写输出（DEN/AMS/XYZ 等未知代码也保留，便于审计）；
    N/A、空值或含非法字符的值统一写作 NA，绝不伪装成某个国家。
    """
    code = normalize_colo(colo)
    if code == UNKNOWN or not _COLO_TOKEN_RE.fullmatch(code):
        return "NA"
    return code


def is_confirmed(colo, regions_config: dict) -> bool:
    return normalize_colo(colo) in {
        str(k).upper() for k in regions_config.get("confirmed", {})
    }


def is_pending(colo, regions_config: dict) -> bool:
    return normalize_colo(colo) in {
        str(k).upper() for k in regions_config.get("pending", {})
    }


def is_excluded(colo, regions_config: dict) -> bool:
    return normalize_colo(colo) in {
        str(k).upper() for k in regions_config.get("excluded", {})
    }
```


## app/safety.py  (139 行, sha256=e231cdbefe5cba3d6b260b5bda6831e5407664ed525f945aa006768c53cc1aab)

```python
"""六个 TXT 的独立校验与单文件原子更新。

铁律：
  * 每个文件独立生成、独立校验、独立 os.replace()，一个失败不影响其他五个；
  * 完整测速失败（退出码非 0 或 CSV 不完整）时，六个文件一律不更新；
  * 情况 A（测速成功但某地区无有效节点）-> 该文件更新为空文件；
  * 情况 B（生成/写入/校验异常）-> 删除临时文件，只保留该文件上次成功版本；
  * 不做六文件整体事务、不做 current symlink、不生成 merged.txt。

阶段 4.1 只在临时目录里做离线模拟，不写 NAS 正式订阅文件。
"""

from __future__ import annotations

import ipaddress
import os
import re
import tempfile
from pathlib import Path

from .config import EXPECTED_RESULT_FILES, TARGET_REGIONS, UNKNOWN

# IP:端口#地区-英文名-Colo-整数ms
_LINE_RE = re.compile(
    r"^(\[[0-9A-Fa-f:]+\]|(?:\d{1,3}\.){3}\d{1,3}):(\d{1,5})#"
    r"([A-Z]{2}|UNKNOWN)-([A-Za-z]+)-([A-Z0-9]{2,10})-(\d+)ms$"
)
_SECRET_MARKERS = ("ghp_", "github_pat_", "Authorization:", "password=", "token=",
                   "SendKey", "SCT")

REGION_FILES = tuple(code + ".txt" for code in TARGET_REGIONS)
GLOBAL_FILE = "global_top25.txt"


class SafetyError(RuntimeError):
    """单文件内容校验失败或原子替换被拒绝。"""


def node_count(content: str) -> int:
    return 0 if not content else len(content.splitlines())


def validate_txt(content: str, *, filename: str, expected_lines: list,
                 settings: dict, names: dict, max_lines: int) -> dict:
    """校验单个 TXT 的格式、行数、IP、备注与排名顺序。

    expected_lines 是由 output.render_board 生成并已排好序的行列表；
    逐字节比对可同时验证格式正确性与排名未被篡改。
    """
    if not isinstance(content, str):
        raise SafetyError("%s 内容不是字符串" % filename)
    if expected_lines is None:
        raise SafetyError("%s 缺少渲染基准，拒绝校验" % filename)
    expected = "\n".join(expected_lines) + ("\n" if expected_lines else "")
    if content != expected:
        raise SafetyError("%s 内容与按排名渲染的结果不一致（格式/行数/顺序校验失败）" % filename)

    lines = content.splitlines()
    if len(lines) > max_lines:
        raise SafetyError("%s 行数 %d 超过上限 %d" % (filename, len(lines), max_lines))
    if any(not line.strip() for line in lines):
        raise SafetyError("%s 含空行" % filename)
    if any(marker in content for marker in _SECRET_MARKERS):
        raise SafetyError("%s 疑似包含凭据内容" % filename)

    allowed_codes = set(TARGET_REGIONS) | {UNKNOWN}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("<") or stripped.startswith("{"):
            raise SafetyError("%s 含代码围栏/HTML/JSON 外壳" % filename)
        match = _LINE_RE.match(stripped)
        if not match:
            raise SafetyError("%s 含非法行: %r" % (filename, stripped[:100]))
        ip_part, port_text, code, english, colo, latency = match.groups()
        try:
            ipaddress.ip_address(ip_part.strip("[]"))
        except ValueError as exc:
            raise SafetyError("%s 含非法 IP: %s" % (filename, ip_part)) from exc
        if int(port_text) != settings["port"]:
            raise SafetyError("%s 端口不是 %d" % (filename, settings["port"]))
        if code not in allowed_codes:
            raise SafetyError("%s 地区代码非法: %s" % (filename, code))
        if filename in REGION_FILES:
            want = filename[:-4]
            if code != want:
                raise SafetyError("%s 出现非本地区/UNKNOWN 节点: %s" % (filename, code))
        if names.get(code) != english:
            raise SafetyError("%s 英文地区名不匹配: %s" % (filename, english))
        if not colo or int(latency) < 0:
            raise SafetyError("%s Colo 或延迟非法" % filename)
    return {"ok": True, "lines": len(lines), "filename": filename}


def publish_one(target, content: str, validator, *, replace_fn=None) -> dict:
    """单文件原子更新：同目录临时文件 -> 写完整内容 -> fsync -> 回读校验 ->
    validator 校验 -> os.replace()。任何异常都删除临时文件并保留旧正式文件。

    replace_fn 仅供离线测试注入监视器，生产路径恒为 os.replace。
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    do_replace = replace_fn or os.replace
    fd, tmp = tempfile.mkstemp(prefix=".tmp-%s-" % target.name,
                               suffix=".part", dir=str(target.parent))
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        # 回读确认落盘内容完整
        if tmp_path.read_text(encoding="utf-8") != content:
            raise SafetyError("%s 临时文件回读不一致" % target.name)
        validator(content)
        do_replace(str(tmp_path), str(target))
        return {
            "status": "updated",
            "node_count": node_count(content),
            "reason": None,
            "temp_file": tmp_path.name,
            "atomic_replace": True,
        }
    except Exception as exc:  # 单文件失败不得向外抛，由调用方隔离
        try:
            tmp_path.unlink()
        except OSError:
            pass
        return {
            "status": "failed",
            "node_count": None,
            "reason": "%s: %s" % (type(exc).__name__, exc),
            "temp_file": tmp_path.name,
            "atomic_replace": False,
        }


def leftover_temp_files(directory) -> list:
    p = Path(directory)
    return sorted(x.name for x in p.glob(".tmp-*.part")) if p.is_dir() else []
```


## app/config.py  (215 行, sha256=63eacb034085b573196ee9ebb62944c871a070561449ddfa8aa3e77f8764df94)

```python
"""配置加载与校验。仅使用 Python 标准库。

所有路径基于本文件位置用 pathlib 解析，不依赖当前工作目录；
适配容器内以 UID 1000 / GID 0 运行。不读取、不打印任何 Token、密码或环境变量。

新任务书要点：
  * 单轮测速：settings.json 中不得再出现 httping_url / httping_count / max_merged；
  * 六个 TXT 固定，禁止 merged.txt / global_top15.txt；
  * 地区映射独立维护在 regions.json，未确认 Colo 一律 UNKNOWN；
  * 六个文件独立校验、独立原子更新，不做整体事务。
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
EXPECTED_RESULT_FILES = (
    "HK.txt", "JP.txt", "SG.txt", "KR.txt", "US.txt", "global_top25.txt",
)
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
```


## config/settings.json  (28 行, sha256=bc0f5af89e0399604b8f88ace6b98dd784b9ca12c2ea3f615528692b94bbca18)

```json
{
  "schema_version": 2,
  "run_mode": "single_pass",
  "download_url": "https://speed.cloudflare.com/__down?bytes=10000000",
  "port": 443,
  "cfst_binary": "bin/cfst_linux_amd64/cfst",
  "ip_file": "bin/cfst_linux_amd64/ip.txt",
  "concurrency": 20,
  "latency_count": 4,
  "download_count": 5,
  "download_duration": 10,
  "cfst_timeout_sec": 1800,
  "region_top_n": 5,
  "global_top_n": 25,
  "speed_unit": "MB/s",
  "timezone": "Asia/Shanghai",
  "loss_unit": "ratio",
  "csv_path": "data/result.csv",
  "output_dir": "data",
  "log_dir": "logs",
  "result_files": ["HK.txt", "JP.txt", "SG.txt", "KR.txt", "US.txt", "global_top25.txt"],
  "notes": [
    "单轮测速：一次 CFST 普通 TCPing + 下载测速，只产生一份 CSV；禁止 -httping / -httping-code / -dd / -cfcolo。",
    "download_count 对应 CFST -dn（进入下载测速的候选数量）。当前沿用任务书初始值 5；-dn=5 与 global_top25 取 25 条存在数量矛盾，须在阶段 4.3/4.4 由用户与 ChatGPT 确认，代码不擅自改值。",
    "loss_unit=ratio 依据 CFST v2.3.5 -h 中 -tlr 的 0.00~1.00 范围；正式单位仍需阶段 4.4 真实 CSV 复核。",
    "地区码 Colo 是 Anycast 落点，不是 IP 地理归属；同一 IP 在不同网络/时间可能落到不同节点。"
  ]
}
```


## config/regions.json  (42 行, sha256=998745250d900520000599da43b3c1f4ef59e92a077984295079b771e8d7f83a)

```json
{
  "schema_version": 2,
  "evidence_source": "阶段 4.0 审计：samples/ 下 6 份历史 CSV 中实际出现的 Colo；阶段 2 普通下载模式 CSV 已出现 SIN/LAX/N/A 与真实速度",
  "regions": {
    "HK": [],
    "JP": [],
    "SG": ["SIN"],
    "KR": [],
    "US": ["LAX"]
  },
  "region_names": {
    "HK": "HongKong",
    "JP": "Japan",
    "SG": "Singapore",
    "KR": "SouthKorea",
    "US": "UnitedStates",
    "UNKNOWN": "Unknown"
  },
  "confirmed": {
    "SIN": "多次测试成功，SG 候选",
    "LAX": "多次测试成功，US 候选；不代表完整 US Colo 列表"
  },
  "pending": {
    "DEN": "仅一次测试成功，待核实；暂不纳入任何目标地区"
  },
  "excluded": {
    "AMS": "一次测试成功，暂不纳入目标地区",
    "N/A": "CFST 未返回地区码，未知，排除地区归类"
  },
  "no_samples": ["HK", "JP", "KR"],
  "incomplete_regions": {
    "US": "当前仅 LAX 有历史证据；US Colo 列表不完整，须由后续真实样本补充并经用户确认"
  },
  "unknown_policy": "未出现在 regions 已确认映射中的 Colo（含 N/A、空值、DEN、AMS 及任何新代码）一律归类为 UNKNOWN，不进入任何地区榜，但允许进入 global_top25.txt 并使用 UNKNOWN-Unknown-<Colo>-<ms>ms 备注；不得自动猜测国家或地区",
  "notes": [
    "Colo 是本轮 CFST CSV 的地区码（Cloudflare Anycast 落点机场码），不是 IP 地理归属；同一 IP 在不同网络或不同时间可能落到不同节点。",
    "HK、JP、KR 目前没有真实测试样本，保持空列表；禁止拿其他地区 IP 凑数，成功测速但无有效节点时应输出空文件。",
    "DEN 保持待确认、AMS 保持排除；以后发现新 Colo 必须先记录真实测试结果、经用户确认后才能加入 regions。",
    "五个地区固定存在，每个地区可含多个已确认 Colo；一个 Colo 只能属于一个地区；confirmed / pending / excluded 不得互相冲突。",
    "地区归属只依据本轮同一份 CSV 的地区码，不再有两轮映射。"
  ]
}
```
