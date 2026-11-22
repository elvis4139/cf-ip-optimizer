# 阶段 4.1-R1 修改后关键源码审查材料（只读导出）

- 导出时间：2026-11-22 17:0x Asia/Shanghai
- 来源：NAS `/share/Container/cf-ip-optimizer/` 已部署文件；下列内容逐字取自本地同哈希副本
- NAS 与本地副本 SHA256 逐个一致；本轮共修改 10 个文件，未新增、未删除文件
- 代码块使用四反引号围栏，避免源码内的三反引号字符串影响渲染

## 0 修改前后 SHA256 对照

| 文件 | 大小 | 修改前 | 修改后 |
|---|---:|---|---|
| `app/__init__.py` | 680 B | `0020f2e4244da3c2ccfd3dceaf3617c61018d1996908186f00a7526c832b9360` | `9f735c5f0e5697e800dea872cf3443168bbd1cdb64bc1b7d9fb2be0023164c17` |
| `app/main.py` | 51969 B | `69571d43bf196b7def099bf083f4de23690c216a4724981bc8d5e35124b1c3f5` | `821ec0224a056f69d0a2fb5b7685960effe228ddf906a0653163b3a1f7dc443a` |
| `app/config.py` | 9473 B | `63eacb034085b573196ee9ebb62944c871a070561449ddfa8aa3e77f8764df94` | `6a0db6b78c820548c5117214157dedea124d39ce5c6bae5a9aca0d1a21ffada2` |
| `app/cfst.py` | 13218 B | `d3f7325d64d8490dbc5ad439bfd1ed3710d359c66daafe438e0e9570b4aced94` | `76661d0d3cf4ace82db70e12dd8d209b5c173834e003fdc65940406a3a758484` |
| `app/ranking.py` | 4208 B | `0d80743f2dacc0fe7f18615d772b2f086b578853773ead173e7503ede2529e57` | `8be5c3ef412634f5f42633c48821f02e21b61124665c72ac04ab09ec0df7552f` |
| `app/output.py` | 3398 B | `8a87302d4c3cc77132d87d36ef32347cc65ef53c403215f42d7b8fee5ab615ca` | `ed3e303c16949fa418fa27fd9c49fa7416d58e75af1dd78922245c6025130896` |
| `app/safety.py` | 7248 B | `e231cdbefe5cba3d6b260b5bda6831e5407664ed525f945aa006768c53cc1aab` | `24a358b3a1754d9485621629c2825235a5de9f6c787ed7bf73b66723dc8f11e6` |
| `app/pipeline.py` | 10171 B | `cfd4e221ee3928b89267699d3444c74d4f1a44d37f1ab5143a7ceaf975c8d2b7` | `cf97abde9fd1ca1f3742d82c4b3fada1cb43c4b750ce207a3dbb374bf30ca5ae` |
| `config/settings.json` | 2409 B | `bc0f5af89e0399604b8f88ace6b98dd784b9ca12c2ea3f615528692b94bbca18` | `750b9fedde2b1f4519f996007286b951482deaa54eb90d5a5ec64d3c5f0a00e0` |
| `docs/TASK_BOOK.md` | 26986 B | `afd4fb3348cc62a50501df6e89f4c74c278c686e05d89e773b8e369e0a77f27e` | `ff68dc4d94916998e9741da95dc826575b16187e4ad4a486aa209ead5c719b46` |

未修改文件（SHA256 前后一致）：

```
app/region.py                            4ddb1f8c03e9a29ff8c3ac361e6921d64dc794905b21ca1f24f16db5465b78b1
config/regions.json                      998745250d900520000599da43b3c1f4ef59e92a077984295079b771e8d7f83a
Dockerfile                               2df92118e23aeb94252527cf37a892de229fd65aa822be331871fbc6cb234b42
compose.yaml                             e1b8a795073d189b07aa75e438c65299788591e74be6e7c855e5a2290a0f20b1
.dockerignore                            75750ad633da57a4225051d8bec39322db408b2edf494b9053b8a91c519f4792
bin/cfst_linux_amd64.tar.gz              c4c8fc76b4e1bf2bdb5ced8b765956d82dda7bc4eb59df5c04053f0f7db98d90
```

## 1 修正摘要

**必须修正**：(1) `download_count` 5→100，notes 删除过时说明并明确 `-dn` 是下载测速候选数；
(2) `parse_loss` 严格按显式单位，删除 `value > 1.0` 数值猜测，无效值整条排除不静默置 0；
(3) 本轮 CSV 一次性独立路径 + 新鲜度 + 完整性三重校验，成功后才归档，失败不丢历史；
(4) 六榜在发布循环内逐榜独立选取/渲染/校验/原子替换，循环前无集体渲染。

**建议修正**：(5) 严格 IPv4（ranking / output / safety）；(6) 表头解析与完整性共用别名语义字段；
(7) 核查并文档化 mkstemp 最终 0o600 权限，未放宽，读取权限留待 4.2。

**测试**：T18 改写，新增 R01~R18 共 18 项；`--simulate` 5→9 个场景。

## 2 修改后关键源码全文


### app/cfst.py  — 329 行，sha256=76661d0d3cf4ace82db70e12dd8d209b5c173834e003fdc65940406a3a758484

````python
"""单轮 CFST 命令构造、CSV 解析与本轮 CSV 新鲜度判定（阶段 4.1-R1）。

依据 NAS 上 CFST v2.3.5 的 -h 与 samples/ 6 份历史 CSV 实证：
  * CSV 标准表头: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
  * 普通 TCPing + 下载模式（不加 -httping / -dd）确实同时输出速度、延迟、
    丢包率与地区码：samples/phase2-download-3ip.csv 与
    samples/phase2-download-cloudflare-108.csv 中可见 SIN/LAX 与 15.84/15.22 MB/s。
    -> 这是「单轮成立」的离线证据；完整真实 CSV 仍须阶段 4.4 验证。
  * -cfcolo 仅 HTTPing 模式可用；-dd 禁用下载测速；-tlr 说明丢包率范围 0.00~1.00。
  * 下载速度单位是 MB/s，不是 Mbps。

架构铁律：本模块只提供 build_command() 一个命令构造函数，
一次运行只产生一条命令、一份 CSV；不存在第一轮/第二轮命令构造器。
execute_cfst() 在阶段 4.1 是拒绝执行的占位，保证本阶段无法触发真实测速。

4.1-R1 修正：
  * parse_loss 严格按显式单位解析，不再按数值大小猜测百分数；
  * 表头解析与完整性校验统一使用 HEADER_ALIASES / REQUIRED_SEMANTIC_FIELDS；
  * 新增 new_run_csv_path / prepare_run_csv / csv_is_fresh：
    生产运行 -o 指向本轮一次性独立路径，杜绝误读上一轮遗留的 data/result.csv。
"""

from __future__ import annotations

import csv
import io
import math
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import PROJECT_ROOT, asset_paths

CSV_HEADER = "IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码"

# 按字段名解析，绝不依赖固定列序号。
# 完整性与解析共用这一套语义字段，避免「解析成功但固定中文表头检查又失败」。
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
REQUIRED_SEMANTIC_FIELDS = frozenset(HEADER_ALIASES)

FORBIDDEN_FLAGS = ("-httping", "-httping-code", "-dd", "-cfcolo")
NA_TEXTS = {"", "N/A", "NA", "NULL", "NONE", "-", "--", "UNKNOWN"}

RUN_CSV_PREFIX = ".cfst-run-"
# 时间戳容差：容忍文件系统时间戳粒度与「测试预置 fixture」的毫秒级时间差，
# 同时能拒绝明显属于上一轮的陈旧文件。
FRESHNESS_TOLERANCE_NS = 2_000_000_000


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
    resolved_fields: dict = field(default_factory=dict)  # 语义字段 -> 实际表头名

    @property
    def total_rows(self) -> int:
        return len(self.rows) + len(self.malformed_rows)


def build_command(settings: dict, csv_out=None) -> list:
    """构造唯一一条完整 CFST 测速命令（参数列表，供 subprocess 使用）。

    不拼接 shell 字符串；不含 -httping / -httping-code / -dd / -cfcolo。
    csv_out 为 None 时 -o 指向配置中的正式 CSV（仅供 --check-config 展示）；
    生产运行由 pipeline.run_once 显式传入本轮一次性路径。
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
    if "-dn" not in tokens or tokens[tokens.index("-dn") + 1] != str(settings["download_count"]):
        problems.append("-dn 与 download_count 配置不一致")
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


# --------------------------------------------------------------------------
# 本轮 CSV 新鲜度（4.1-R1 新增）
# --------------------------------------------------------------------------
def new_run_csv_path(formal_csv, run_id=None) -> Path:
    """在正式 CSV 同目录生成【本轮一次性】路径，与 data/result.csv 不重名。

    同目录保证后续 os.replace() 是同文件系统原子操作。
    """
    formal = Path(formal_csv)
    rid = run_id or "%s-%d-%s" % (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"),
        os.getpid(), uuid.uuid4().hex[:8],
    )
    return formal.parent / ("%s%s.csv" % (RUN_CSV_PREFIX, rid))


def prepare_run_csv(path) -> bool:
    """运行前清理本轮一次性路径（正常情况不存在；返回是否确实删除了文件）。

    只操作本轮路径，绝不触碰正式 data/result.csv 或六个正式 TXT。
    """
    p = Path(path)
    try:
        p.unlink()
        return True
    except (FileNotFoundError, OSError):
        return False


def csv_is_fresh(path, started_ns: int):
    """判断本轮 CSV 是否确为本次运行写出，返回 (bool, 原因)。

    仅凭 CFST 退出码 0 不足以证明写出了新 CSV：必须同时满足
      * 本轮独立路径上的文件存在；
      * 文件非空；
      * mtime 不早于本轮开始时间（含 2 秒容差）。
    这样上一轮遗留的 data/result.csv 永远不会被当作本轮结果。
    """
    p = Path(path)
    if not p.is_file():
        return False, "本轮 CSV 未生成"
    st = p.stat()
    if st.st_size == 0:
        return False, "本轮 CSV 为空文件"
    if st.st_mtime_ns + FRESHNESS_TOLERANCE_NS < started_ns:
        return False, "本轮 CSV 时间戳早于本轮开始（疑似上一轮遗留）"
    return True, "新鲜"


# --------------------------------------------------------------------------
# 数值解析
# --------------------------------------------------------------------------
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
    """把丢包率归一化为 0.00~1.00 的比率（严格按显式单位，不做数值猜测）。

    4.1-R1 规则（依据 ChatGPT 只读审查修正）：

    * unit="ratio"（生产配置强制）：只接受 0~1 的【无百分号】数值。
        '0'->0.0  '0.25'->0.25  '1'->1.0
        '1.2' / '25' / '100' -> None（>1 一律拒绝，绝不猜测为百分数）
    * unit="percent"：明确按百分数处理，数值除以 100。
        '25'->0.25  '0'->0.0  '1'->0.01  '200'->None（结果 >1）
    * 显式带 '%' 的数值按百分数转换，且只除一次（任何 unit 下都一样）：
        '25%'->0.25  '0%'->0.0  '150%'->None
    * 负数、N/A、NaN、Infinity、非法文本、归一化后 >1 一律返回 None。

    调用方（ranking.make_candidate）在返回 None 时整条记录排除，
    绝不会把格式不符的记录静默当作 0 丢包。
    真实 CSV 的单位仍须在阶段 4.4 复核。
    """
    s = str(text).strip() if text is not None else ""
    percent_sign = s.endswith("%")
    if percent_sign:
        s = s[:-1].strip()
    value = finite_float(s)
    if value is None or value < 0:
        return None
    if percent_sign or unit == "percent":
        value = value / 100.0
    elif unit != "ratio":
        return None  # 未知单位，拒绝而非猜测
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
    """按表头名解析 CFST CSV 文本，兼容 UTF-8 BOM、GBK 与中英文表头。

    解析成功后 resolved_fields 记录每个语义字段实际匹配到的表头名，
    供 validate_csv_completeness 用同一套别名逻辑复核。
    """
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return CsvData()

    header = [cell.strip() for cell in rows[0]]
    index = {}
    resolved = {}
    for key, aliases in HEADER_ALIASES.items():
        position = next((header.index(a) for a in aliases if a in header), None)
        if position is None:
            raise CsvError("CSV 缺少字段 %s；实际表头: %s" % (key, header))
        index[key] = position
        resolved[key] = header[position]

    data = CsvData(header=header, resolved_fields=resolved)
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
    """判断一次完整测速的 CSV 是否可信。返回 (bool, 原因, CsvData|None)。

    4.1-R1：表头校验改用与 parse_csv_text 相同的 REQUIRED_SEMANTIC_FIELDS，
    不再要求固定中文表头字符串，避免中英文表头解析成功却又被判定不完整。
    """
    p = Path(path)
    if not p.is_file():
        return False, "CSV 文件不存在", None
    if p.stat().st_size == 0:
        return False, "CSV 为空文件", None
    try:
        data = parse_csv_file(p)
    except CsvError as exc:
        return False, str(exc), None
    missing = sorted(REQUIRED_SEMANTIC_FIELDS - set(data.resolved_fields))
    if missing:
        return False, "CSV 缺少语义字段: %s" % ", ".join(missing), data
    if data.malformed_rows:
        return False, "CSV 有 %d 行截断/列数不足" % len(data.malformed_rows), data
    if not data.rows:
        return False, "CSV 无数据行", data
    return True, "完整", data
````


### app/pipeline.py  — 234 行，sha256=cf97abde9fd1ca1f3742d82c4b3fada1cb43c4b750ce207a3dbb374bf30ca5ae

````python
"""一次完整 CFST 测速 -> 一份本轮 CSV -> 六个独立 TXT 的编排（4.1-R1）。

本阶段（4.1）只在临时目录里用「模拟 runner」离线运行，runner 默认指向
cfst.execute_cfst()，而后者在 4.1 直接拒绝，因此不存在触发真实测速的路径。

关键隔离语义：
  * runner 失败 / 退出码非 0 / 本轮 CSV 未生成、不新鲜或不完整
        -> 六个文件全部 skipped，旧文件与历史 CSV 一个都不动；
  * 测速成功后，六个文件【逐榜】独立选取、独立渲染、独立校验、独立原子替换，
    单个榜单的渲染失败、校验失败或写入失败都不影响其他五个；
  * 测速成功但某地区无有效节点 -> 该文件更新为空文件（情况 A）；
  * 情况 B（生成/写入/校验异常）-> 只保留该文件上次成功版本。

4.1-R1 关键修正（ChatGPT 只读审查）：

1) CSV 本轮新鲜度
   - CFST 的 -o 不再指向正式 data/result.csv，而是指向同目录下
     【本轮一次性路径】 .cfst-run-<run_id>.csv；
   - 运行前清理该一次性路径；运行后要求文件存在、非空、mtime 不早于本轮开始，
     并通过完整性校验，才允许发布六个 TXT；
   - 只有上述全部通过后，才把本轮 CSV 原子归档为 data/result.csv；
   - 本轮任何失败都只删除本轮临时 CSV，历史 data/result.csv 与六个旧 TXT 不变。

2) 六文件生成隔离
   - 发布循环前不再做「一次集体渲染」（旧版 render_all_boards / select_boards）；
   - 每个榜单在独立 try 内依次调用 ranking.select_board -> output.render_board
     -> safety.validate_txt -> safety.publish_one；
   - 最快节点计算单独 try，异常只记 warning，不阻断发布。

测试注入参数（仅离线测试使用，生产路径一律为默认值）：
    csv_path            本轮 CSV 路径覆盖；None 表示自动生成一次性路径
    formal_csv_path     历史正式 CSV 路径覆盖（默认 data/result.csv）
    render_overrides    {文件名: 异常实例或 callable} 注入单榜渲染失败
    validator_overrides {文件名: callable} 注入单榜校验失败
    replace_overrides   {文件名: 异常实例} 注入单榜写入失败
    replace_fn          os.replace 监视器
    archive_csv         是否归档本轮 CSV；None 表示仅自动路径才归档
    run_id              固定本轮 id，便于离线测试可复现
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import cfst, output, ranking, safety
from .config import (
    EXPECTED_RESULT_FILES, GLOBAL_FILE, asset_paths, colo_map, region_names,
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


def _failed(reason: str) -> dict:
    return {
        "status": "failed", "node_count": None, "reason": reason,
        "atomic_replace": False,
    }


def run_once(settings: dict, regions: dict, *, runner=None, csv_path=None,
             formal_csv_path=None, output_dir=None,
             validator_overrides=None, render_overrides=None,
             replace_overrides=None, replace_fn=None,
             archive_csv=None, run_id=None, now_iso=None) -> dict:
    """执行一次完整流程；返回运行状态字典（不打印任何敏感信息）。"""
    names = region_names(regions)
    cmap = colo_map(regions)
    paths = asset_paths(settings)

    formal = (Path(formal_csv_path) if formal_csv_path is not None
              else paths["csv_path"])
    auto_csv = csv_path is None
    run_csv = (cfst.new_run_csv_path(formal, run_id=run_id) if auto_csv
               else Path(csv_path))
    should_archive = auto_csv if archive_csv is None else bool(archive_csv)
    out_dir = Path(output_dir) if output_dir is not None else paths["output_dir"]
    validator_overrides = validator_overrides or {}
    render_overrides = render_overrides or {}
    replace_overrides = replace_overrides or {}
    run = runner or _default_runner

    status = {
        "run_time": now_iso or datetime.now(CST).isoformat(timespec="seconds"),
        "timezone": settings["timezone"],
        "run_mode": settings["run_mode"],
        "cfst_command": cfst.build_command(settings, run_csv),
        "run_csv_path": str(run_csv),
        "formal_csv_path": str(formal),
        "cfst_exit_code": None,
        "csv_fresh": False,
        "csv_complete": False,
        "csv_archived": False,
        "csv_total_rows": 0,
        "valid_ip_count": 0,
        "files": {},
        "failed_files": [],
        "skipped_files": [],
        "fastest_node": None,
        "measurement_success": False,
        "all_files_updated": False,
        "speed_unit": settings["speed_unit"],
        "warnings": [],
    }

    def _cleanup_run_csv():
        """只删除本轮一次性 CSV；绝不触碰历史 data/result.csv 或六个正式 TXT。"""
        if auto_csv:
            try:
                Path(run_csv).unlink()
            except (FileNotFoundError, OSError):
                pass

    def _abort(reason: str) -> dict:
        _cleanup_run_csv()
        status["files"] = {name: _skipped(reason) for name in EXPECTED_RESULT_FILES}
        status["skipped_files"] = list(EXPECTED_RESULT_FILES)
        status["failure_reason"] = reason
        return status

    # --- 阶段 A：一次完整测速；任何失败都六个文件全部不更新 ---
    if auto_csv:
        cfst.prepare_run_csv(run_csv)
    started_ns = time.time_ns()
    try:
        exit_code = run(status["cfst_command"], run_csv, settings["cfst_timeout_sec"])
    except Exception as exc:
        return _abort("CFST 执行异常（%s）: %s" % (type(exc).__name__, exc))
    status["cfst_exit_code"] = exit_code
    if exit_code != 0:
        return _abort("CFST 退出码非 0 (%s)，完整测速失败" % exit_code)

    fresh, fresh_reason = cfst.csv_is_fresh(run_csv, started_ns)
    status["csv_fresh"] = fresh
    if not fresh:
        return _abort("本轮 CSV 新鲜度校验失败: %s" % fresh_reason)

    complete, reason, csv_data = cfst.validate_csv_completeness(run_csv)
    status["csv_complete"] = complete
    if not complete:
        return _abort("CSV 不完整: %s" % reason)

    status["csv_total_rows"] = csv_data.total_rows
    status["measurement_success"] = True

    # --- 阶段 B：同一份 CSV 解析、一次排序（纯计算，不渲染）---
    try:
        candidates = [
            c for c in (
                ranking.make_candidate(row, cmap, settings["loss_unit"])
                for row in csv_data.rows
            ) if c is not None
        ]
        status["valid_ip_count"] = len(candidates)
        ranked = ranking.sort_candidates(candidates)
    except Exception as exc:
        return _abort("CSV 解析/排序异常（%s）: %s" % (type(exc).__name__, exc))

    # 最快节点只是审计信息，单独 try，异常绝不阻断六个榜单发布
    try:
        global_board = ranking.select_board(GLOBAL_FILE, ranked, settings)
        status["fastest_node"] = output.fastest_node_of(
            {GLOBAL_FILE: global_board}, settings, names)
    except Exception as exc:
        status["warnings"].append("最快节点计算失败（不影响发布）: %s" % exc)

    def _make_replace(name):
        """把单榜写入故障注入包装进 os.replace 监视器。"""
        def _do(src, dst):
            injected = replace_overrides.get(name)
            if injected is not None:
                raise injected if isinstance(injected, BaseException) else OSError(str(injected))
            base = replace_fn or os.replace
            return base(src, dst)
        return _do

    # --- 阶段 C：每个榜单独立选取 -> 独立渲染 -> 独立校验 -> 独立原子替换 ---
    for name in EXPECTED_RESULT_FILES:
        try:
            items = ranking.select_board(name, ranked, settings)
            hook = render_overrides.get(name)
            if isinstance(hook, BaseException):
                raise hook
            content = (hook(items, settings, names) if callable(hook)
                       else output.render_board(items, settings, names))
            expected_lines = content.splitlines()
            override = validator_overrides.get(name)
            default_validator = lambda text, _n=name, _e=expected_lines: safety.validate_txt(
                text, filename=_n, expected_lines=_e, settings=settings,
                names=names,
                max_lines=(settings["global_top_n"] if _n == GLOBAL_FILE
                           else settings["region_top_n"]),
            )
            validator = override or default_validator
            result = safety.publish_one(out_dir / name, content, validator,
                                        replace_fn=_make_replace(name))
        except Exception as exc:
            result = _failed("生成/渲染/发布异常（%s）: %s" % (type(exc).__name__, exc))
        status["files"][name] = result
        if result["status"] == "failed":
            status["failed_files"].append(name)
        elif result["status"] == "skipped":
            status["skipped_files"].append(name)

    status["all_files_updated"] = (
        all(status["files"][n]["status"] == "updated" for n in EXPECTED_RESULT_FILES)
    )

    # --- 阶段 D：本轮 CSV 归档（只有完整性通过的 CSV 才会替换历史 result.csv）---
    if should_archive:
        try:
            formal.parent.mkdir(parents=True, exist_ok=True)
            os.replace(str(run_csv), str(formal))
            status["csv_archived"] = True
        except Exception as exc:
            status["warnings"].append("本轮 CSV 归档失败（不影响六个 TXT）: %s" % exc)
            _cleanup_run_csv()
    else:
        _cleanup_run_csv()
    return status
````


### app/ranking.py  — 116 行，sha256=8be5c3ef412634f5f42633c48821f02e21b61124665c72ac04ab09ec0df7552f

````python
"""六榜排名（同一份 CSV，一次排序，多榜取用）。

排序规则（六个榜单完全一致）：
  1. 下载速度 MB/s 降序
  2. 平均延迟 ms 升序
  3. 丢包率（0~1 比率）升序
  4. 全部相同时以 IP 地址作为最后的稳定排序条件

有效记录：IPv4 合法、速度 > 0、延迟与丢包率为有限非负数、无 NaN/Infinity/负数、
N/A 速度不算有效成绩。未知 Colo 可以进入全球榜，但不得进入任何地区榜。
不做跨文件去重，也不做合并；地区榜不足 5 条就输出实际条数，不拿别地区 IP 凑数。

4.1-R1 修正：
  * is_valid_ip() 只接受 IPv4，IPv6 暂不纳入当前六个榜单；
  * 新增 select_board() 单榜选取，供 pipeline 在发布循环内逐榜独立调用；
    select_boards() 保留为离线对照/测试用的薄封装，生产发布路径不再使用它。
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from .cfst import finite_float, parse_loss
from .config import GLOBAL_FILE, TARGET_REGIONS, UNKNOWN
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
    """当前阶段严格限定 IPv4；IPv6 一律拒绝。"""
    try:
        return ipaddress.ip_address(str(value).strip()).version == 4
    except (ValueError, TypeError):
        return False


def _ip_sort_key(value: str):
    try:
        addr = ipaddress.ip_address(value)
        return (int(addr),) if addr.version == 4 else (0,)
    except (ValueError, TypeError):
        return (0,)


def make_candidate(row, colo_map: dict, loss_unit: str = "ratio") -> Candidate | None:
    """把一条原始 CSV 行转为有效候选；任何字段不合格即返回 None。

    丢包率格式不符时 parse_loss 返回 None -> 整条记录排除，不静默当作 0 丢包。
    """
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


def select_board(name: str, ranked: list, settings: dict) -> list:
    """单榜选取（4.1-R1）：只处理一个榜单，异常由 pipeline 逐榜隔离。

    地区榜：只取 region 等于本地区且已确认 Colo 的候选，Top region_top_n。
    全球榜：取全部有效候选 Top global_top_n，允许 UNKNOWN，不与地区榜去重。
    任一榜单不足上限时返回实际条数，不补造、不拿其他地区凑数。
    """
    if name == GLOBAL_FILE:
        return ranked[:settings["global_top_n"]]
    code = name[:-4] if name.endswith(".txt") else name
    if code not in TARGET_REGIONS:
        raise ValueError("未知榜单: %s" % name)
    return [c for c in ranked if c.region == code][:settings["region_top_n"]]


def select_boards(candidates, settings: dict) -> dict:
    """一次性生成六榜（仅供离线对照与测试；生产发布路径使用 select_board）。"""
    ranked = sort_candidates(candidates)
    return {
        code + ".txt": select_board(code + ".txt", ranked, settings)
        for code in TARGET_REGIONS
    } | {GLOBAL_FILE: select_board(GLOBAL_FILE, ranked, settings)}


def board_stats(boards: dict) -> dict:
    return {name: len(items) for name, items in boards.items()}
````


### app/region.py  — 64 行，sha256=4ddb1f8c03e9a29ff8c3ac361e6921d64dc794905b21ca1f24f16db5465b78b1  （本轮未修改）

````python
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
````


### app/safety.py  — 156 行，sha256=24a358b3a1754d9485621629c2825235a5de9f6c787ed7bf73b66723dc8f11e6

````python
"""六个 TXT 的独立校验与单文件原子更新。

铁律：
  * 每个文件独立生成、独立渲染、独立校验、独立 os.replace()，一个失败不影响其他五个；
  * 完整测速失败（退出码非 0、本轮 CSV 未生成/不新鲜/不完整）时，六个文件一律不更新；
  * 情况 A（测速成功但某地区无有效节点）-> 该文件更新为空文件；
  * 情况 B（生成/写入/校验异常）-> 删除临时文件，只保留该文件上次成功版本；
  * 不做六文件整体事务、不做 current symlink、不生成 merged.txt。

4.1-R1 修正：
  * 节点行与安全校验严格限定 IPv4（正则 + ipaddress.version 双重判定），IPv6 被拒绝；
  * REGION_FILES / GLOBAL_FILE 统一从 config 导入，与 ranking 共用同一名称来源。

权限说明（4.1-R1 按 ChatGPT 审查要求核查；本阶段不放宽，留待 4.2 实测）：
  * tempfile.mkstemp() 以 mode 0o600 创建临时文件；os.replace() 只改目录项，
    不改动文件模式，因此正式 TXT 最终权限同样是 0o600。
    代码中没有 os.chmod / umask 放宽，也【不应】擅自放宽。
  * 属主 = 创建文件的进程 euid / egid。容器内 compose.yaml 为 user: "1000:0"，
    因此预期最终文件 UID=1000 (HAKU)、GID=0 (administrators)；
    只读根文件系统下只有 data/ 与 logs/ 两个 bind mount 可写。
  * 0o600 意味着仅属主可读写，其他用户不可读。EdgeTunnel / GitHub / Web
    订阅服务能否读取，必须在阶段 4.2 用真实消费者验证；若届时确需放宽，
    须由用户明确授权后单独处理，本阶段一律不改。

阶段 4.1 只在临时目录里做离线模拟，不写 NAS 正式订阅文件。
"""

from __future__ import annotations

import ipaddress
import os
import re
import tempfile
from pathlib import Path

from .config import (
    EXPECTED_RESULT_FILES, GLOBAL_FILE, REGION_FILES, TARGET_REGIONS, UNKNOWN,
)

# IP:端口#地区-英文名-Colo-整数ms —— 当前阶段仅接受 IPv4 点分十进制
_LINE_RE = re.compile(
    r"^((?:\d{1,3}\.){3}\d{1,3}):(\d{1,5})#"
    r"([A-Z]{2}|UNKNOWN)-([A-Za-z]+)-([A-Z0-9]{2,10})-(\d+)ms$"
)
_SECRET_MARKERS = ("ghp_", "github_pat_", "Authorization:", "password=", "token=",
                   "SendKey", "SCT")


class SafetyError(RuntimeError):
    """单文件内容校验失败或原子替换被拒绝。"""


def node_count(content: str) -> int:
    return 0 if not content else len(content.splitlines())


def validate_txt(content: str, *, filename: str, expected_lines: list,
                 settings: dict, names: dict, max_lines: int) -> dict:
    """校验单个 TXT 的格式、行数、IPv4、备注与排名顺序。

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
            raise SafetyError("%s 含非法行（当前阶段仅接受 IPv4）: %r" % (filename, stripped[:100]))
        ip_part, port_text, code, english, colo, latency = match.groups()
        try:
            addr = ipaddress.ip_address(ip_part)
        except ValueError as exc:
            raise SafetyError("%s 含非法 IP: %s" % (filename, ip_part)) from exc
        if addr.version != 4:
            raise SafetyError("%s 含非 IPv4 地址: %s" % (filename, ip_part))
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
    """单文件原子更新：同目录临时文件(0o600) -> 写完整内容 -> fsync -> 回读校验 ->
    validator 校验 -> os.replace()。任何异常都删除临时文件并保留旧正式文件。

    replace_fn 仅供离线测试注入监视器或故障，生产路径恒为 os.replace。
    不调用 chmod：最终文件权限保持 mkstemp 的 0o600（见模块 docstring）。
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
````


### app/config.py  — 220 行，sha256=6a0db6b78c820548c5117214157dedea124d39ce5c6bae5a9aca0d1a21ffada2

````python
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
````


### app/output.py  — 88 行，sha256=ed3e303c16949fa418fa27fd9c49fa7416d58e75af1dd78922245c6025130896

````python
"""TXT 节点渲染与运行状态渲染（全部为纯函数，只返回字符串）。

节点行格式: IP:443#地区代码-英文地区名称-Colo-整数延迟ms
  已知地区: 172.64.150.190:443#SG-Singapore-SIN-92ms
  未知 Colo: 172.64.150.190:443#UNKNOWN-Unknown-DEN-92ms
  N/A 或空 Colo: 172.64.150.190:443#UNKNOWN-Unknown-NA-92ms
下载速度只参与排名，不写入备注；延迟四舍五入为整数毫秒（不使用银行家舍入）。
全球榜允许未知节点；地区榜不允许出现 UNKNOWN。
正式文件的写盘与原子替换由 safety.py 负责。

4.1-R1：当前阶段严格 IPv4，format_ip_port 遇到 IPv6 直接抛错；
render_all_boards 仅供离线对照/测试，生产发布路径由 pipeline 逐榜调用 render_board。
"""

from __future__ import annotations

import ipaddress
import json
import math

from .config import TARGET_REGIONS, UNKNOWN
from .region import colo_token


def format_latency_ms(value: float) -> int:
    """四舍五入为整数毫秒（0.5 进位，不用 Python round 的银行家舍入）。"""
    return int(math.floor(float(value) + 0.5))


def format_ip_port(ip: str, port: int = 443) -> str:
    """当前阶段仅接受 IPv4；IPv6 抛 ValueError，绝不隐式加括号进入六个榜单。"""
    address = ipaddress.ip_address(str(ip).strip())
    if address.version != 4:
        raise ValueError("阶段 4.1 仅支持 IPv4，拒绝 %s" % ip)
    return "%s:%d" % (address.compressed, port)


def render_node(candidate, settings: dict, names: dict) -> str:
    if settings["speed_unit"] != "MB/s":
        raise ValueError("速度单位必须为 MB/s")
    if candidate.region == UNKNOWN:
        code, english = UNKNOWN, names[UNKNOWN]
    else:
        code, english = candidate.region, names[candidate.region]
    token = colo_token(candidate.colo)
    return "%s#%s-%s-%s-%dms" % (
        format_ip_port(candidate.ip, settings["port"]),
        code, english, token, format_latency_ms(candidate.latency),
    )


def render_board(candidates, settings: dict, names: dict) -> str:
    """空榜返回空字符串（空文件）；非空时每行以 LF 结尾。"""
    lines = [render_node(c, settings, names) for c in candidates]
    return "\n".join(lines) + ("\n" if lines else "")


def render_all_boards(boards: dict, settings: dict, names: dict) -> dict:
    """一次性渲染六榜（仅供离线对照 / 测试使用）。

    生产发布路径不使用本函数：pipeline.run_once 在逐榜循环内独立调用
    render_board，避免一次集体渲染异常导致六个文件全部发布中断。
    """
    return {
        name: render_board(items, settings, names)
        for name, items in boards.items()
    }


def render_run_status(info: dict) -> str:
    """运行状态 JSON。禁止写入 Token、密码、完整环境变量等敏感信息。"""
    return json.dumps(info, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def fastest_node_of(boards: dict, settings: dict, names: dict) -> dict | None:
    global_top = boards.get("global_top25.txt") or []
    if not global_top:
        return None
    best = global_top[0]
    return {
        "node": render_node(best, settings, names),
        "ip": best.ip,
        "region": best.region,
        "colo": best.colo,
        "latency_ms": best.latency,
        "speed_mb_s": best.speed,
        "loss": best.loss,
    }
````


### app/__init__.py  — 18 行，sha256=9f735c5f0e5697e800dea872cf3443168bbd1cdb64bc1b7d9fb2be0023164c17

````python
"""cf-ip-optimizer 自动测速程序（阶段 4.1 修订版：单轮测速 / 六榜独立发布）。

本阶段只做代码架构修订与离线测试：
不执行真实测速、不发网络请求、不启动容器、不创建 Cron、不上传 GitHub、
不修改 EdgeTunnel、不更新正式订阅文件。

已废弃的旧两轮逻辑（HTTPing 初筛 + 按地区分别下载）不得再出现：
任何模块都不得构造第二条 CFST 命令，也不得读取第二轮 Colo 做分类。
"""

from __future__ import annotations

__version__ = "4.1.2-r1"
__stage__ = "4.1-R1"

__all__ = [
    "config", "cfst", "region", "ranking", "output", "safety", "pipeline", "main",
]
````


### config/settings.json  — 31 行，sha256=750b9fedde2b1f4519f996007286b951482deaa54eb90d5a5ec64d3c5f0a00e0

````json
{
  "schema_version": 2,
  "run_mode": "single_pass",
  "download_url": "https://speed.cloudflare.com/__down?bytes=10000000",
  "port": 443,
  "cfst_binary": "bin/cfst_linux_amd64/cfst",
  "ip_file": "bin/cfst_linux_amd64/ip.txt",
  "concurrency": 20,
  "latency_count": 4,
  "download_count": 100,
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
    "download_count 对应 CFST -dn，含义是【进入下载测速阶段的候选 IP 数量】，不是本轮延迟测试/扫描发现的 IP 总数，也不是最终入榜数量。当前初始值为 100（可配置，config.py 允许 1~10000），目的是让全球 Top 25 与五个地区各 Top 5 有足够的有效下载记录。有效下载记录不足时按实际数量输出，不保证恰好 25 条或 5 条，也不拿其他地区 IP 凑数。",
    "100 是初始测试值而非最终定值：阶段 4.4 依据完整测速耗时、有效下载数量、地区覆盖率和 NAS 负载再调整；调整只需改本文件，不需要改代码。",
    "loss_unit=ratio 依据 CFST v2.3.5 -h 中 -tlr 的 0.00~1.00 范围。parse_loss 严格按显式单位解析：ratio 只接受 0~1 的无百分号数值，percent 明确除以 100，显式带 % 的数值按百分数转换；不得根据数值是否大于 1 自动猜测单位，格式不符的记录整条排除而非静默当作 0 丢包。真实 CSV 的单位仍须阶段 4.4 复核。",
    "本轮 CSV 使用与 data/result.csv 不同的一次性独立路径（.cfst-run-<run_id>.csv），CFST -o 指向它；只有本轮 CSV 确认新生成且完整性校验通过，才允许发布六个 TXT。成功后才把它原子归档为 data/result.csv；本轮失败时历史 CSV 与六个旧 TXT 均保持不变。",
    "地区码 Colo 是 Anycast 落点，不是 IP 地理归属；同一 IP 在不同网络/时间可能落到不同节点。",
    "当前阶段仅支持 IPv4：ranking 与安全校验都拒绝 IPv6，IPv6 不进入六个榜单。"
  ]
}
````


### config/regions.json  — 42 行，sha256=998745250d900520000599da43b3c1f4ef59e92a077984295079b771e8d7f83a  （本轮未修改）

````json
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
````


### app/main.py  — 1053 行，sha256=821ec0224a056f69d0a2fb5b7685960effe228ddf906a0653163b3a1f7dc443a

````python
"""主流程入口（阶段 4.1-R1）。

可用命令：
  --check-config   加载并校验两份配置，打印唯一一条 CFST 命令（只构造，不执行）
  --self-test      任务书 28 项必测 + 4.1-R1 新增 18 项修正测试 + 网络守卫，
                   零真实测速、零真实网络请求
  --simulate       在临时目录用模拟 CSV 演示六榜生成 / 单文件失败 / 完整测速失败 /
                   空榜 / 原子替换 / CSV 新鲜度 / 独立渲染 / 数量边界九个场景，
                   不写 NAS 正式订阅文件
  --version

--run 在阶段 4.1 明确拒绝（exit 2）；真实测速须等阶段 4.4 用户授权。
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

from . import __stage__, __version__, cfst, output, pipeline, ranking, safety
from .config import (
    APP_DIR, EXPECTED_RESULT_FILES, PROJECT_ROOT, REGIONS_PATH, SETTINGS_PATH,
    TARGET_REGIONS, UNKNOWN, asset_paths, colo_map, region_names, validate_all,
)
from .region import classify

CSV_HEADER = cfst.CSV_HEADER


# --------------------------------------------------------------------------
# 模拟数据（离线，无任何网络访问）
# --------------------------------------------------------------------------
def _fixture_csv_text() -> str:
    """36 条有效记录 + 10 条无效记录；含 SIN/LAX/DEN/AMS/N/A/XYZ 与异常数值。"""
    lines = [CSV_HEADER]
    # SG: 8 条 SIN，含速度相同(20.00)延迟不同的两条，用于验证次级排序
    sg = [(30, 92.35), (25, 100.11), (20, 40.00), (20, 50.00),
          (18, 60.00), (15, 70.00), (12, 80.00), (10, 90.00)]
    for i, (sp, lat) in enumerate(sg, start=1):
        lines.append("108.162.192.%d,2,2,0.00,%.2f,%.2f,SIN" % (i, lat, sp))
    # US: 8 条 LAX
    us = [28, 24, 22, 19, 17, 14, 11, 9]
    for i, sp in enumerate(us, start=1):
        lines.append("104.16.0.%d,2,2,0.00,%.2f,%.2f,LAX" % (i, 100 + i * 10, sp))
    # 未知 Colo: 20 条，速度 35..16，确保进入全球榜
    colos = ["DEN", "AMS", "N/A", "XYZ"]
    for i in range(1, 21):
        lines.append("172.66.0.%d,2,2,0.00,%.2f,%.2f,%s" %
                     (i, 50 + i, 36 - i, colos[(i - 1) % len(colos)]))
    # 10 条应被排除的无效记录
    lines += [
        "999.999.999.999,2,2,0.00,10.00,50.00,SIN",   # 非法 IP
        "108.162.193.1,2,2,0.00,10.00,0.00,SIN",     # 速度 0
        "108.162.193.2,2,2,0.00,10.00,N/A,SIN",      # N/A 速度
        "108.162.193.3,2,2,0.00,10.00,nan,SIN",      # NaN
        "108.162.193.4,2,2,0.00,10.00,Infinity,SIN", # Infinity
        "108.162.193.5,2,2,0.00,10.00,-5.00,SIN",    # 负速度
        "108.162.193.6,2,2,0.00,-3.00,8.00,SIN",     # 负延迟
        "108.162.193.7,2,2,-1.00,10.00,8.00,SIN",    # 负丢包率
        "108.162.193.8,2,2,0.00,nan,8.00,SIN",       # NaN 延迟
        "108.162.193.9,2,2,N/A,10.00,8.00,SIN",      # N/A 丢包率
    ]
    return "\n".join(lines) + "\n"


def _small_csv_text() -> str:
    """仅 2 条有效 IPv4 记录：用于地区榜不足 5、全球榜不足 25 的边界。"""
    return "\n".join([
        CSV_HEADER,
        "108.162.192.1,2,2,0.00,92.35,30.00,SIN",
        "104.16.0.1,2,2,0.00,110.00,28.00,LAX",
    ]) + "\n"


def _empty_board_csv_text() -> str:
    """CSV 结构完整但零有效候选（一行全无效记录），用于六榜全空。"""
    return CSV_HEADER + "\n999.999.999.999,2,2,0.00,10.00,0.00,SIN\n"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_fixture(csv_path: Path) -> None:
    _write_text(csv_path, _fixture_csv_text())


def _runner_ok(command, csv_path, timeout_sec):
    """模拟 CFST 成功：CSV 已由测试预置好，返回退出码 0；绝不发起网络请求。"""
    return 0


def _runner_writes(text: str):
    """构造一个真正把本轮 CSV 写到 -o 目标路径的模拟 runner。"""
    def _run(command, csv_path, timeout_sec):
        _write_text(Path(csv_path), text)
        return 0
    return _run


def _prep_run_dir(base: Path, tag: str) -> Path:
    """准备含六个旧 TXT 的输出目录。"""
    out = base / tag
    out.mkdir(parents=True, exist_ok=True)
    for name in EXPECTED_RESULT_FILES:
        (out / name).write_text("OLD-%s\n" % name, encoding="utf-8")
    return out


def _old_bytes(out: Path) -> dict:
    return {n: (out / n).read_bytes() for n in EXPECTED_RESULT_FILES}


def _ipv6_rejected(settings: dict, names: dict) -> bool:
    line = "[2001:db8::1]:443#SG-Singapore-SIN-10ms"
    try:
        safety.validate_txt(line + "\n", filename="SG.txt",
                            expected_lines=[line], settings=settings,
                            names=names, max_lines=5)
    except safety.SafetyError:
        return True
    return False


def _independent_rendering() -> bool:
    """源码级确认：发布循环内逐榜渲染，循环前没有集体渲染/集体选榜。"""
    text = (APP_DIR / "pipeline.py").read_text(encoding="utf-8")
    return ("render_all_boards(" not in text
            and "select_boards(" not in text
            and "output.render_board(" in text
            and "ranking.select_board(" in text
            and "for name in EXPECTED_RESULT_FILES:" in text)


# --------------------------------------------------------------------------
# --check-config
# --------------------------------------------------------------------------
def cmd_check_config() -> int:
    try:
        settings, regions = validate_all()
    except Exception as exc:
        print("[失败] 配置校验未通过: %s" % exc)
        return 1

    print("=== cf-ip-optimizer 阶段 %s 配置校验（单轮测速版）===" % __stage__)
    print("程序版本      : %s" % __version__)
    print("项目根        : %s" % PROJECT_ROOT)
    print("settings.json : %s" % SETTINGS_PATH)
    print("regions.json  : %s" % REGIONS_PATH)
    print()
    print("--- settings.json：必填字段、类型、范围校验通过 ---")
    for key in ("run_mode", "download_url", "port", "cfst_binary", "ip_file",
                "concurrency", "latency_count", "download_count",
                "download_duration", "cfst_timeout_sec", "region_top_n",
                "global_top_n", "speed_unit", "timezone", "loss_unit",
                "csv_path", "output_dir", "log_dir"):
        print("  %-19s = %s" % (key, settings[key]))
    print("  result_files        = %s" % ", ".join(settings["result_files"]))
    print("  已废弃键检查        = httping_url / httping_count / max_merged 均不存在")
    print("  -dn 说明            = 进入下载测速的候选 IP 数量，非总扫描 IP 数；"
          "当前 %d（可调 1~10000）" % settings["download_count"])
    print()
    print("--- 运行资产（只读，不创建目录）---")
    for key, path in asset_paths(settings).items():
        print("  %-12s %s  [%s]" % (key, path, "存在" if path.exists() else "本机预览/尚未创建"))
    print()
    print("--- regions.json：只使用已确认 Colo，未补全、未猜测 ---")
    for code in TARGET_REGIONS:
        colos = regions["regions"][code]
        print("  %-3s (%-12s): %s" % (code, regions["region_names"][code],
                                      ", ".join(colos) if colos else "(空，待真实样本)"))
    print("  pending=%s  excluded=%s  no_samples=%s" % (
        ", ".join(regions.get("pending", {})),
        ", ".join(regions.get("excluded", {})),
        ", ".join(regions.get("no_samples", []))))
    print("  unknown_policy: 未确认 Colo -> UNKNOWN，可进全球榜，不进地区榜")
    print()
    print("--- 唯一一条完整 CFST 命令（仅构造，未执行、未测速）---")
    argv = cfst.build_command(settings)
    print("  %s" % " ".join(argv))
    print("  禁用参数自检: %s" % (cfst.command_violations(argv, settings) or "无违规"))
    print("  -dn = %s（来自 settings.json，可配置）" % argv[argv.index("-dn") + 1])
    print("  注意: 上面 -o 指向配置中的正式 CSV 仅用于展示；生产运行时由")
    print("        pipeline.run_once 改为本轮一次性路径 .cfst-run-<run_id>.csv，")
    print("        成功后才原子归档为 data/result.csv，避免误读上一轮遗留 CSV。")
    print("  CSV 表头   : %s" % CSV_HEADER)
    print("  表头识别   : 解析与完整性校验共用 HEADER_ALIASES 语义字段（支持中英文）")
    print("  丢包率     : ratio 严格 0~1；显式 % 按百分数；不按数值大小猜测单位")
    print("  IP 范围    : 当前阶段仅 IPv4，IPv6 不进入六个榜单")
    print("  说明: 普通 TCPing + 下载模式，一次测速一份 CSV；分类直接读本轮地区码。")
    print("  离线证据: samples/phase2-download-3ip.csv 与")
    print("           samples/phase2-download-cloudflare-108.csv 中普通下载模式")
    print("           同时含速度(MB/s)、平均延迟、丢包率与 Colo(SIN/LAX/N/A)。")
    print("  权限提示: mkstemp 生成 0o600 的最终 TXT（UID 1000 / GID 0 预期），")
    print("           本阶段不放宽权限，读取权限留待阶段 4.2 实测。")
    print()
    print("[通过] 配置校验完成；本阶段不执行真实测速、不写正式结果、不启动容器。")
    return 0


# --------------------------------------------------------------------------
# --self-test：任务书 28 项 + 4.1-R1 新增 18 项 + 网络守卫
# --------------------------------------------------------------------------
def cmd_self_test() -> int:
    import socket
    import urllib.request

    attempts = []

    def _blocked(*args, **kwargs):
        attempts.append(repr(args)[:120])
        raise RuntimeError("阶段 4.1 网络守卫：禁止真实网络请求")

    patches = [
        mock.patch.object(socket.socket, "connect", new=_blocked),
        mock.patch.object(socket, "create_connection", new=_blocked),
        mock.patch.object(urllib.request, "urlopen", new=_blocked),
    ]
    guard_note = "已安装（socket.connect / create_connection / urlopen）"
    try:
        for p in patches:
            p.start()
    except Exception as exc:
        guard_note = "安装失败: %s（改用源码静态扫描佐证）" % exc

    results = []

    def check(tid, name, fn):
        try:
            ok, reason = bool(fn()), ""
        except Exception as exc:
            ok, reason = False, "%s: %s" % (type(exc).__name__, exc)
        results.append((tid, name, ok, reason))

    settings, regions = validate_all()
    names = region_names(regions)
    cmap = colo_map(regions)
    argv = cfst.build_command(settings)
    fixture = _fixture_csv_text()
    perm_modes = {}

    # --- 命令构造 1~6 ---
    check("T01", "只构造一条完整 CFST 测速命令",
          lambda: len([n for n in dir(cfst) if n.startswith("build_") and n.endswith("command")]) == 1
          and isinstance(argv, list) and argv.count("-url") == 1)
    check("T02", "命令不包含 -httping / -httping-code",
          lambda: not any(t.startswith("-httping") for t in argv))
    check("T03", "命令不包含 -dd", lambda: "-dd" not in argv)
    check("T04", "命令不包含 -cfcolo", lambda: "-cfcolo" not in argv)
    check("T05", "命令使用官方 Cloudflare 下载地址",
          lambda: settings["download_url"] == "https://speed.cloudflare.com/__down?bytes=10000000"
          and settings["download_url"] in argv)
    check("T06", "命令使用完整 IPv4 文件 ip.txt",
          lambda: argv[argv.index("-f") + 1].endswith("ip.txt")
          and settings["ip_file"] == "bin/cfst_linux_amd64/ip.txt")
    check("T01b", "execute_cfst 在 4.1 拒绝真实测速",
          lambda: _raises(lambda: cfst.execute_cfst(argv, 60), NotImplementedError))

    # --- 地区映射 7~9、11 ---
    check("T07", "SIN 正确归类 SG", lambda: classify("SIN", cmap) == "SG")
    check("T08", "LAX 正确归类 US", lambda: classify("LAX", cmap) == "US")
    check("T09", "DEN/AMS/N/A/XYZ/HKG/空值均不自动归类",
          lambda: all(classify(x, cmap) == UNKNOWN
                      for x in ("DEN", "AMS", "N/A", "XYZ", "HKG", "", " sin x ")))
    check("T09b", "配置未猜测 HK/JP/KR 映射",
          lambda: all(not regions["regions"][r] for r in ("HK", "JP", "KR")))

    # --- 解析 + 排名 10~19 ---
    data = cfst.parse_csv_text(fixture)
    candidates = [c for c in (
        ranking.make_candidate(row, cmap, settings["loss_unit"]) for row in data.rows
    ) if c is not None]
    boards = ranking.select_boards(candidates, settings)
    contents = output.render_all_boards(boards, settings, names)

    check("T10", "未知 Colo 的有效 IP 可以进入全球榜",
          lambda: any(c.region == UNKNOWN for c in boards["global_top25.txt"]))
    check("T11", "未知 Colo 不能进入地区榜",
          lambda: all(c.region == code for code in TARGET_REGIONS
                      for c in boards[code + ".txt"]))
    check("T12", "全球榜数量上限 25",
          lambda: len(boards["global_top25.txt"]) == 25
          and len(contents["global_top25.txt"].splitlines()) == 25)
    check("T13", "地区榜数量上限 5",
          lambda: len(boards["SG.txt"]) == 5 and len(boards["US.txt"]) == 5
          and all(len(contents[c + ".txt"].splitlines()) <= 5 for c in TARGET_REGIONS))
    check("T14", "排序：速度降序 / 延迟升序 / 丢包率升序 / IP 稳定",
          lambda: _sorting_ok(candidates, cmap, settings))
    check("T15", "速度为 0 的记录排除",
          lambda: all(c.speed > 0 for c in candidates)
          and "108.162.193.1" not in [c.ip for c in candidates])
    check("T16", "NaN / Infinity / 负数排除",
          lambda: not any(c.ip in ("108.162.193.3", "108.162.193.4",
                                  "108.162.193.5", "108.162.193.6",
                                  "108.162.193.7", "108.162.193.8")
                          for c in candidates))
    check("T17", "非法 IP / N/A 速度排除",
          lambda: not any(c.ip in ("999.999.999.999", "108.162.193.2") for c in candidates))
    check("T18", "丢包率严格按显式单位解析（ratio 0~1，不猜测）",
          lambda: cfst.parse_loss("0.00") == 0.0
          and cfst.parse_loss("0.25") == 0.25
          and cfst.parse_loss("1") == 1.0
          and cfst.parse_loss("25%") == 0.25
          and cfst.parse_loss("25") is None
          and cfst.parse_loss("1.2") is None
          and cfst.parse_loss("N/A") is None
          and cfst.parse_loss("-1") is None
          and cfst.parse_loss("nan") is None
          and cfst.parse_loss("Infinity") is None
          and cfst.parse_loss("200") is None)
    check("T19", "六个文件允许出现重复 IP（不跨文件去重）",
          lambda: boards["SG.txt"][0].ip in
          {c.ip for c in boards["global_top25.txt"]})
    check("T20", "不生成 merged.txt / global_top15.txt",
          lambda: "merged.txt" not in contents
          and "global_top15.txt" not in contents
          and tuple(settings["result_files"]) == EXPECTED_RESULT_FILES)
    check("T21", "六个文件格式正确（IP:443#地区-英文名-Colo-整数ms）",
          lambda: _format_ok(contents, settings, names))
    check("T21b", "延迟四舍五入为整数毫秒",
          lambda: output.format_latency_ms(92.5) == 93
          and output.format_latency_ms(92.4) == 92)

    with tempfile.TemporaryDirectory(prefix="cf41r1-selftest-") as td:
        base = Path(td)

        # ===== 原有：独立更新 / 故障隔离 22~27 =====
        csv_file = base / "result.csv"
        out_dir = _prep_run_dir(base, "out")
        _write_fixture(csv_file)

        def _failing_validator(text):
            raise safety.SafetyError("模拟 SG.txt 校验失败")

        status = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_file,
            output_dir=out_dir, validator_overrides={"SG.txt": _failing_validator},
        )
        check("T22", "单个文件更新失败不影响其他文件",
              lambda: status["files"]["SG.txt"]["status"] == "failed"
              and all(status["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES if n != "SG.txt"))
        check("T23", "单个文件更新失败保留旧文件",
              lambda: (out_dir / "SG.txt").read_text(encoding="utf-8") == "OLD-SG.txt\n")
        check("T24", "成功测速但地区空榜时输出空文件",
              lambda: all((out_dir / (c + ".txt")).read_bytes() == b""
                          for c in ("HK", "JP", "KR")))
        check("T27", "运行状态正确记录六个文件的独立结果",
              lambda: len(status["files"]) == 6
              and status["failed_files"] == ["SG.txt"]
              and status["measurement_success"] is True
              and status["all_files_updated"] is False
              and status["cfst_exit_code"] == 0
              and status["csv_fresh"] is True
              and status["csv_complete"] is True
              and status["csv_total_rows"] == 46
              and status["valid_ip_count"] == 36
              and status["files"]["HK.txt"]["node_count"] == 0
              and status["fastest_node"] is not None)

        before = _old_bytes(out_dir)
        fail_status = pipeline.run_once(
            settings, regions, runner=lambda c, p, t: 1,
            csv_path=csv_file, output_dir=out_dir,
        )
        check("T25", "完整测速失败时所有旧文件不变",
              lambda: all((out_dir / n).read_bytes() == before[n]
                          for n in EXPECTED_RESULT_FILES)
              and all(fail_status["files"][n]["status"] == "skipped"
                      for n in EXPECTED_RESULT_FILES)
              and fail_status["measurement_success"] is False)

        broken = base / "broken.csv"
        _write_text(broken, CSV_HEADER + "\n")
        broken_status = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=broken, output_dir=out_dir,
        )
        check("T25b", "CSV 不完整时全部榜单不更新",
              lambda: broken_status["csv_complete"] is False
              and all((out_dir / n).read_bytes() == before[n]
                      for n in EXPECTED_RESULT_FILES))

        calls = []
        real_replace = os.replace

        def _spy(src, dst):
            calls.append((src, dst))
            return real_replace(src, dst)

        ok_status = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_file,
            output_dir=out_dir, replace_fn=_spy,
        )
        check("T26", "文件使用临时文件及 os.replace() 原子替换",
              lambda: len(calls) == 6
              and all(Path(src).parent == Path(dst).parent for src, dst in calls)
              and all(".tmp-" in Path(src).name for src, _ in calls)
              and safety.leftover_temp_files(out_dir) == []
              and all(ok_status["files"][n]["atomic_replace"] is True
                      for n in EXPECTED_RESULT_FILES))

        # ===== 4.1-R1 新增 R01~R16 =====
        check("R01", "-dn 实际命令参数为配置中的 100",
              lambda: settings["download_count"] == 100
              and argv[argv.index("-dn") + 1] == "100"
              and cfst.command_violations(argv, settings) == [])

        ratio_cases = {
            "0": 0.0, "0.25": 0.25, "1": 1.0, "1.2": None, "25": None,
            "25%": 0.25, "0%": 0.0, "150%": None,
            "NaN": None, "Infinity": None, "-0.1": None, "N/A": None, "": None,
        }
        check("R02", "ratio 边界 0/0.25/1/1.2/25/25%/NaN/Infinity/负数",
              lambda: all(cfst.parse_loss(k) == v for k, v in ratio_cases.items()))

        percent_cases = {
            "25": 0.25, "25%": 0.25, "0": 0.0, "1": 0.01,
            "200": None, "NaN": None, "-1": None,
        }
        check("R03", "percent 边界 25/25%/0/1/200/NaN/负数",
              lambda: all(cfst.parse_loss(k, "percent") == v
                          for k, v in percent_cases.items()))

        check("R04", "不得根据数值是否大于 1 自动猜测单位",
              lambda: all(cfst.parse_loss(x) is None for x in ("1.2", "25", "100", "2"))
              and cfst.parse_loss("25", "percent") == 0.25
              and cfst.parse_loss("25", "bogus") is None)

        # R05 旧 CSV 遗留，但本轮 CFST 没有生成新 CSV
        formal5 = base / "legacy5.csv"
        _write_text(formal5, "LEGACY-OLD-CSV\n")
        out5 = _prep_run_dir(base, "r05")
        old5 = _old_bytes(out5)
        st5 = pipeline.run_once(
            settings, regions, runner=_runner_ok,
            csv_path=base / "this_run_not_written.csv",
            formal_csv_path=formal5, output_dir=out5)
        check("R05", "旧 CSV 遗留但本轮未生成新 CSV -> 六 TXT 全部保持旧内容",
              lambda: all((out5 / n).read_bytes() == old5[n]
                          for n in EXPECTED_RESULT_FILES)
              and all(st5["files"][n]["status"] == "skipped"
                      for n in EXPECTED_RESULT_FILES)
              and st5["csv_fresh"] is False
              and st5["measurement_success"] is False
              and formal5.read_text(encoding="utf-8") == "LEGACY-OLD-CSV\n")

        # R06 本轮 CSV 不完整
        formal6 = base / "legacy6.csv"
        _write_text(formal6, "LEGACY-6\n")
        out6 = _prep_run_dir(base, "r06")
        old6 = _old_bytes(out6)
        incomplete6 = base / "incomplete6.csv"
        _write_text(incomplete6, CSV_HEADER + "\n1.1.1.1,2,2,0.00\n")
        st6 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=incomplete6,
            formal_csv_path=formal6, output_dir=out6)
        check("R06", "本轮 CSV 不完整 -> 六 TXT 全部保持旧内容，历史 CSV 不变",
              lambda: st6["csv_fresh"] is True
              and st6["csv_complete"] is False
              and all((out6 / n).read_bytes() == old6[n]
                      for n in EXPECTED_RESULT_FILES)
              and formal6.read_text(encoding="utf-8") == "LEGACY-6\n")

        # R07 单个榜单渲染失败，其余五榜仍更新
        csv7 = base / "r07.csv"
        _write_fixture(csv7)
        out7 = _prep_run_dir(base, "r07")
        old7 = _old_bytes(out7)

        def _render_boom(items, settings_, names_):
            raise ValueError("注入：SG.txt 渲染失败")

        st7 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv7, output_dir=out7,
            render_overrides={"SG.txt": _render_boom})
        check("R07", "单个榜单渲染失败，其余五榜仍更新",
              lambda: st7["files"]["SG.txt"]["status"] == "failed"
              and all(st7["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES if n != "SG.txt")
              and (out7 / "SG.txt").read_bytes() == old7["SG.txt"]
              and (out7 / "US.txt").read_bytes() != old7["US.txt"]
              and st7["measurement_success"] is True)

        # R08 单个榜单写入失败，其余五榜仍更新
        csv8 = base / "r08.csv"
        _write_fixture(csv8)
        out8 = _prep_run_dir(base, "r08")
        old8 = _old_bytes(out8)
        st8 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv8, output_dir=out8,
            replace_overrides={"KR.txt": OSError("注入：磁盘写入失败")})
        check("R08", "单个榜单写入失败，其余五榜仍更新且旧文件不变",
              lambda: st8["files"]["KR.txt"]["status"] == "failed"
              and all(st8["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES if n != "KR.txt")
              and (out8 / "KR.txt").read_bytes() == old8["KR.txt"]
              and (out8 / "SG.txt").read_bytes() != old8["SG.txt"]
              and safety.leftover_temp_files(out8) == [])

        # R09 IPv6 全面拒绝
        ipv6_row = cfst.CsvRow("2001:db8::1", "2", "2", "0.00", "10", "8.00", "SIN")
        check("R09", "IPv6 被 ranking / output / safety 拒绝",
              lambda: not ranking.is_valid_ip("2001:db8::1")
              and ranking.is_valid_ip("1.1.1.1")
              and ranking.make_candidate(ipv6_row, cmap) is None
              and _raises(lambda: output.format_ip_port("2001:db8::1"), ValueError)
              and not safety._LINE_RE.match("[2001:db8::1]:443#SG-Singapore-SIN-10ms")
              and safety._LINE_RE.match("1.1.1.1:443#SG-Singapore-SIN-10ms") is not None
              and _ipv6_rejected(settings, names))

        # R10 六榜为空 / 地区榜不足 5 / 全球榜不足 25
        csv_empty = base / "empty.csv"
        _write_text(csv_empty, _empty_board_csv_text())
        out_empty = _prep_run_dir(base, "r10empty")
        st_empty = pipeline.run_once(settings, regions, runner=_runner_ok,
                                     csv_path=csv_empty, output_dir=out_empty)
        csv_small = base / "small.csv"
        _write_text(csv_small, _small_csv_text())
        out_small = _prep_run_dir(base, "r10small")
        st_small = pipeline.run_once(settings, regions, runner=_runner_ok,
                                     csv_path=csv_small, output_dir=out_small)
        check("R10", "六榜为空 / 地区榜不足 5 / 全球榜不足 25 均输出实际数量",
              lambda: all(st_empty["files"][n]["node_count"] == 0
                          for n in EXPECTED_RESULT_FILES)
              and all((out_empty / n).read_bytes() == b"" for n in EXPECTED_RESULT_FILES)
              and st_small["files"]["SG.txt"]["node_count"] == 1
              and st_small["files"]["US.txt"]["node_count"] == 1
              and st_small["files"]["global_top25.txt"]["node_count"] == 2
              and all(st_small["files"][c + ".txt"]["node_count"] == 0
                      for c in ("HK", "JP", "KR"))
              and (out_small / "SG.txt").read_text(encoding="utf-8").count("\n") == 1)

        # R11 原子替换无残留 + mkstemp 权限
        csv11 = base / "r11.csv"
        _write_fixture(csv11)
        out11 = _prep_run_dir(base, "r11")
        calls11 = []

        def _spy11(src, dst):
            calls11.append((src, dst))
            return real_replace(src, dst)

        st11 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                 csv_path=csv11, output_dir=out11, replace_fn=_spy11)
        perm_modes.update({
            n: stat.S_IMODE((out11 / n).stat().st_mode)
            for n in EXPECTED_RESULT_FILES
        })

        def _perm_ok():
            if os.name != "posix":
                return True  # 非 POSIX 仅记录，精确断言在 NAS 侧执行
            return all(m == 0o600 for m in perm_modes.values())

        check("R11", "原子替换无临时文件残留；最终 TXT 保持 mkstemp 的 0o600",
              lambda: len(calls11) == 6
              and safety.leftover_temp_files(out11) == []
              and _perm_ok()
              and all(st11["files"][n]["atomic_replace"] is True
                      for n in EXPECTED_RESULT_FILES))

        check("R12", "目录中不生成 merged.txt / global_top15.txt",
              lambda: not (out11 / "merged.txt").exists()
              and not (out11 / "global_top15.txt").exists()
              and sorted(x.name for x in out11.iterdir()) == sorted(EXPECTED_RESULT_FILES))

        # R13 表头别名统一（英文表头解析成功且完整性通过）
        en_header = ("IP Address,Sent,Received,Loss,Average Latency,"
                     "Download Speed (MB/s),Colo")
        en_text = en_header + "\n1.1.1.1,2,2,0.00,50.00,10.00,SIN\n"
        en_path = base / "english.csv"
        _write_text(en_path, en_text)
        en_data = cfst.parse_csv_text(en_text)
        en_ok, en_reason, en_parsed = cfst.validate_csv_completeness(en_path)
        check("R13", "表头解析与完整性校验共用别名逻辑（英文表头通过）",
              lambda: en_ok
              and set(en_data.resolved_fields) == set(cfst.REQUIRED_SEMANTIC_FIELDS)
              and en_parsed.rows[0].ip == "1.1.1.1"
              and en_reason == "完整")

        # R14 CSV 新鲜度：陈旧 mtime 的本轮路径被拒绝
        csv14 = base / "stale14.csv"
        _write_fixture(csv14)
        old_ns = time.time_ns() - 10 * 86400 * 1_000_000_000
        os.utime(csv14, ns=(old_ns, old_ns))
        out14 = _prep_run_dir(base, "r14")
        old14 = _old_bytes(out14)
        st14 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                 csv_path=csv14, output_dir=out14)
        check("R14", "本轮 CSV 时间戳陈旧 -> 拒绝发布，六 TXT 保持旧内容",
              lambda: st14["csv_fresh"] is False
              and st14["csv_complete"] is False
              and all((out14 / n).read_bytes() == old14[n]
                      for n in EXPECTED_RESULT_FILES))

        # R15 测速异常时历史 CSV 与六个旧 TXT 均不变
        formal15 = base / "legacy15.csv"
        _write_text(formal15, "KEEP-ME\n")
        out15 = _prep_run_dir(base, "r15")
        old15 = _old_bytes(out15)
        st15 = pipeline.run_once(
            settings, regions,
            runner=lambda c, p, t: (_ for _ in ()).throw(RuntimeError("模拟 CFST 异常")),
            csv_path=base / "r15run.csv", formal_csv_path=formal15,
            output_dir=out15)
        check("R15", "测速异常时历史 CSV 与六个旧 TXT 均保持不变",
              lambda: formal15.read_text(encoding="utf-8") == "KEEP-ME\n"
              and all((out15 / n).read_bytes() == old15[n]
                      for n in EXPECTED_RESULT_FILES)
              and all(st15["files"][n]["status"] == "skipped"
                      for n in EXPECTED_RESULT_FILES))

        # R16 生产式：本轮独立路径 + 成功后归档 + 无残留
        formal16 = base / "result16.csv"
        _write_text(formal16, "OLD-RESULT\n")
        out16 = _prep_run_dir(base, "r16")
        st16 = pipeline.run_once(
            settings, regions, runner=_runner_writes(fixture),
            formal_csv_path=formal16, output_dir=out16, run_id="selftest-r16")
        check("R16", "本轮独立 CSV 生成 -> 六榜发布 -> 归档 -> 一次性路径无残留",
              lambda: st16["csv_fresh"] is True
              and st16["csv_complete"] is True
              and st16["csv_archived"] is True
              and formal16.read_text(encoding="utf-8") == fixture
              and not Path(st16["run_csv_path"]).exists()
              and st16["run_csv_path"] != st16["formal_csv_path"]
              and cfst.RUN_CSV_PREFIX in Path(st16["run_csv_path"]).name
              and not any(x.name.startswith(cfst.RUN_CSV_PREFIX) for x in base.iterdir())
              and all(st16["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES))

        check("R18", "生产 -o 指向本轮一次性路径，不是 data/result.csv",
              lambda: st16["cfst_command"][st16["cfst_command"].index("-o") + 1]
              == st16["run_csv_path"]
              and Path(st16["run_csv_path"]).name.startswith(cfst.RUN_CSV_PREFIX))

    check("R17", "源码级：发布循环内逐榜独立渲染，无集体渲染/集体选榜",
          lambda: _independent_rendering())
    check("T28", "配置检查通过",
          lambda: validate_all()[0]["run_mode"] == "single_pass"
          and validate_all()[1]["regions"]["SG"] == ["SIN"])
    check("T28b", "源码静态扫描：业务模块无网络/subprocess 导入",
          lambda: _no_network_imports())

    try:
        for p in patches:
            p.stop()
    except Exception:
        pass

    print("=== 阶段 %s 离线必测：任务书 28 项 + R1 新增 18 项 ===" % __stage__)
    print("网络守卫: %s" % guard_note)
    for tid, name, ok, reason in results:
        print("  %-5s [%s] %s%s" % (tid, "PASS" if ok else "FAIL", name,
                                    ("  <- " + reason) if reason else ""))
    skipped = [
        ("S01", "真实 CFST 完整测速 / 真实 CSV 单位验证 -> 阶段 4.4，需用户明确授权"),
        ("S02", "容器 Python 3.12 集成 / 0o600 读取权限 / 只读根文件系统 -> 阶段 4.2"),
    ]
    for tid, name in skipped:
        print("  %-5s [SKIP] %s" % (tid, name))
    failed = [r for r in results if not r[2]]
    print("--- 通过 %d，失败 %d，跳过 %d，合计 %d ---" %
          (len(results) - len(failed), len(failed), len(skipped), len(results) + len(skipped)))
    print("--- 网络守卫拦截到的连接尝试: %d 次 ---" % len(attempts))
    if attempts:
        print("    %s" % attempts[:3])
    print("--- 最终 TXT 权限实测 mode: %s（%s）---" %
          ({n: oct(m) for n, m in perm_modes.items()},
           "POSIX，断言 0o600" if os.name == "posix" else "非 POSIX，精确断言留待 NAS"))
    for tid, name, ok, reason in failed:
        print("    [失败详情] %s %s : %s" % (tid, name, reason))
    return 0 if (not failed and not attempts) else 1


def _raises(fn, exc_type) -> bool:
    try:
        fn()
    except exc_type:
        return True
    return False


def _sorting_ok(candidates, cmap, settings) -> bool:
    ranked = ranking.sort_candidates(candidates)
    for a, b in zip(ranked, ranked[1:]):
        if a.speed < b.speed:
            return False
        if a.speed == b.speed and a.latency > b.latency:
            return False
        if a.speed == b.speed and a.latency == b.latency and a.loss > b.loss:
            return False
    # 丢包率作为第三排序键的定向用例
    rows = [
        cfst.CsvRow("1.1.1.1", "2", "2", "0.30", "50", "20.00", "SIN"),
        cfst.CsvRow("1.1.1.2", "2", "2", "0.10", "50", "20.00", "SIN"),
    ]
    got = [c for c in (ranking.make_candidate(r, cmap) for r in rows) if c]
    return ranking.sort_candidates(got)[0].ip == "1.1.1.2"


def _format_ok(contents, settings, names) -> bool:
    for name, content in contents.items():
        if not isinstance(content, str):
            return False
        for line in content.splitlines():
            if not safety._LINE_RE.match(line):
                return False
        if name in safety.REGION_FILES and "UNKNOWN" in content:
            return False
        if name == safety.GLOBAL_FILE and "UNKNOWN-Unknown-DEN-" not in content:
            return False
    return True


def _no_network_imports() -> bool:
    banned = ("import socket", "urllib.request", "import subprocess",
              "import requests", "urlopen(")
    files = ["config.py", "cfst.py", "region.py", "ranking.py",
             "output.py", "safety.py", "pipeline.py"]
    for name in files:
        text = (APP_DIR / name).read_text(encoding="utf-8")
        if any(token in text for token in banned):
            return False
    return True


# --------------------------------------------------------------------------
# --simulate：九个离线场景的完整输出
# --------------------------------------------------------------------------
def cmd_simulate() -> int:
    settings, regions = validate_all()
    names = region_names(regions)
    fixture = _fixture_csv_text()
    real_replace = os.replace
    print("=== 阶段 %s 离线模拟（临时目录，不写 NAS 正式文件、不联网）===" % __stage__)
    print("模拟 CSV：%d 条有效记录 + 10 条无效记录；Colo 含 SIN/LAX/DEN/AMS/N/A/XYZ" %
          (len(fixture.splitlines()) - 11))

    with tempfile.TemporaryDirectory(prefix="cf41r1-sim-") as td:
        base = Path(td)

        # 场景 1：正常六榜
        csv1, out1 = base / "s1.csv", base / "s1"
        _write_fixture(csv1)
        calls = []

        def _spy(src, dst):
            calls.append((src, dst))
            return real_replace(src, dst)

        st1 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                csv_path=csv1, output_dir=out1, replace_fn=_spy)
        print("\n----- 场景 1：一次完整测速 -> 六个 TXT -----")
        print("CFST 退出码=%s  CSV 新鲜=%s  CSV 完整=%s  CSV 总记录=%d  有效 IP=%d" %
              (st1["cfst_exit_code"], st1["csv_fresh"], st1["csv_complete"],
               st1["csv_total_rows"], st1["valid_ip_count"]))
        print("本次最快节点: %s" % (st1["fastest_node"]["node"] if st1["fastest_node"] else "无"))
        print("CFST 命令(仅构造): %s" % " ".join(st1["cfst_command"]))
        for name in EXPECTED_RESULT_FILES:
            content = (out1 / name).read_text(encoding="utf-8")
            info = st1["files"][name]
            print("\n--- %s | %s | %d 行 | %d 字节 ---" %
                  (name, info["status"], info["node_count"] or 0, len(content.encode())))
            print(content if content else "(空文件，0 字节)")
        print("\n目录文件清单: %s" % sorted(x.name for x in out1.iterdir()))
        print("merged.txt 存在? %s" % (out1 / "merged.txt").exists())
        print("os.replace 调用次数=%d，临时文件残留=%s" %
              (len(calls), safety.leftover_temp_files(out1)))
        print("[场景 1] 六文件全部独立更新=%s" % st1["all_files_updated"])

        # 场景 2：单文件校验失败隔离
        csv2, out2 = base / "s2.csv", base / "s2"
        _write_fixture(csv2)
        out2.mkdir()
        for name in EXPECTED_RESULT_FILES:
            (out2 / name).write_text("OLD-%s\n" % name, encoding="utf-8")
        old = _old_bytes(out2)

        def _fail_sg(text):
            raise safety.SafetyError("注入故障：模拟 SG.txt 校验失败")

        st2 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                csv_path=csv2, output_dir=out2,
                                validator_overrides={"SG.txt": _fail_sg})
        print("\n----- 场景 2：单文件校验失败隔离 -----")
        for name in EXPECTED_RESULT_FILES:
            info = st2["files"][name]
            print("  %-18s status=%-8s node_count=%-5s reason=%s" %
                  (name, info["status"], info["node_count"], info["reason"]))
        print("  SG.txt 旧内容是否原样保留: %s" %
              ((out2 / "SG.txt").read_bytes() == old["SG.txt"]))
        print("  HK.txt 是否被更新为空文件(情况A): %s" %
              ((out2 / "HK.txt").read_bytes() == b""))
        print("  US.txt 是否照常更新(非旧内容): %s" %
              ((out2 / "US.txt").read_bytes() != old["US.txt"]))
        print("  失败文件列表=%s  全部更新=%s" %
              (st2["failed_files"], st2["all_files_updated"]))
        print("  临时文件残留=%s" % safety.leftover_temp_files(out2))

        # 场景 3：完整测速失败（退出码非 0）
        csv3, out3 = base / "s3.csv", base / "s3"
        _write_fixture(csv3)
        out3.mkdir()
        for name in EXPECTED_RESULT_FILES:
            (out3 / name).write_text("OLD-%s\n" % name, encoding="utf-8")
        old3 = _old_bytes(out3)
        st3 = pipeline.run_once(settings, regions, runner=lambda c, p, t: 1,
                                csv_path=csv3, output_dir=out3)
        print("\n----- 场景 3：完整测速失败（CFST 退出码=1）-----")
        print("  measurement_success=%s  csv_fresh=%s  csv_complete=%s  failure_reason=%s" %
              (st3["measurement_success"], st3["csv_fresh"], st3["csv_complete"],
               st3.get("failure_reason")))
        print("  六文件全部保持旧版本: %s" %
              all((out3 / n).read_bytes() == old3[n] for n in EXPECTED_RESULT_FILES))
        print("  六文件状态: %s" %
              {n: st3["files"][n]["status"] for n in EXPECTED_RESULT_FILES})

        # 场景 3b：CSV 不完整（只有表头 + 截断行）
        broken, out3b = base / "broken.csv", base / "s3b"
        _write_text(broken, CSV_HEADER + "\n1.1.1.1,2,2,0.00\n")
        out3b.mkdir()
        for name in EXPECTED_RESULT_FILES:
            (out3b / name).write_text("OLD-%s\n" % name, encoding="utf-8")
        old3b = _old_bytes(out3b)
        st3b = pipeline.run_once(settings, regions, runner=_runner_ok,
                                 csv_path=broken, output_dir=out3b)
        print("\n----- 场景 3b：CSV 不完整（截断行）-----")
        print("  csv_fresh=%s  csv_complete=%s  failure_reason=%s" %
              (st3b["csv_fresh"], st3b["csv_complete"], st3b.get("failure_reason")))
        print("  六文件全部保持旧版本: %s" %
              all((out3b / n).read_bytes() == old3b[n] for n in EXPECTED_RESULT_FILES))

        # 场景 4：空榜（HK/JP/KR 无确认 Colo，但有旧内容）
        csv4, out4 = base / "s4.csv", base / "s4"
        _write_fixture(csv4)
        out4.mkdir()
        for code in ("HK", "JP", "KR"):
            (out4 / (code + ".txt")).write_text(
                "%s.txt#OLD-节点\n" % code, encoding="utf-8")
        st4 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                csv_path=csv4, output_dir=out4)
        print("\n----- 场景 4：成功测速，地区空榜应更新为空文件 -----")
        for code in ("HK", "JP", "KR"):
            name = code + ".txt"
            print("  %-6s status=%-8s node_count=%s 字节数=%d 内容=%r" %
                  (name, st4["files"][name]["status"],
                   st4["files"][name]["node_count"],
                   (out4 / name).stat().st_size,
                   (out4 / name).read_text(encoding="utf-8")))
        print("  SG.txt 行数=%d  global_top25.txt 行数=%d" %
              (st4["files"]["SG.txt"]["node_count"],
               st4["files"]["global_top25.txt"]["node_count"]))

        # 场景 5：原子替换细节
        csv5, out5 = base / "s5.csv", base / "s5"
        _write_fixture(csv5)
        out5.mkdir()
        replace_log = []

        def _spy5(src, dst):
            replace_log.append((Path(src).name, Path(src).parent == Path(dst).parent))
            return real_replace(src, dst)

        st5 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                csv_path=csv5, output_dir=out5, replace_fn=_spy5)
        print("\n----- 场景 5：临时文件 + os.replace() 原子替换 -----")
        for tmp_name, same_dir in replace_log:
            print("  os.replace 临时文件=%-40s 同目录=%s" % (tmp_name, same_dir))
        print("  调用次数=%d  临时文件残留=%s  正式文件=%s" %
              (len(replace_log), safety.leftover_temp_files(out5),
               sorted(x.name for x in out5.iterdir())))
        print("  六文件 atomic_replace 全为 True: %s" %
              all(st5["files"][n]["atomic_replace"] for n in EXPECTED_RESULT_FILES))
        print("  最终 TXT 权限(mode): %s" %
              {n: oct(stat.S_IMODE((out5 / n).stat().st_mode))
               for n in EXPECTED_RESULT_FILES})

        # 场景 6：CSV 本轮新鲜度（旧 CSV 遗留 / 陈旧 mtime / 本轮不完整）
        print("\n----- 场景 6：CSV 本轮新鲜度（不误读上一轮遗留）-----")
        formal6 = base / "legacy6.csv"
        _write_text(formal6, "LEGACY-OLD-CSV-CONTENT\n")
        out6 = _prep_run_dir(base, "s6")
        old6 = _old_bytes(out6)
        st6 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                csv_path=base / "not_written6.csv",
                                formal_csv_path=formal6, output_dir=out6)
        print("  6a 旧 CSV 存在但本轮未生成新 CSV:")
        print("     csv_fresh=%s  measurement_success=%s  failure_reason=%s" %
              (st6["csv_fresh"], st6["measurement_success"], st6.get("failure_reason")))
        print("     六 TXT 全部保持旧内容=%s  历史 CSV 未变=%s" %
              (all((out6 / n).read_bytes() == old6[n] for n in EXPECTED_RESULT_FILES),
               formal6.read_text(encoding="utf-8") == "LEGACY-OLD-CSV-CONTENT\n"))

        stale6 = base / "stale6.csv"
        _write_fixture(stale6)
        old_ns = time.time_ns() - 10 * 86400 * 1_000_000_000
        os.utime(stale6, ns=(old_ns, old_ns))
        out6b = _prep_run_dir(base, "s6b")
        old6b = _old_bytes(out6b)
        st6b = pipeline.run_once(settings, regions, runner=_runner_ok,
                                 csv_path=stale6, output_dir=out6b)
        print("  6b 本轮路径存在但 mtime 陈旧(10 天前):")
        print("     csv_fresh=%s  failure_reason=%s  六 TXT 保持旧内容=%s" %
              (st6b["csv_fresh"], st6b.get("failure_reason"),
               all((out6b / n).read_bytes() == old6b[n] for n in EXPECTED_RESULT_FILES)))

        # 场景 7：单榜渲染失败 / 单榜写入失败
        print("\n----- 场景 7：单榜渲染失败与单榜写入失败隔离 -----")
        csv7 = base / "s7.csv"
        _write_fixture(csv7)
        out7 = _prep_run_dir(base, "s7")
        old7 = _old_bytes(out7)

        def _boom(items, s, n):
            raise ValueError("注入：SG.txt 渲染失败")

        st7 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                csv_path=csv7, output_dir=out7,
                                render_overrides={"SG.txt": _boom})
        print("  7a 单榜渲染失败: %s" %
              {n: st7["files"][n]["status"] for n in EXPECTED_RESULT_FILES})
        print("     SG.txt 旧内容保留=%s  其余五榜仍更新=%s" %
              ((out7 / "SG.txt").read_bytes() == old7["SG.txt"],
               all(st7["files"][n]["status"] == "updated"
                   for n in EXPECTED_RESULT_FILES if n != "SG.txt")))

        out8 = _prep_run_dir(base, "s8")
        old8 = _old_bytes(out8)
        st8 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                csv_path=csv7, output_dir=out8,
                                replace_overrides={"KR.txt": OSError("注入：写入失败")})
        print("  7b 单榜写入失败: %s" %
              {n: st8["files"][n]["status"] for n in EXPECTED_RESULT_FILES})
        print("     KR.txt 旧内容保留=%s  其余五榜仍更新=%s  临时残留=%s" %
              ((out8 / "KR.txt").read_bytes() == old8["KR.txt"],
               all(st8["files"][n]["status"] == "updated"
                   for n in EXPECTED_RESULT_FILES if n != "KR.txt"),
               safety.leftover_temp_files(out8)))

        # 场景 8：数量边界 / IPv6 / 表头别名
        print("\n----- 场景 8：数量边界 / IPv4 严格 / 表头别名 -----")
        csv_empty = base / "empty8.csv"
        _write_text(csv_empty, _empty_board_csv_text())
        out8a = _prep_run_dir(base, "s8empty")
        st8a = pipeline.run_once(settings, regions, runner=_runner_ok,
                                 csv_path=csv_empty, output_dir=out8a)
        print("  8a 六榜全空: %s  全部为 0 字节=%s" %
              ({n: st8a["files"][n]["node_count"] for n in EXPECTED_RESULT_FILES},
               all((out8a / n).read_bytes() == b"" for n in EXPECTED_RESULT_FILES)))

        csv_small = base / "small8.csv"
        _write_text(csv_small, _small_csv_text())
        out8b = _prep_run_dir(base, "s8small")
        st8b = pipeline.run_once(settings, regions, runner=_runner_ok,
                                 csv_path=csv_small, output_dir=out8b)
        print("  8b 地区榜不足 5 / 全球榜不足 25: %s" %
              {n: st8b["files"][n]["node_count"] for n in EXPECTED_RESULT_FILES})

        print("  8c IPv4 严格: is_valid_ip('1.1.1.1')=%s  "
              "is_valid_ip('2001:db8::1')=%s  _LINE_RE(IPv6)=%s" %
              (ranking.is_valid_ip("1.1.1.1"),
               ranking.is_valid_ip("2001:db8::1"),
               bool(safety._LINE_RE.match("[2001:db8::1]:443#SG-Singapore-SIN-10ms"))))

        en_header = ("IP Address,Sent,Received,Loss,Average Latency,"
                     "Download Speed (MB/s),Colo")
        en_csv = base / "english8.csv"
        _write_text(en_csv, en_header + "\n1.1.1.1,2,2,0.00,50.00,10.00,SIN\n")
        en_ok, en_reason, _ = cfst.validate_csv_completeness(en_csv)
        print("  8d 英文表头解析+完整性统一: ok=%s reason=%s" % (en_ok, en_reason))

        # 场景 9：生产式本轮独立 CSV 路径 + 归档
        print("\n----- 场景 9：本轮独立 CSV 路径 + 成功后归档 -----")
        formal9 = base / "result9.csv"
        _write_text(formal9, "OLD-RESULT\n")
        out9 = _prep_run_dir(base, "s9")
        st9 = pipeline.run_once(settings, regions,
                                runner=_runner_writes(fixture),
                                formal_csv_path=formal9, output_dir=out9,
                                run_id="simulate-s9")
        print("  本轮 CSV 路径 : %s" % st9["run_csv_path"])
        print("  正式历史路径 : %s" % st9["formal_csv_path"])
        print("  -o 实际参数  : %s" %
              st9["cfst_command"][st9["cfst_command"].index("-o") + 1])
        print("  csv_fresh=%s  csv_complete=%s  csv_archived=%s" %
              (st9["csv_fresh"], st9["csv_complete"], st9["csv_archived"]))
        print("  历史 CSV 已更新为本轮内容=%s  一次性路径已消失=%s" %
              (formal9.read_text(encoding="utf-8") == fixture,
               not Path(st9["run_csv_path"]).exists()))
        print("  目录内无 .cfst-run-* 残留=%s  六榜状态=%s" %
              (not any(x.name.startswith(cfst.RUN_CSV_PREFIX) for x in base.iterdir()),
               {n: st9["files"][n]["status"] for n in EXPECTED_RESULT_FILES}))

        # 运行状态完整记录
        print("\n----- 运行状态 JSON 样例（场景 2，含失败文件）-----")
        print(output.render_run_status({
            k: st2[k] for k in ("run_time", "cfst_exit_code", "csv_fresh",
                                "csv_complete", "csv_total_rows", "valid_ip_count",
                                "files", "failed_files", "fastest_node",
                                "measurement_success", "all_files_updated")
        }), end="")

    print("\n=== 模拟结束：临时目录已自动清理；NAS data/ 与正式订阅文件未被写入 ===")
    return 0


# --------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description="cf-ip-optimizer 阶段 4.1-R1（单轮测速 / 六榜独立发布；不执行真实测速）",
    )
    parser.add_argument("--check-config", action="store_true",
                         help="加载并校验 settings.json / regions.json")
    parser.add_argument("--self-test", action="store_true",
                         help="运行任务书 28 项 + R1 新增 18 项离线必测")
    parser.add_argument("--simulate", action="store_true",
                         help="临时目录离线模拟九类场景")
    parser.add_argument("--run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version",
                        version="cf-ip-optimizer %s (stage %s)" % (__version__, __stage__))
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.run:
        print("[拒绝] --run（真实测速）在阶段 4.1 禁止；须在阶段 4.4 获得明确授权后启用。")
        return 2
    if not (args.check_config or args.self_test or args.simulate):
        parser.print_help()
        return 0
    rc = 0
    if args.check_config:
        rc = rc or cmd_check_config()
    if args.self_test:
        rc = rc or cmd_self_test()
    if args.simulate:
        rc = rc or cmd_simulate()
    return rc


if __name__ == "__main__":
    sys.exit(main())
````


## 3 docs/TASK_BOOK.md 新增附录 B（全文）

````markdown
# 附录 B：阶段 4.1-R1 源码审查修正记录（2026-11-22）

> 依据 ChatGPT 对 `STAGE4_1_CODE_REVIEW.md` 的只读审查结论做的针对性修正。
> 本轮授权范围：**仅修改源码与配置**，不得启动容器、不得执行真实 CFST 测速、
> 不得修改 Cron、不得上传 GitHub、不得修改 EdgeTunnel。完成后停止等待只读验收。

## B.1 已完成的修正

| 编号 | 类别 | 修正内容 |
|---|---|---|
| 1 | 必须 | `config/settings.json`：`download_count` 5 → **100**（保留 1~10000 可调）；notes 删除「沿用初始值 5」过时说明，明确 `-dn` 是**进入下载测速的候选 IP 数量**，不是总扫描 IP 数；有效记录不足时按实际数量输出。 |
| 2 | 必须 | `app/cfst.py` `parse_loss()` 重写：ratio 只接受 0~1 的无百分号数值；percent 明确 /100；显式 `%` 按百分数转换且只除一次；**删除 `value > 1.0` 的数值猜测分支**；负数/NaN/Infinity/N/A/未知单位一律返回 None，由 `ranking.make_candidate` 整条排除，不静默当作 0 丢包。 |
| 3 | 必须 | CSV 本轮新鲜度：新增 `new_run_csv_path` / `prepare_run_csv` / `csv_is_fresh`；生产运行 CFST `-o` 指向同目录一次性路径 `.cfst-run-<run_id>.csv`，与正式 `data/result.csv` 不重名；要求本轮文件存在、非空、mtime 不早于本轮开始且完整性校验通过才发布六榜；成功后才原子归档为 `data/result.csv`；本轮失败只删除本轮临时 CSV，历史 CSV 与六个旧 TXT 均不变。 |
| 4 | 必须 | 六文件生成隔离：`pipeline.run_once` 不再于发布循环前调用集体渲染 `render_all_boards` / 集体选榜 `select_boards`；改为循环内对每个榜单独立 `select_board` → `render_board` → `validate_txt` → `publish_one`，各自 `try/except`；最快节点计算单独 `try`，异常只记 warning。 |
| 5 | 建议 | 严格 IPv4：`ranking.is_valid_ip()`、`output.format_ip_port()`、`safety._LINE_RE` 与 `validate_txt` 均拒绝 IPv6；IPv6 暂不纳入当前六榜。 |
| 6 | 建议 | CSV 表头解析与完整性校验统一使用 `HEADER_ALIASES` / `REQUIRED_SEMANTIC_FIELDS`；`CsvData.resolved_fields` 记录实际匹配表头，中文/英文表头均能解析并通过完整性校验。 |
| 7 | 建议 | `tempfile.mkstemp()` 权限核查：确认最终 TXT 为 **0o600**，代码中无 `chmod` / umask 放宽；`safety.py` 文档明确预期 UID 1000 / GID 0（compose `user: "1000:0"`）及「其他用户不可读」的影响；**读取权限留待阶段 4.2 实测**，本阶段不放宽。 |
| 8 | 测试 | `app/main.py` 修正 T18，新增 R01~R18 共 18 项离线测试；`--simulate` 由 5 个场景扩展到 9 个。 |

## B.2 新增离线测试覆盖

`-dn` 参数等于配置 100；ratio/percent 丢包率边界（0 / 0.25 / 1 / 1.2 / 25 / 25% / NaN / Infinity / 负数 / N/A / 未知单位）；旧 CSV 遗留但本轮未生成新 CSV；本轮 CSV 不完整；本轮 CSV 时间戳陈旧；单榜渲染失败其余五榜仍更新；单榜写入失败其余五榜仍更新；IPv6 被 ranking/output/safety 全面拒绝；六榜为空 / 地区榜不足 5 / 全球榜不足 25；原子替换无临时文件残留 + 0o600 权限；目录级不生成 `merged.txt` / `global_top15.txt`；英文表头别名统一；测速异常时历史 CSV 与六旧 TXT 不变；本轮独立路径生成→归档→无残留；生产 `-o` 指向本轮路径；源码级确认逐榜独立渲染。

## B.3 明确未完成 / 留待后续阶段

1. **阶段 4.2（未授权）**：容器 Python 3.12 集成测试；0o600 最终 TXT 是否能被 EdgeTunnel / Web / GitHub 消费者读取；只读根文件系统与目录权限实测；非 root（UID 1000 / GID 0）运行验证。
2. **阶段 4.3（未授权）**：真实测速前参数与网络安全审计；`-dn 100` 的合理性、运行超时、Docker bridge 出口、不加入 Mihomo 网络、路由器透明代理状态（应用层代理变量为空**不能证明**透明代理不存在）。
3. **阶段 4.4（未授权，需用户明确授权）**：单次完整真实 CFST 测速；用真实 CSV 复核丢包率单位、普通 TCPing+下载模式是否稳定输出 Colo、下载速度 MB/s、有效下载数量与地区覆盖率；据此调整 `download_count`（100 只是初始测试值）。
4. **`data/result.json` 与 `data/last_run.json` 尚未落盘实现**：当前 `pipeline.run_once` 只返回运行状态字典，`output.render_run_status` 只生成 JSON 字符串；后续阶段需补齐写盘（含独立日志、`logs/` 归档）。
5. **地区映射仍未补全**：`regions.json` 只有 `SIN→SG`、`LAX→US`；HK/JP/KR 空列表，DEN 待确认、AMS/N/A 排除。禁止猜测，需真实样本经用户确认后加入。
6. **阶段 5~9 全部未执行**：正式六文件发布、GitHub Raw 订阅、EdgeTunnel 六订阅接入、每日三次定时与防重入、Server 酱微信推送。
7. **SSH 凭据**：建议用户尽快改密或改用公钥认证，并检查是否有其他服务复用同一密码；本轮未对 NAS 系统设置做任何变更。

## B.4 本轮安全边界（均为「未执行」）

真实网络请求 / CFST 测速 / 网络扫描 / 容器启动 / 镜像构建 / Cron 修改 / GitHub 上传 / EdgeTunnel 修改 —— **全部未执行**。`Dockerfile`、`compose.yaml`、`.dockerignore`、CFST 二进制与 6 份历史 `samples/*.csv`、`config/regions.json` 均未修改；`data/`、`logs/` 保持空目录，未生成任何正式订阅文件、编译产物或遗留本轮 CSV。
````
