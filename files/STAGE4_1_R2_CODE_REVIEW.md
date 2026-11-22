# 阶段 4.1-R2 代码审查报告（只读导出）

- 依据：`STAGE4_1-R1 综合问题清单与后续整改要求.md`（用户整理的三类问题清单）
- 本轮授权范围：**仅 P0-1 / P1-1 / P1-2 三项** + 对应离线测试 + 任务书更新；清单中「正式部署前必须完成的事项」一律未实施
- 来源：NAS `/share/Container/cf-ip-optimizer/` 已部署文件；下列源码逐字取自本地同哈希副本（NAS 与本地 SHA256 已双向复核一致）
- 测试输出全文：`STAGE4_1_R2_TEST_OUTPUT.txt`（497 行，含 65 项自测与 11 场景模拟）
- 代码块使用四反引号围栏，避免源码内三反引号字符串影响渲染

## 0 修改前后 SHA256 对照（7 个修改文件）

| 文件 | 大小 | 修改前 | 修改后 |
|---|---:|---|---|
| `app/__init__.py` | 680 B | `9f735c5f0e5697e800dea872cf3443168bbd1cdb64bc1b7d9fb2be0023164c17` | `b1e3d46372864cdbb7e7252c95e19fa3291afbb37702cb844573934bd83524e1` |
| `app/main.py` | 74090 B | `821ec0224a056f69d0a2fb5b7685960effe228ddf906a0653163b3a1f7dc443a` | `c252219792993cc878631621ee59db6016bbb37ba3a970acca425ff9c4615b62` |
| `app/cfst.py` | 19287 B | `76661d0d3cf4ace82db70e12dd8d209b5c173834e003fdc65940406a3a758484` | `7e9bfcf41e80f18ed2bd0379e07ff4bd9382685f9dbec97ef2d57694ed810860` |
| `app/output.py` | 6930 B | `ed3e303c16949fa418fa27fd9c49fa7416d58e75af1dd78922245c6025130896` | `c22b866a3ded9e4c5bb26c874a942f4bd0f788a4a4f452eff6ffb83b3605d473` |
| `app/safety.py` | 10292 B | `24a358b3a1754d9485621629c2825235a5de9f6c787ed7bf73b66723dc8f11e6` | `5ef487ae663f150448ab00a1c02aaa4c519ed856028f08949d97c9a9f4a90fa9` |
| `app/pipeline.py` | 17046 B | `cf97abde9fd1ca1f3742d82c4b3fada1cb43c4b750ce207a3dbb374bf30ca5ae` | `ad06af7dd3d10edafab548daa645622b6dd30b3f284433aa62dd8c7e4a78561e` |
| `docs/TASK_BOOK.md` | 37953 B | `ff68dc4d94916998e9741da95dc826575b16187e4ad4a486aa209ead5c719b46` | `aa63174b53c26e5851cfb13eb824351c0830ae091adf2ff7ed008d2d5bab1031` |

未修改文件（SHA256 前后一致，共 15 个）：

```
app/config.py                                  6a0db6b78c820548c5117214157dedea124d39ce5c6bae5a9aca0d1a21ffada2
app/ranking.py                                 8be5c3ef412634f5f42633c48821f02e21b61124665c72ac04ab09ec0df7552f
app/region.py                                  4ddb1f8c03e9a29ff8c3ac361e6921d64dc794905b21ca1f24f16db5465b78b1
config/settings.json                           750b9fedde2b1f4519f996007286b951482deaa54eb90d5a5ec64d3c5f0a00e0
config/regions.json                            998745250d900520000599da43b3c1f4ef59e92a077984295079b771e8d7f83a
Dockerfile                                     2df92118e23aeb94252527cf37a892de229fd65aa822be331871fbc6cb234b42
compose.yaml                                   e1b8a795073d189b07aa75e438c65299788591e74be6e7c855e5a2290a0f20b1
.dockerignore                                  75750ad633da57a4225051d8bec39322db408b2edf494b9053b8a91c519f4792
bin/cfst_linux_amd64.tar.gz                    c4c8fc76b4e1bf2bdb5ced8b765956d82dda7bc4eb59df5c04053f0f7db98d90
samples/phase2-colo-filter-sin-lax.csv         bb92287b95982df91b304f09de176e76e2634b462afaa69217cddb8e5f25039f
samples/phase2-download-108.csv                8bd9e10fc86dda0ede76593201b8f91dcef676ae43ff96e962db1f441d30abc8
samples/phase2-download-3ip.csv                2eb6b5e6b5edae01b090a333872092bd250705ad3d1a4db72bc4f52419773ada
samples/phase2-download-cloudflare-108.csv     1daf346d6a0e4f33dab1aed8bd1d95ad912d45f3092ee44ea267a1a1b807e0a7
samples/phase2-robots-104.csv                  0d6cc410ccc082b21fd9faf5bfdaaceb150873bb12bbf37040646caea00778eb
samples/phase2-robots-colo-sample.csv          b2327964fb0473715e68bf6cd67c86cbcd57754374d62aca5b68fdf73a867e6c
```

## 1 三项修正摘要


**P0-1 CSV 初始化失败即终止**：`prepare_run_csv()` 由返回 bool 改为返回
`RunCsvInit(ok, reason, pre_absent, started_ns, token, source)` 证据对象，fail-closed
（父目录缺失 / 残留清理失败 / 删除后仍存在 / 状态不稳定一律 `ok=False`）；
`run_once` 显式检查 `init.ok`，失败立即 return，**不调用 runner**，
`cfst_exit_code=None`、`failure_stage="csv_init"`、六榜全 skipped、
六个旧 TXT 与正式历史 CSV 字节不变、残留现场保留（`cleanup=False`）。
实测清理失败时 **CFST runner 调用次数 = 0**。

**P1-1 新鲜度不单独依赖 mtime**：`csv_is_fresh(path, init)` 强制消费本轮
`RunCsvInit`；生产路径主证据是「运行前确证目标一次性路径不存在」+ runner 退出码 0
+「运行后存在且非空」的存在性跃迁；mtime 降级为辅助校验（含 2s 容差），
并在 docstring 说明 NAS/网络文件系统时间戳粒度与时钟回拨风险。
`init` 非法 / `ok=False` / `pre_absent=False` 一律 fail-closed，
即使残留文件 mtime 很新也拒绝。`explicit_path_evidence()` 仅为离线测试显式
`csv_path` 构造 `source="test_explicit"` 非生产证据，生产恒走 `prepare_run_csv`。

**P1-2 两个状态 JSON 真正落盘**：`output.py` 用字段白名单构造
`result.json`（完整结果：含 CFST 命令、路径、初始化证据、六榜详情、警告）与
`last_run.json`（轻量状态：去掉命令/路径/警告，六榜精简为
`status/node_count/reason`）；`safety.publish_json_file()` 走
`mkstemp(0o600) → flush → fsync → 回读比对 → json.loads → 凭据标记扫描 → os.replace()`；
`pipeline` 阶段 E 在六榜发布与 CSV 归档之后独立写两个 JSON，
`status_files` 记录各自结果，`overall_status` 区分 success/partial/failed。
状态 JSON 使用**独立的** replace 注入通道，不复用 TXT 的 `replace_fn`，
故六个 TXT 的 `os.replace` 仍恰好 6 次。


## 2 修改后关键源码全文（6 个被修改的源码文件）


### app/cfst.py — 430 行，sha256=7e9bfcf41e80f18ed2bd0379e07ff4bd9382685f9dbec97ef2d57694ed810860

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

4.1-R2 修正（P0-1 / P1-1）：
  * prepare_run_csv() 改为返回 RunCsvInit 证据对象（ok / reason / pre_absent /
    started_ns / token / source），清理失败、父目录缺失、删除后仍存在一律 fail-closed；
    调用方必须检查 ok，失败即刻终止，不允许调用 CFST runner。
  * csv_is_fresh() 不再单独依赖 mtime：生产路径必须消费「运行前确证目标路径不存在」
    的前置证据，配合 runner 退出码 0 与「运行后存在且非空」构成完整证据链；
    mtime 降级为辅助合理性校验，并对时间戳粒度/文件系统行为给出说明。
  * 新增 explicit_path_evidence()：仅为离线测试的显式 csv_path 构造非生产证据，
    生产路径恒走 prepare_run_csv，二者由 source 字段区分。
"""

from __future__ import annotations

import csv
import io
import math
import os
import time
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
# 时间戳容差：仅作为【辅助】合理性校验，容忍文件系统时间戳粒度与
# 「测试预置 fixture」的毫秒级时间差。4.1-R2 起不再是判定本轮生成的依据：
# 主证据是 prepare_run_csv 的「运行前确证不存在」+ 运行后的存在性跃迁。
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
# 本轮 CSV 初始化证据与新鲜度（4.1-R1 新增；4.1-R2 按 P0-1 / P1-1 重写）
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RunCsvInit:
    """本轮 CSV 初始化证据对象。

    ok            是否初始化成功；False 时调用方【必须】终止本轮，不得调用 runner。
    reason        成功/失败原因，写入运行状态，便于区分「初始化失败」与「测速失败」。
    pre_absent    运行前是否已确证目标路径不存在（生产路径的新鲜度主证据）。
    started_ns    本轮时间基准，在确证不存在之后取（mtime 辅助校验用）。
    token         本轮随机 nonce，标识证据属于本轮，防止跨轮复用。
    source        "production"（一次性路径）| "test_explicit"（离线测试显式路径）。
    """

    ok: bool
    reason: str
    pre_absent: bool
    started_ns: int
    token: str
    source: str


def new_run_csv_path(formal_csv, run_id=None) -> Path:
    """在正式 CSV 同目录生成【本轮一次性】路径，与 data/result.csv 不重名。

    同目录保证后续 os.replace() 是同文件系统原子操作。
    路径含 UTC 时间戳 + pid + 8 位随机 nonce，外部无法预知，因此
    「运行前确证不存在 -> 运行后存在」即可证明文件由本轮 runner 创建。
    """
    formal = Path(formal_csv)
    rid = run_id or "%s-%d-%s" % (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"),
        os.getpid(), uuid.uuid4().hex[:8],
    )
    return formal.parent / ("%s%s.csv" % (RUN_CSV_PREFIX, rid))


def prepare_run_csv(path, *, unlink_fn=None) -> RunCsvInit:
    """运行前初始化本轮一次性 CSV 路径：清理残留并确证目标路径不存在。

    P0-1 关键语义 —— fail-closed：
      * 父目录不存在 -> ok=False（不擅自创建目录，避免在不预期位置写文件）；
      * 目标路径已存在且删除失败（权限 / I/O 错误）-> ok=False；
      * 删除后仍存在、或路径状态不稳定 -> ok=False；
      * 只有「父目录存在 + 目标路径确证不存在」才返回 ok=True / pre_absent=True。
    只操作本轮路径，绝不触碰正式 data/result.csv 或六个正式 TXT。

    unlink_fn 仅供离线测试注入删除故障，生产路径恒为 Path.unlink。
    """
    p = Path(path)
    token = uuid.uuid4().hex

    def _fail(reason: str) -> RunCsvInit:
        return RunCsvInit(False, reason, False, time.time_ns(), token, "production")

    if not p.parent.is_dir():
        return _fail("本轮 CSV 父目录不存在，拒绝继续测速: %s" % p.parent)
    try:
        existed = p.exists()
    except OSError as exc:
        return _fail("检查本轮 CSV 路径失败（%s）: %s" % (type(exc).__name__, exc))

    if existed:
        try:
            (unlink_fn or Path.unlink)(p)
        except OSError as exc:
            return _fail("清理本轮残留 CSV 失败（拒绝继续测速）: %s: %s" %
                         (type(exc).__name__, exc))
        # 二次确证：删除后仍存在同样 fail-closed，绝不带病继续测速
        if p.exists():
            return _fail("清理后本轮 CSV 路径仍存在，拒绝继续测速: %s" % p)
    elif p.exists():
        # 防御 TOCTOU 竞态：两次观测不一致
        return _fail("本轮 CSV 路径状态不稳定，拒绝继续测速: %s" % p)

    return RunCsvInit(True, "本轮 CSV 路径已确证为空", True,
                      time.time_ns(), token, "production")


def explicit_path_evidence(path) -> RunCsvInit:
    """离线测试专用：为显式注入的 csv_path 构造【非生产】证据。

    pipeline.run_once 仅在测试显式传入 csv_path 时调用本函数；生产路径恒走
    prepare_run_csv。test_explicit 没有「前置不存在」证据，因此 csv_is_fresh
    对它只使用 mtime 辅助判据，并在返回原因中明确标注为非生产路径。
    """
    return RunCsvInit(True, "离线测试显式路径（非生产）", False,
                      time.time_ns(), "test-explicit", "test_explicit")


def csv_is_fresh(path, init) -> tuple:
    """判断本轮 CSV 是否确由本次运行写出，返回 (bool, 原因)。

    P1-1：新鲜度【不再单独依赖 mtime】。生产路径的硬性证据链：

      1. init 必须是本轮 prepare_run_csv 返回的 RunCsvInit，且 ok=True；
      2. init.pre_absent=True —— 运行前已确证目标一次性路径不存在；
      3. CFST runner 退出码为 0（由 pipeline 在调用本函数前保证）；
      4. 运行后该路径存在且非空。

    由 2)+4) 的「不存在 -> 存在」跃迁即可证明文件是本轮创建的：一次性随机
    路径外部无法预知，残留旧文件在 prepare 阶段要么被删除、要么触发
    fail-closed 终止；因此通过 2) 的文件不可能是上一轮遗留。即使旧文件
    mtime 很新，只要初始化失败（ok=False）或缺少前置证据，一律拒绝。

    mtime 降级为【辅助】合理性校验，原因与文件系统行为说明：
      * 部分 NAS / 网络文件系统的时间戳粒度只有 1s 甚至更粗，mtime 可能
        落后于真实创建时刻；系统时钟回拨也会让新文件看起来「旧」；
      * 反过来，恶意或异常残留文件可以把 mtime 伪造成很新，因此 mtime 新
        【不能】证明是本轮生成；
      * 故 mtime 只用于剔除「明显早于本轮开始」的异常（含 2s 容差），
        不再作为通过与否的唯一依据；
      * 离线测试的显式 csv_path（source=test_explicit）没有前置不存在证据，
        保留 mtime 辅助判据以兼容既有离线 fixture，并明确标注非生产路径。
    """
    if not isinstance(init, RunCsvInit):
        return False, "缺少本轮 CSV 初始化证据（fail-closed，拒绝非本轮文件）"
    if not init.ok:
        return False, "本轮 CSV 初始化未成功: %s" % init.reason
    production = init.source == "production"
    if production and not init.pre_absent:
        return False, "生产路径缺少「运行前确证不存在」证据（fail-closed）"

    p = Path(path)
    if not p.is_file():
        return False, "本轮 CSV 未生成"
    st = p.stat()
    if st.st_size == 0:
        return False, "本轮 CSV 为空文件"
    if st.st_mtime_ns + FRESHNESS_TOLERANCE_NS < init.started_ns:
        return False, "本轮 CSV 时间戳早于本轮开始（辅助校验不通过）"
    if production:
        return True, ("新鲜（前置确证不存在 + runner 退出码 0 + 本轮路径新生成 + 非空；"
                      "mtime 仅辅助）")
    return True, "新鲜（离线测试显式路径：mtime 基准 + 非空；非生产路径）"


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


### app/pipeline.py — 368 行，sha256=ad06af7dd3d10edafab548daa645622b6dd30b3f284433aa62dd8c7e4a78561e

````python
"""一次完整 CFST 测速 -> 一份本轮 CSV -> 六个独立 TXT + 两个状态 JSON 的编排。

本阶段（4.1）只在临时目录里用「模拟 runner」离线运行，runner 默认指向
cfst.execute_cfst()，而后者在 4.1 直接拒绝，因此不存在触发真实测速的路径。

关键隔离语义：
  * CSV 初始化失败 / runner 失败 / 退出码非 0 / 本轮 CSV 未生成、不新鲜或不完整
        -> 六个文件全部 skipped，旧文件与历史 CSV 一个都不动；
  * 测速成功后，六个文件【逐榜】独立选取、独立渲染、独立校验、独立原子替换，
    单个榜单的渲染失败、校验失败或写入失败都不影响其他五个；
  * 测速成功但某地区无有效节点 -> 该文件更新为空文件（情况 A）；
  * 情况 B（生成/写入/校验异常）-> 只保留该文件上次成功版本；
  * 两个状态 JSON 在六个 TXT 之后独立落盘，任一失败都不影响已发布的 TXT。

4.1-R1 关键修正（ChatGPT 只读审查）：

1) CSV 本轮新鲜度
   - CFST 的 -o 不再指向正式 data/result.csv，而是指向同目录下
     【本轮一次性路径】 .cfst-run-<run_id>.csv；
   - 运行前清理该一次性路径；运行后要求文件存在、非空、新鲜且完整性校验通过，
     才允许发布六个 TXT；
   - 只有上述全部通过后，才把本轮 CSV 原子归档为 data/result.csv；
   - 本轮任何失败都只删除本轮临时 CSV，历史 data/result.csv 与六个旧 TXT 不变。

2) 六文件生成隔离
   - 发布循环前不再做「一次集体渲染」（旧版 render_all_boards / select_boards）；
   - 每个榜单在独立 try 内依次调用 ranking.select_board -> output.render_board
     -> safety.validate_txt -> safety.publish_one；
   - 最快节点计算单独 try，异常只记 warning，不阻断发布。

4.1-R2 关键修正（P0-1 / P1-1 / P1-2）：

3) CSV 初始化失败即刻终止（P0-1）
   - prepare_run_csv() 返回 RunCsvInit 证据对象，run_once 显式检查 ok；
   - 清理失败 / 父目录缺失 / 删除后仍存在 -> fail-closed：立即 return，
     【不调用 CFST runner】，六个 TXT 与正式历史 CSV 全部保持旧内容；
   - 状态中 csv_init_ok=False、failure_stage="csv_init"、failure_reason 明确，
     与「普通测速失败」区分，cfst_exit_code 保持 None。

4) 新鲜度证据链（P1-1）
   - csv_is_fresh 消费本轮 RunCsvInit：生产路径必须满足「运行前确证目标路径
     不存在」的前置证据，配合 runner 退出码 0 与运行后存在且非空，
     由「不存在 -> 存在」跃迁证明 CSV 为本轮生成；
   - mtime 降级为辅助合理性校验，不再单独决定新鲜度；
   - 即使残留旧文件 mtime 很新，初始化失败或前置证据缺失也一律拒绝。

5) 运行状态真正落盘（P1-2）
   - 六个 TXT 发布与 CSV 归档之后，把状态原子写入 data/result.json（完整结果）
     与 data/last_run.json（轻量状态）；
   - 两个 JSON 各自独立 publish_json_file，失败只记入 status 与报告，
     不破坏任何已发布的 TXT；
   - overall_status 区分 success / partial / failed。

测试注入参数（仅离线测试使用，生产路径一律为默认值）：
    csv_path                  本轮 CSV 路径覆盖；None 表示自动生成一次性路径
    formal_csv_path           历史正式 CSV 路径覆盖（默认 data/result.csv）
    render_overrides          {文件名: 异常实例或 callable} 注入单榜渲染失败
    validator_overrides       {文件名: callable} 注入单榜校验失败
    replace_overrides         {文件名: 异常实例} 注入单榜写入失败
    replace_fn                TXT 的 os.replace 监视器（不作用于 JSON）
    prepare_unlink_fn         注入本轮 CSV 清理失败（P0-1 测试）
    status_write_overrides    {JSON 文件名: 异常} 注入状态文件写入失败
    status_replace_overrides  {JSON 文件名: 异常} 注入状态文件替换失败
    status_replace_fn         JSON 的 os.replace 监视器
    archive_csv               是否归档本轮 CSV；None 表示仅自动路径才归档
    run_id                    固定本轮 id，便于离线测试可复现
"""

from __future__ import annotations

import os
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


def overall_status_of(status: dict) -> str:
    """总体状态：success / partial / failed（三者必须可区分）。

    failed   : 完整测速/CSV 初始化失败（六榜全 skipped），或六榜零更新；
    partial  : 测速成功但至少有一个榜单未更新；
    success  : 测速成功且六个榜单全部 updated。
    """
    if not status["measurement_success"]:
        return "failed"
    updated = [n for n in EXPECTED_RESULT_FILES
               if status["files"].get(n, {}).get("status") == "updated"]
    if len(updated) == len(EXPECTED_RESULT_FILES):
        return "success"
    return "partial" if updated else "failed"


def run_once(settings: dict, regions: dict, *, runner=None, csv_path=None,
             formal_csv_path=None, output_dir=None,
             validator_overrides=None, render_overrides=None,
             replace_overrides=None, replace_fn=None,
             prepare_unlink_fn=None,
             status_write_overrides=None, status_replace_overrides=None,
             status_replace_fn=None,
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
    status_write_overrides = status_write_overrides or {}
    status_replace_overrides = status_replace_overrides or {}
    run = runner or _default_runner

    status = {
        "run_time": now_iso or datetime.now(CST).isoformat(timespec="seconds"),
        "timezone": settings["timezone"],
        "run_mode": settings["run_mode"],
        "cfst_command": cfst.build_command(settings, run_csv),
        "run_csv_path": str(run_csv),
        "formal_csv_path": str(formal),
        "cfst_exit_code": None,
        "csv_init_ok": False,
        "csv_init_reason": None,
        "csv_init_source": None,
        "csv_init_pre_absent": False,
        "csv_fresh": False,
        "csv_complete": False,
        "csv_archived": False,
        "csv_total_rows": 0,
        "valid_ip_count": 0,
        "files": {},
        "failed_files": [],
        "skipped_files": [],
        "updated_files": [],
        "fastest_node": None,
        "measurement_success": False,
        "all_files_updated": False,
        "overall_status": "failed",
        "failure_stage": None,
        "failure_reason": None,
        "status_files": {},
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

    def _persist_status():
        """P1-2：把运行状态原子落盘为 result.json / last_run.json。

        两个状态文件在六个 TXT 之后独立写入；任一失败只记录结果，
        绝不向外抛、绝不破坏已经成功发布的 TXT。
        注：写入失败的状态文件无法记录自身的失败，故完整写入结果只保存在
        run_once 返回的 status["status_files"] 与后续运行日志中，不写进两个
        JSON 自身（避免自指不一致）。
        """
        try:
            status["updated_files"] = [
                n for n in EXPECTED_RESULT_FILES
                if status["files"].get(n, {}).get("status") == "updated"
            ]
            status["overall_status"] = overall_status_of(status)
            writes = {}
            for name, renderer in ((output.RESULT_JSON, output.render_result_json),
                                  (output.LAST_RUN_JSON, output.render_last_run_json)):
                try:
                    content = renderer(status)
                except Exception as exc:
                    writes[name] = {
                        "status": "failed", "size_bytes": None,
                        "reason": "状态渲染失败（%s）: %s" % (type(exc).__name__, exc),
                        "temp_file": None, "atomic_replace": False,
                    }
                    continue

                injected_write = status_write_overrides.get(name)
                write_fn = None
                if injected_write is not None:
                    err = (injected_write if isinstance(injected_write, BaseException)
                           else OSError(str(injected_write)))

                    def write_fn(_content, _err=err):
                        raise _err

                def do_replace(src, dst, _name=name):
                    injected = status_replace_overrides.get(_name)
                    if injected is not None:
                        raise (injected if isinstance(injected, BaseException)
                               else OSError(str(injected)))
                    base = status_replace_fn or os.replace
                    return base(src, dst)

                writes[name] = safety.publish_json_file(
                    out_dir / name, content,
                    replace_fn=do_replace, write_fn=write_fn)
            status["status_files"] = writes
        except Exception as exc:
            status["warnings"].append(
                "状态 JSON 持久化异常（不影响六个 TXT）: %s: %s" %
                (type(exc).__name__, exc))

    def _abort(reason: str, stage: str = "measurement", *, cleanup=True) -> dict:
        # csv_init 阶段保留残留现场，便于审计确认旧文件确实没有被误用；
        # 其余失败阶段清理本轮一次性路径（绝不触碰正式历史 CSV 与六个 TXT）。
        if cleanup:
            _cleanup_run_csv()
        status["files"] = {name: _skipped(reason) for name in EXPECTED_RESULT_FILES}
        status["skipped_files"] = list(EXPECTED_RESULT_FILES)
        status["failure_reason"] = reason
        status["failure_stage"] = stage
        _persist_status()
        return status

    # --- 阶段 A0：本轮 CSV 初始化（P0-1：失败立即终止，runner 调用次数必须为 0）---
    if auto_csv:
        init = cfst.prepare_run_csv(run_csv, unlink_fn=prepare_unlink_fn)
    else:
        init = cfst.explicit_path_evidence(run_csv)
    status["csv_init_ok"] = init.ok
    status["csv_init_reason"] = init.reason
    status["csv_init_source"] = init.source
    status["csv_init_pre_absent"] = init.pre_absent
    if not init.ok:
        return _abort("CSV 初始化失败: %s" % init.reason,
                      stage="csv_init", cleanup=False)

    # --- 阶段 A：一次完整测速；任何失败都六个文件全部不更新 ---
    try:
        exit_code = run(status["cfst_command"], run_csv, settings["cfst_timeout_sec"])
    except Exception as exc:
        return _abort("CFST 执行异常（%s）: %s" % (type(exc).__name__, exc),
                      stage="cfst_run")
    status["cfst_exit_code"] = exit_code
    if exit_code != 0:
        return _abort("CFST 退出码非 0 (%s)，完整测速失败" % exit_code,
                      stage="cfst_run")

    # P1-1：新鲜度必须消费本轮初始化证据，不再只看 started_ns/mtime
    fresh, fresh_reason = cfst.csv_is_fresh(run_csv, init)
    status["csv_fresh"] = fresh
    if not fresh:
        return _abort("本轮 CSV 新鲜度校验失败: %s" % fresh_reason,
                      stage="csv_fresh")

    complete, reason, csv_data = cfst.validate_csv_completeness(run_csv)
    status["csv_complete"] = complete
    if not complete:
        return _abort("CSV 不完整: %s" % reason, stage="csv_complete")

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
        return _abort("CSV 解析/排序异常（%s）: %s" % (type(exc).__name__, exc),
                      stage="parse")

    # 最快节点只是审计信息，单独 try，异常绝不阻断六个榜单发布
    try:
        global_board = ranking.select_board(GLOBAL_FILE, ranked, settings)
        status["fastest_node"] = output.fastest_node_of(
            {GLOBAL_FILE: global_board}, settings, names)
    except Exception as exc:
        status["warnings"].append("最快节点计算失败（不影响发布）: %s" % exc)

    def _make_replace(name):
        """把单榜写入故障注入包装进 TXT 的 os.replace 监视器。"""
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

    # --- 阶段 E：两个状态 JSON 独立落盘（P1-2；失败不影响六个 TXT）---
    _persist_status()
    return status
````


### app/output.py — 164 行，sha256=c22b866a3ded9e4c5bb26c874a942f4bd0f788a4a4f452eff6ffb83b3605d473

````python
"""TXT 节点渲染与运行状态渲染（纯函数，只返回字符串）。

节点行格式: IP:443#地区代码-英文地区名称-Colo-整数延迟ms
  已知地区: 172.64.150.190:443#SG-Singapore-SIN-92ms
  未知 Colo: 172.64.150.190:443#UNKNOWN-Unknown-DEN-92ms
  N/A 或空 Colo: 172.64.150.190:443#UNKNOWN-Unknown-NA-92ms
下载速度只参与排名，不写入备注；延迟四舍五入为整数毫秒（不使用银行家舍入）。
全球榜允许未知节点；地区榜不允许出现 UNKNOWN。
正式文件的写盘与原子替换由 safety.py 负责。

4.1-R1：当前阶段严格 IPv4，format_ip_port 遇到 IPv6 直接抛错；
render_all_boards 仅供离线对照/测试，生产发布路径由 pipeline 逐榜调用 render_board。

4.1-R2（P1-2）：新增 result.json / last_run.json 的内容构造。
两者【保存不同数据】：
  * result.json  = 本次运行的完整结果（含 CFST 命令、本轮/历史 CSV 路径、
    初始化证据、六榜逐文件详情、警告、总体状态），用于审计与追溯；
  * last_run.json = 最近一次运行的轻量状态（去掉命令/路径/警告，六榜精简为
    status/node_count/reason 三项），供监控、调度与推送读取。
两个 payload 都采用【字段白名单】从 status 中挑选，绝不整体 dump，
从源头杜绝 Token / SendKey / 密码 / 环境变量等凭据进入状态文件；
safety.publish_json_file 落盘前再做一次敏感标记扫描与 JSON 回读校验。
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


# --------------------------------------------------------------------------
# 运行状态 JSON（4.1-R2 / P1-2）
# --------------------------------------------------------------------------
RESULT_JSON = "result.json"
LAST_RUN_JSON = "last_run.json"
STATUS_JSON_FILES = (RESULT_JSON, LAST_RUN_JSON)

# 字段白名单：只从 status 中挑选这些键，绝不整体 dump status。
# 任何 Token / SendKey / 密码 / 环境变量都不在白名单内，从源头隔离凭据。
_FULL_FIELDS = (
    "run_time", "timezone", "run_mode", "cfst_command", "run_csv_path",
    "formal_csv_path", "cfst_exit_code", "csv_init_source", "csv_init_ok",
    "csv_init_reason", "csv_init_pre_absent", "csv_fresh", "csv_complete",
    "csv_archived", "csv_total_rows", "valid_ip_count", "files", "failed_files",
    "skipped_files", "updated_files", "fastest_node", "measurement_success",
    "all_files_updated", "overall_status", "failure_stage", "failure_reason",
    "warnings", "speed_unit",
)
_LIGHT_FIELDS = (
    "run_time", "timezone", "run_mode", "overall_status", "failure_stage",
    "failure_reason", "measurement_success", "all_files_updated",
    "cfst_exit_code", "csv_init_ok", "csv_fresh", "csv_complete",
    "csv_total_rows", "valid_ip_count", "fastest_node", "failed_files",
    "skipped_files", "updated_files", "speed_unit",
)


def render_run_status(info: dict) -> str:
    """运行状态 JSON。禁止写入 Token、密码、完整环境变量等敏感信息。"""
    return json.dumps(info, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _light_files(files: dict) -> dict:
    """轻量版只保留每个榜单的状态、节点数与失败原因。"""
    return {
        name: {
            "status": info.get("status"),
            "node_count": info.get("node_count"),
            "reason": info.get("reason"),
        }
        for name, info in files.items()
    }


def build_result_payload(status: dict) -> dict:
    """result.json：本次运行的【完整结果】（含命令、路径、六榜详情与警告）。"""
    payload = {k: status[k] for k in _FULL_FIELDS if k in status}
    payload["status_schema_version"] = 1
    payload["document_type"] = "result"
    payload["description"] = "本次运行的完整结果，用于审计与历史追溯"
    return payload


def build_last_run_payload(status: dict) -> dict:
    """last_run.json：最近一次运行的【轻量状态】（去掉命令/路径/警告）。"""
    payload = {k: status[k] for k in _LIGHT_FIELDS if k in status}
    payload["files"] = _light_files(status.get("files", {}))
    payload["status_schema_version"] = 1
    payload["document_type"] = "last_run"
    payload["description"] = "最近一次运行的轻量状态，供监控 / 调度 / 推送读取"
    return payload


def render_result_json(status: dict) -> str:
    return render_run_status(build_result_payload(status))


def render_last_run_json(status: dict) -> str:
    return render_run_status(build_last_run_payload(status))


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


### app/safety.py — 220 行，sha256=5ef487ae663f150448ab00a1c02aaa4c519ed856028f08949d97c9a9f4a90fa9

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

4.1-R2（P1-2）新增 publish_json_file()：为 data/result.json 与
data/last_run.json 提供单文件原子落盘。与 TXT 完全解耦：
  * 同目录 mkstemp(0o600) -> 写完整内容 -> flush -> fsync -> 回读文本比对
    -> json.loads 结构校验 -> 敏感标记扫描 -> os.replace()；
  * 任何异常都删除临时文件、保留该 JSON 的旧正式版本，且绝不向外抛，
    因此状态文件写入/替换失败不会破坏已经成功发布的六个 TXT；
  * write_fn / replace_fn 仅供离线测试注入「写入失败」「替换失败」。
"""

from __future__ import annotations

import ipaddress
import json
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
# 凭据标记：TXT 与 JSON 状态文件共用同一套扫描规则
_SECRET_MARKERS = ("ghp_", "github_pat_", "Authorization:", "Bearer ",
                   "password=", "passwd=", "token=", "api_key", "private_key",
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


def publish_json_file(target, content: str, *, replace_fn=None,
                      write_fn=None) -> dict:
    """单文件原子写入 JSON 状态文件（4.1-R2 / P1-2）。

    流程：同目录 mkstemp(0o600) -> 写完整内容 -> flush -> fsync ->
    回读文本逐字节比对 -> json.loads 结构校验 -> 凭据标记扫描 -> os.replace()。
    任何异常都删除临时文件、保留该 JSON 的旧正式版本，且不向外抛出，
    由调用方把失败结果记入运行状态（状态文件失败与六个 TXT 完全隔离）。

    write_fn(content) / replace_fn(src, dst) 仅供离线测试注入
    「写入失败」「替换失败」；生产路径恒为默认值。
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    do_replace = replace_fn or os.replace
    fd, tmp = tempfile.mkstemp(prefix=".tmp-%s-" % target.name,
                               suffix=".part", dir=str(target.parent))
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            if write_fn is not None:
                write_fn(content)          # 注入点；抛异常时 with 仍会关闭 fd
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        raw = tmp_path.read_text(encoding="utf-8")
        if raw != content:
            raise SafetyError("%s 临时文件回读不一致" % target.name)
        json.loads(raw)                    # 必须是合法 JSON
        if any(marker in raw for marker in _SECRET_MARKERS):
            raise SafetyError("%s 疑似包含凭据内容，拒绝发布" % target.name)
        do_replace(str(tmp_path), str(target))
        return {
            "status": "updated",
            "size_bytes": len(content.encode("utf-8")),
            "reason": None,
            "temp_file": tmp_path.name,
            "atomic_replace": True,
        }
    except Exception as exc:  # 状态文件失败不得影响六个 TXT
        try:
            tmp_path.unlink()
        except OSError:
            pass
        return {
            "status": "failed",
            "size_bytes": None,
            "reason": "%s: %s" % (type(exc).__name__, exc),
            "temp_file": tmp_path.name,
            "atomic_replace": False,
        }


def leftover_temp_files(directory) -> list:
    p = Path(directory)
    return sorted(x.name for x in p.glob(".tmp-*.part")) if p.is_dir() else []
````


### app/__init__.py — 18 行，sha256=b1e3d46372864cdbb7e7252c95e19fa3291afbb37702cb844573934bd83524e1

````python
"""cf-ip-optimizer 自动测速程序（阶段 4.1 修订版：单轮测速 / 六榜独立发布）。

本阶段只做代码架构修订与离线测试：
不执行真实测速、不发网络请求、不启动容器、不创建 Cron、不上传 GitHub、
不修改 EdgeTunnel、不更新正式订阅文件。

已废弃的旧两轮逻辑（HTTPing 初筛 + 按地区分别下载）不得再出现：
任何模块都不得构造第二条 CFST 命令，也不得读取第二轮 Colo 做分类。
"""

from __future__ import annotations

__version__ = "4.1.3-r2"
__stage__ = "4.1-R2"

__all__ = [
    "config", "cfst", "region", "ranking", "output", "safety", "pipeline", "main",
]
````


### app/main.py — 1419 行，sha256=c252219792993cc878631621ee59db6016bbb37ba3a970acca425ff9c4615b62

````python
"""主流程入口（阶段 4.1-R2）。

可用命令：
  --check-config   加载并校验两份配置，打印唯一一条 CFST 命令（只构造，不执行）
  --self-test      任务书 28 项 + 4.1-R1 新增 18 项 + 4.1-R2 新增 N 项，
                   含网络守卫；零真实测速、零真实网络请求
  --simulate       在临时目录用模拟 CSV 演示六榜生成 / 单文件失败 / 完整测速失败 /
                   空榜 / 原子替换 / CSV 新鲜度 / CSV 初始化失败 /
                   状态 JSON 落盘与失败隔离等 11 个场景，不写 NAS 正式订阅文件
  --version

--run 在阶段 4.1 明确拒绝（exit 2）；真实测速须等阶段 4.4 用户授权。
"""

from __future__ import annotations

import argparse
import json
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
    print("  权限提示: mkstemp 生成 0o600 的最终 TXT / JSON（UID 1000 / GID 0 预期），")
    print("           本阶段不放宽权限，读取权限留待阶段 4.2 实测。")
    print("  CSV 初始化: R2 起 prepare_run_csv 返回 RunCsvInit 证据；清理失败/父目录缺失")
    print("           /删除后仍存在一律 fail-closed，立即终止且不调用 CFST runner。")
    print("  新鲜度    : 生产路径要求「运行前确证不存在 + 本轮新生成」，mtime 仅辅助。")
    print("  状态 JSON : data/result.json（完整结果）与 data/last_run.json（轻量状态），")
    print("           各自临时文件 + fsync + 回读 JSON 校验 + os.replace() 原子替换；")
    print("           写入失败不影响六个 TXT；两者字段不同，均不含凭据。")
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

        check("R12", "目录中不生成 merged.txt / global_top15.txt；仅六 TXT + 两状态 JSON",
              lambda: not (out11 / "merged.txt").exists()
              and not (out11 / "global_top15.txt").exists()
              and sorted(x.name for x in out11.iterdir())
              == sorted(tuple(EXPECTED_RESULT_FILES) + output.STATUS_JSON_FILES)
              and json.loads((out11 / output.RESULT_JSON).read_text(encoding="utf-8"))["document_type"] == "result"
              and json.loads((out11 / output.LAST_RUN_JSON).read_text(encoding="utf-8"))["document_type"] == "last_run")

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

        # ===== 4.1-R2 新增 N01~N14：P0-1 / P1-1 / P1-2 =====
        # N01 P0-1 主场景：本轮一次性路径残留一个 mtime 很新的旧 CSV，
        #      清理因权限失败 -> 必须立即终止，runner 调用 0 次。
        formal_n1 = base / "n1-history.csv"
        _write_text(formal_n1, "N1-HISTORY-KEEP\n")
        out_n1 = _prep_run_dir(base, "n1")
        old_n1 = _old_bytes(out_n1)
        residual = cfst.new_run_csv_path(formal_n1, run_id="r2-n1")
        _write_text(residual, fixture)
        now_ns1 = time.time_ns()
        os.utime(residual, ns=(now_ns1, now_ns1))  # 旧文件 mtime 落在允许时间范围内
        n1_calls = []

        def _runner_n1(command, csv_path, timeout_sec):
            n1_calls.append(1)
            return 0

        def _unlink_denied(p):
            raise OSError("注入：本轮 CSV 清理权限错误")

        st_n1 = pipeline.run_once(
            settings, regions, runner=_runner_n1,
            formal_csv_path=formal_n1, output_dir=out_n1, run_id="r2-n1",
            prepare_unlink_fn=_unlink_denied)
        check("N01", "P0-1 初始化失败即终止：runner 0 次 / 六 TXT 与历史 CSV 不变 / 状态明确",
              lambda: len(n1_calls) == 0
              and st_n1["csv_init_ok"] is False
              and st_n1["failure_stage"] == "csv_init"
              and "CSV 初始化失败" in st_n1["failure_reason"]
              and "清理" in st_n1["csv_init_reason"]
              and st_n1["cfst_exit_code"] is None
              and st_n1["csv_fresh"] is False
              and st_n1["measurement_success"] is False
              and st_n1["overall_status"] == "failed"
              and st_n1["csv_init_source"] == "production"
              and all(st_n1["files"][n]["status"] == "skipped" for n in EXPECTED_RESULT_FILES)
              and all((out_n1 / n).read_bytes() == old_n1[n] for n in EXPECTED_RESULT_FILES)
              and formal_n1.read_text(encoding="utf-8") == "N1-HISTORY-KEEP\n"
              and residual.exists())  # fail-closed 保留现场，旧文件未被误用

        # N02 P0-1 对照：初始化成功 -> runner 恰好 1 次，前置不存在证据成立
        formal_n2 = base / "n2-history.csv"
        _write_text(formal_n2, "OLD-N2\n")
        out_n2 = _prep_run_dir(base, "n2")
        n2_calls = []

        def _runner_n2(command, csv_path, timeout_sec):
            n2_calls.append(1)
            _write_text(Path(csv_path), fixture)
            return 0

        st_n2 = pipeline.run_once(settings, regions, runner=_runner_n2,
                                  formal_csv_path=formal_n2, output_dir=out_n2,
                                  run_id="r2-n2")
        check("N02", "P0-1 对照：初始化成功 -> runner 1 次 / 前置确证不存在 / 归档成功",
              lambda: len(n2_calls) == 1
              and st_n2["csv_init_ok"] is True
              and st_n2["csv_init_pre_absent"] is True
              and st_n2["csv_init_source"] == "production"
              and st_n2["csv_fresh"] is True
              and st_n2["csv_archived"] is True
              and st_n2["overall_status"] == "success"
              and not Path(st_n2["run_csv_path"]).exists())

        # N03 prepare_run_csv 四态返回值语义
        p_n3 = base / "n3-clean.csv"
        init_clean = cfst.prepare_run_csv(p_n3)
        _write_text(p_n3, "STALE\n")
        init_removed = cfst.prepare_run_csv(p_n3)
        removed_gone = not p_n3.exists()   # 立即取快照，避免下面重建文件影响断言
        _write_text(p_n3, "STALE-AGAIN\n")
        init_denied = cfst.prepare_run_csv(p_n3, unlink_fn=_unlink_denied)
        init_noparent = cfst.prepare_run_csv(base / "no_such_dir_xyz" / "x.csv")
        check("N03", "prepare_run_csv 返回证据：干净/已清理 -> ok；清理失败/父目录缺失 -> fail-closed",
              lambda: isinstance(init_clean, cfst.RunCsvInit)
              and init_clean.ok and init_clean.pre_absent and init_clean.source == "production"
              and init_removed.ok and init_removed.pre_absent and removed_gone
              and (not init_denied.ok) and (not init_denied.pre_absent)
              and "清理" in init_denied.reason
              and (not init_noparent.ok) and "父目录" in init_noparent.reason)

        # N04 P1-1：mtime 很新也不能单独证明新鲜，必须消费本轮证据
        now_ns4 = time.time_ns()
        os.utime(residual, ns=(now_ns4, now_ns4))
        fresh_none = cfst.csv_is_fresh(residual, None)
        fresh_bad = cfst.csv_is_fresh(residual, init_denied)
        evidence_no_pre = cfst.RunCsvInit(True, "ok", False, now_ns4, "t", "production")
        fresh_no_pre = cfst.csv_is_fresh(residual, evidence_no_pre)
        evidence_ok = cfst.RunCsvInit(True, "ok", True, now_ns4, "t", "production")
        fresh_ok = cfst.csv_is_fresh(residual, evidence_ok)
        check("N04", "P1-1 新鲜度不单独依赖 mtime：无证据/初始化失败/缺前置证据一律拒绝",
              lambda: fresh_none[0] is False
              and fresh_bad[0] is False
              and fresh_no_pre[0] is False
              and fresh_ok[0] is True
              and "前置确证不存在" in fresh_ok[1]
              and "mtime 仅辅助" in fresh_ok[1]
              and "fail-closed" in fresh_no_pre[1])

        # N05 P1-1 端到端：auto 路径 runner 退出码 0 但未写 CSV -> 拒绝发布
        formal_n5 = base / "n5-history.csv"
        _write_text(formal_n5, "N5-KEEP\n")
        out_n5 = _prep_run_dir(base, "n5")
        old_n5 = _old_bytes(out_n5)
        st_n5 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                  formal_csv_path=formal_n5, output_dir=out_n5,
                                  run_id="r2-n5")
        check("N05", "P1-1 auto 路径：退出码 0 但未生成 CSV -> 新鲜度拒绝，六 TXT 与历史 CSV 不变",
              lambda: st_n5["csv_init_ok"] is True
              and st_n5["cfst_exit_code"] == 0
              and st_n5["csv_fresh"] is False
              and st_n5["failure_stage"] == "csv_fresh"
              and all((out_n5 / n).read_bytes() == old_n5[n] for n in EXPECTED_RESULT_FILES)
              and formal_n5.read_text(encoding="utf-8") == "N5-KEEP\n")

        # N06 P1-2：两个状态 JSON 正常落盘、字段齐全、两者内容不同
        csv_n6 = base / "n6.csv"
        _write_fixture(csv_n6)
        out_n6 = _prep_run_dir(base, "n6")
        st_n6 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                  csv_path=csv_n6, output_dir=out_n6)
        full_n6 = json.loads((out_n6 / output.RESULT_JSON).read_text(encoding="utf-8"))
        light_n6 = json.loads((out_n6 / output.LAST_RUN_JSON).read_text(encoding="utf-8"))
        required = ("run_time", "timezone", "run_mode", "cfst_exit_code", "csv_fresh",
                    "csv_complete", "csv_total_rows", "valid_ip_count", "fastest_node",
                    "files", "failed_files", "overall_status")
        check("N06", "P1-2 两状态 JSON 合法落盘、必需字段齐全、完整版与轻量版内容不同",
              lambda: all(k in full_n6 and k in light_n6 for k in required)
              and full_n6["document_type"] == "result"
              and light_n6["document_type"] == "last_run"
              and "cfst_command" in full_n6 and "cfst_command" not in light_n6
              and "warnings" in full_n6 and "warnings" not in light_n6
              and len(full_n6["files"]) == 6 and len(light_n6["files"]) == 6
              and set(light_n6["files"]["SG.txt"]) == {"status", "node_count", "reason"}
              and st_n6["overall_status"] == "success"
              and all(st_n6["status_files"][n]["status"] == "updated"
                      for n in output.STATUS_JSON_FILES))

        # N07 P1-2：两个 JSON 各自同目录临时文件 + os.replace()，无残留
        csv_n7 = base / "n7.csv"
        _write_fixture(csv_n7)
        out_n7 = _prep_run_dir(base, "n7")
        json_calls = []

        def _json_spy(src, dst):
            json_calls.append((Path(src).name, Path(src).parent == Path(dst).parent))
            return real_replace(src, dst)

        st_n7 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                  csv_path=csv_n7, output_dir=out_n7,
                                  status_replace_fn=_json_spy)
        check("N07", "P1-2 两 JSON 各经临时文件 + os.replace() 原子替换，无临时残留",
              lambda: len(json_calls) == 2
              and all(same and tmp.startswith(".tmp-") and tmp.endswith(".part")
                      for tmp, same in json_calls)
              and all(st_n7["status_files"][n]["atomic_replace"] is True
                      for n in output.STATUS_JSON_FILES)
              and safety.leftover_temp_files(out_n7) == [])

        # N08 P1-2：JSON 写入失败隔离
        out_n8 = _prep_run_dir(base, "n8")
        st_n8 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_n6, output_dir=out_n8,
            status_write_overrides={output.RESULT_JSON: OSError("注入：JSON 写入失败")})
        check("N08", "P1-2 JSON 写入失败：该文件 failed / 另一 JSON 仍更新 / 六榜照常",
              lambda: st_n8["status_files"][output.RESULT_JSON]["status"] == "failed"
              and st_n8["status_files"][output.LAST_RUN_JSON]["status"] == "updated"
              and not (out_n8 / output.RESULT_JSON).exists()
              and (out_n8 / output.LAST_RUN_JSON).exists()
              and all(st_n8["files"][n]["status"] == "updated" for n in EXPECTED_RESULT_FILES)
              and safety.leftover_temp_files(out_n8) == [])

        # N09 P1-2：JSON 替换失败 -> 旧版本字节保留，六 TXT 不受影响
        out_n9 = _prep_run_dir(base, "n9")
        (out_n9 / output.RESULT_JSON).write_text("OLD-RESULT-JSON\n", encoding="utf-8")
        (out_n9 / output.LAST_RUN_JSON).write_text("OLD-LAST-RUN-JSON\n", encoding="utf-8")
        st_n9 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_n6, output_dir=out_n9,
            status_replace_overrides={output.RESULT_JSON: OSError("注入：JSON 替换失败")})
        check("N09", "P1-2 JSON 替换失败：旧版本字节保留 / 六 TXT 仍全部更新 / 无临时残留",
              lambda: (out_n9 / output.RESULT_JSON).read_text(encoding="utf-8")
              == "OLD-RESULT-JSON\n"
              and (out_n9 / output.LAST_RUN_JSON).read_text(encoding="utf-8")
              != "OLD-LAST-RUN-JSON\n"
              and st_n9["status_files"][output.RESULT_JSON]["status"] == "failed"
              and all(st_n9["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES)
              and safety.leftover_temp_files(out_n9) == [])

        # N10 P1-2：两个 JSON 不含任何凭据
        banned = ("ghp_", "github_pat_", "Authorization", "Bearer ", "password=",
                  "passwd=", "token=", "api_key", "private_key", "SendKey", "SCT")
        n10_text = ((out_n6 / output.RESULT_JSON).read_text(encoding="utf-8")
                    + (out_n6 / output.LAST_RUN_JSON).read_text(encoding="utf-8"))
        check("N10", "P1-2 两个状态 JSON 不含 Token / SendKey / 密码 / 凭据标记",
              lambda: all(b not in n10_text for b in banned))

        # N11 P1-2：success / partial / failed 三态可区分，两个 JSON 一致
        out_n11 = _prep_run_dir(base, "n11")
        st_n11 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_n6, output_dir=out_n11,
            validator_overrides={"SG.txt": lambda t: (_ for _ in ()).throw(
                safety.SafetyError("注入：SG 校验失败"))})
        light_n11 = json.loads((out_n11 / output.LAST_RUN_JSON).read_text(encoding="utf-8"))
        out_n11b = _prep_run_dir(base, "n11b")
        st_n11b = pipeline.run_once(settings, regions, runner=lambda c, p, t: 1,
                                    csv_path=csv_n6, output_dir=out_n11b)
        light_n11b = json.loads((out_n11b / output.LAST_RUN_JSON).read_text(encoding="utf-8"))
        check("N11", "P1-2 success / partial / failed 三态可区分且状态文件记录一致",
              lambda: st_n6["overall_status"] == "success"
              and st_n11["overall_status"] == "partial"
              and light_n11["overall_status"] == "partial"
              and len(st_n11["updated_files"]) == 5
              and st_n11b["overall_status"] == "failed"
              and light_n11b["overall_status"] == "failed"
              and light_n11b["failure_reason"] is not None
              and st_n11b["failure_stage"] == "cfst_run")

        # N12 P0-1：初始化失败也落盘状态，且明确区分于普通测速失败
        light_n1 = json.loads((out_n1 / output.LAST_RUN_JSON).read_text(encoding="utf-8"))
        full_n1 = json.loads((out_n1 / output.RESULT_JSON).read_text(encoding="utf-8"))
        check("N12", "P0-1 初始化失败写入状态 JSON：failure_stage=csv_init，不误记为测速失败",
              lambda: light_n1["overall_status"] == "failed"
              and light_n1["csv_init_ok"] is False
              and "CSV 初始化失败" in (light_n1.get("failure_reason") or "")
              and full_n1["failure_stage"] == "csv_init"
              and full_n1["cfst_exit_code"] is None)

        # N13 源码级：确认三处关键实现真实存在
        pipe_src = (APP_DIR / "pipeline.py").read_text(encoding="utf-8")
        cfst_src = (APP_DIR / "cfst.py").read_text(encoding="utf-8")
        safety_src = (APP_DIR / "safety.py").read_text(encoding="utf-8")
        check("N13", "源码级：检查 init.ok fail-closed / 新鲜度消费证据 / 两 JSON 原子落盘",
              lambda: "if not init.ok" in pipe_src
              and "stage=\"csv_init\", cleanup=False" in pipe_src
              and "csv_is_fresh(run_csv, init)" in pipe_src
              and "publish_json_file(" in pipe_src
              and "render_result_json" in pipe_src
              and "isinstance(init, RunCsvInit)" in cfst_src
              and "pre_absent" in cfst_src
              and "def publish_json_file(" in safety_src
              and "json.loads(raw)" in safety_src)

        # N14 回归：TXT 的 os.replace 仍恰好 6 次，JSON 写入不干扰 TXT 监视器
        out_n14 = _prep_run_dir(base, "n14")
        txt_calls = []

        def _txt_spy(src, dst):
            txt_calls.append((src, dst))
            return real_replace(src, dst)

        st_n14 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                   csv_path=csv_n6, output_dir=out_n14,
                                   replace_fn=_txt_spy)
        check("N14", "回归：TXT 原子替换仍恰好 6 次，状态 JSON 不干扰 TXT 发布链路",
              lambda: len(txt_calls) == 6
              and all(st_n14["files"][n]["atomic_replace"] is True
                      for n in EXPECTED_RESULT_FILES)
              and all(st_n14["status_files"][n]["status"] == "updated"
                      for n in output.STATUS_JSON_FILES))

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

    print("=== 阶段 %s 离线必测：任务书 28 项 + R1 新增 18 项 + R2 新增 14 项 ===" % __stage__)
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
        print("  (六个 TXT + R2 新增 result.json / last_run.json 两个状态文件)")
        print("两个状态文件: %s" % {
            n: (out1 / n).stat().st_size for n in output.STATUS_JSON_FILES})
        print("merged.txt 存在? %s" % (out1 / "merged.txt").exists())
        print("os.replace 调用次数(TXT)=%d，临时文件残留=%s" %
              (len(calls), safety.leftover_temp_files(out1)))
        print("[场景 1] 六文件全部独立更新=%s  overall_status=%s" %
              (st1["all_files_updated"], st1["overall_status"]))

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
        print("  调用次数(TXT)=%d  临时文件残留=%s  目录=%s" %
              (len(replace_log), safety.leftover_temp_files(out5),
               sorted(x.name for x in out5.iterdir())))
        print("  (状态 JSON 使用独立的 os.replace 通道，不计入上面 6 次 TXT 替换)")
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

        # 场景 10：CSV 初始化失败 fail-closed（P0-1）
        print("\n----- 场景 10：CSV 初始化失败 fail-closed（P0-1）-----")
        formal10 = base / "result10.csv"
        _write_text(formal10, "S10-HISTORY-KEEP\n")
        out10 = _prep_run_dir(base, "s10")
        old10 = _old_bytes(out10)
        residual10 = cfst.new_run_csv_path(formal10, run_id="sim-s10")
        _write_text(residual10, fixture)
        now10 = time.time_ns()
        os.utime(residual10, ns=(now10, now10))  # 旧文件 mtime 落在允许时间范围内
        n10_calls = []

        def _runner10(c, p, t):
            n10_calls.append(1)
            return 0

        def _unlink_denied10(p):
            raise OSError("注入：清理权限错误")

        st10 = pipeline.run_once(settings, regions, runner=_runner10,
                                 formal_csv_path=formal10, output_dir=out10,
                                 run_id="sim-s10", prepare_unlink_fn=_unlink_denied10)
        print("  预置残留 CSV(mtime 很新): %s" % residual10.name)
        print("  CFST runner 调用次数=%d  csv_init_ok=%s  failure_stage=%s" %
              (len(n10_calls), st10["csv_init_ok"], st10["failure_stage"]))
        print("  failure_reason=%s" % st10["failure_reason"])
        print("  cfst_exit_code=%s  csv_fresh=%s  measurement_success=%s  overall=%s" %
              (st10["cfst_exit_code"], st10["csv_fresh"],
               st10["measurement_success"], st10["overall_status"]))
        print("  六个旧 TXT 全部保持旧内容=%s  正式历史 CSV 未变=%s" %
              (all((out10 / n).read_bytes() == old10[n] for n in EXPECTED_RESULT_FILES),
               formal10.read_text(encoding="utf-8") == "S10-HISTORY-KEEP\n"))
        print("  残留现场保留(未被误用/未擅自删)=%s  六榜状态=%s" %
              (residual10.exists(),
               {n: st10["files"][n]["status"] for n in EXPECTED_RESULT_FILES}))
        print("  两个状态 JSON 也记录 failed: %s" % {
            n: json.loads((out10 / n).read_text(encoding="utf-8"))["overall_status"]
            for n in output.STATUS_JSON_FILES})

        # 场景 11：两个状态 JSON 落盘与失败隔离（P1-2）
        print("\n----- 场景 11：result.json / last_run.json 落盘与失败隔离（P1-2）-----")
        csv11s = base / "s11.csv"
        _write_fixture(csv11s)
        out11s = _prep_run_dir(base, "s11")
        st11s = pipeline.run_once(settings, regions, runner=_runner_ok,
                                  csv_path=csv11s, output_dir=out11s)
        full11 = json.loads((out11s / output.RESULT_JSON).read_text(encoding="utf-8"))
        light11 = json.loads((out11s / output.LAST_RUN_JSON).read_text(encoding="utf-8"))
        print("  11a 正常落盘: %s" % {
            n: {"bytes": (out11s / n).stat().st_size,
                "status": st11s["status_files"][n]["status"],
                "atomic": st11s["status_files"][n]["atomic_replace"]}
            for n in output.STATUS_JSON_FILES})
        print("     result.json   document_type=%s 字段数=%d 含 cfst_command=%s" %
              (full11["document_type"], len(full11), "cfst_command" in full11))
        print("     last_run.json document_type=%s 字段数=%d 含 cfst_command=%s" %
              (light11["document_type"], len(light11), "cfst_command" in light11))
        print("     overall_status=%s  六榜节点数=%s" %
              (st11s["overall_status"],
               {n: st11s["files"][n]["node_count"] for n in EXPECTED_RESULT_FILES}))

        out11b = _prep_run_dir(base, "s11b")
        st11b = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv11s, output_dir=out11b,
            status_write_overrides={output.RESULT_JSON: OSError("注入：JSON 写入失败")})
        print("  11b 写入失败隔离: status_files=%s" %
              {n: v["status"] for n, v in st11b["status_files"].items()})
        print("     六榜仍全部 updated=%s  result.json 不存在=%s  临时残留=%s" %
              (all(st11b["files"][n]["status"] == "updated" for n in EXPECTED_RESULT_FILES),
               not (out11b / output.RESULT_JSON).exists(),
               safety.leftover_temp_files(out11b)))

        out11c = _prep_run_dir(base, "s11c")
        (out11c / output.RESULT_JSON).write_text("OLD-RESULT-JSON\n", encoding="utf-8")
        st11c = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv11s, output_dir=out11c,
            status_replace_overrides={output.RESULT_JSON: OSError("注入：JSON 替换失败")})
        print("  11c 替换失败: 旧 result.json 字节保留=%s  六榜仍全部 updated=%s" %
              ((out11c / output.RESULT_JSON).read_text(encoding="utf-8")
               == "OLD-RESULT-JSON\n",
               all(st11c["files"][n]["status"] == "updated"
                   for n in EXPECTED_RESULT_FILES)))

        out11d = _prep_run_dir(base, "s11d")
        st11d = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv11s, output_dir=out11d,
            validator_overrides={"SG.txt": lambda t: (_ for _ in ()).throw(
                safety.SafetyError("注入：SG 校验失败"))})
        print("  11d 部分成功: overall=%s  updated_files=%d  last_run.json.overall=%s" %
              (st11d["overall_status"], len(st11d["updated_files"]),
               json.loads((out11d / output.LAST_RUN_JSON).read_text(
                   encoding="utf-8"))["overall_status"]))

        # 两个状态文件全文（供 ChatGPT 只读审查）
        print("\n----- 状态文件全文：result.json（场景 11a，完整结果）-----")
        print((out11s / output.RESULT_JSON).read_text(encoding="utf-8"), end="")
        print("\n----- 状态文件全文：last_run.json（场景 11a，轻量状态）-----")
        print((out11s / output.LAST_RUN_JSON).read_text(encoding="utf-8"), end="")

    print("\n=== 模拟结束：临时目录已自动清理；NAS data/ 与正式订阅文件未被写入 ===")
    return 0


# --------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description="cf-ip-optimizer 阶段 4.1-R2（单轮测速 / 六榜独立发布 / 状态 JSON 落盘；不执行真实测速）",
    )
    parser.add_argument("--check-config", action="store_true",
                         help="加载并校验 settings.json / regions.json")
    parser.add_argument("--self-test", action="store_true",
                         help="运行任务书 28 项 + R1 新增 18 项 + R2 新增 14 项离线必测")
    parser.add_argument("--simulate", action="store_true",
                         help="临时目录离线模拟十一类场景")
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


## 3 未修改的 2 个配置文件（R2 未改，R1 审查材料已含全文）


### config/settings.json — sha256=750b9fedde2b1f4519f996007286b951482deaa54eb90d5a5ec64d3c5f0a00e0

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


### config/regions.json — sha256=998745250d900520000599da43b3c1f4ef59e92a077984295079b771e8d7f83a

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


## 4 docs/TASK_BOOK.md 新增附录 C（全文）

````markdown
# 附录 C：阶段 4.1-R2 综合问题清单修正记录（2026-11-22）

> 依据用户整理的 `STAGE4_1-R1 综合问题清单与后续整改要求.md`（合并两份审查材料，分三类）。
> **本轮授权范围严格限定为三项**：P0-1 CSV 初始化失败即终止、P1-1 CSV 新鲜度强化、
> P1-2 真正落盘 `result.json` / `last_run.json`，以及对应离线测试、任务书更新与交付材料。
> 清单中列为「正式部署前必须完成的事项」的 P1-3～P1-7、P2-1～P2-3 **一律不在本轮实施**，
> 只在这里登记，避免 R2 擅自扩大修改范围。完成后停止，等待 ChatGPT 只读验收，不进入 4.2。

## C.1 三项修正（已完成）

### P0-1：CSV 初始化失败必须立即终止，不能继续测速

- `app/cfst.py` 新增 `RunCsvInit(ok, reason, pre_absent, started_ns, token, source)` 证据对象；
  `prepare_run_csv(path, *, unlink_fn=None)` 由「返回 bool」改为返回该对象，**fail-closed**：
  父目录不存在、目标路径残留且删除失败（权限 / I/O 错误）、删除后仍存在、路径状态不稳定，
  一律 `ok=False`；只有「父目录存在 + 目标路径确证不存在」才 `ok=True, pre_absent=True`。
  只操作本轮一次性路径，绝不触碰正式 `data/result.csv` 或六个正式 TXT。
- `app/pipeline.py` `run_once()` 阶段 A0 显式检查 `init.ok`；失败即 `return`，
  **不调用 CFST runner**、`cfst_exit_code` 保持 None、六榜全部 `skipped`、
  六个旧 TXT 与正式历史 CSV 字节不变、残留现场保留（`cleanup=False`）便于审计。
- 状态中新增 `csv_init_ok` / `csv_init_reason` / `csv_init_source` / `csv_init_pre_absent`
  与 `failure_stage="csv_init"`、`failure_reason="CSV 初始化失败: …"`，
  与「普通测速失败」（`failure_stage="cfst_run"`）明确区分，不误记为成功或普通失败。
- 离线测试 N01 预置一个 **mtime 很新**的残留 CSV 并注入清理失败，
  实测 `runner 调用次数 = 0`、六 TXT 与历史 CSV 均不变、状态记录完整；N02 为成功对照。

### P1-1：CSV 新鲜度判断不能只依赖 mtime 时间容差

- `csv_is_fresh(path, init)` 改为**强制消费本轮 `RunCsvInit` 证据**：
  `init` 非 `RunCsvInit` / `init.ok=False` / 生产路径 `pre_absent=False` 一律 fail-closed 拒绝，
  即使残留文件 mtime 很新也不接受。
- 生产路径的硬性证据链：① 初始化成功且运行前确证目标一次性路径不存在；
  ② CFST runner 退出码 0；③ 运行后该路径存在且非空。
  由 ①+③ 的「不存在 → 存在」跃迁证明 CSV 为本轮生成 —— 一次性随机路径外部无法预知，
  残留旧文件在 prepare 阶段要么被删除、要么触发 fail-closed 终止。
- **mtime 降级为辅助合理性校验**（仍保留 2s 容差剔除明显陈旧文件），
  并在 `cfst.py` docstring 中说明：部分 NAS / 网络文件系统时间戳粒度为 1s 或更粗、
  时钟回拨可能让新文件看起来旧；反之残留文件可把 mtime 伪造成很新。
  因此 mtime 既不能单独证明「本轮生成」，也不再是唯一通过依据。
- `explicit_path_evidence()` 仅为离线测试的显式 `csv_path` 构造 `source="test_explicit"`
  的非生产证据（保留 mtime 辅助判据），生产路径恒走 `prepare_run_csv`，
  二者由 `source` 字段区分，返回原因中明确标注非生产路径。
- 离线测试 N03（prepare 四态）、N04（无证据 / init 失败 / 缺前置证据均拒绝）、
  N05（auto 路径退出码 0 但未生成 CSV 仍拒绝）。

### P1-2：真正落盘 `data/result.json` 与 `data/last_run.json`

- `app/output.py` 新增 `RESULT_JSON` / `LAST_RUN_JSON` / `STATUS_JSON_FILES` 常量、
  `build_result_payload()` / `build_last_run_payload()` / `render_result_json()` /
  `render_last_run_json()`。两个 payload 均用**字段白名单**从 status 挑选，绝不整体 dump。
- **两者保存不同数据**（明确定义）：
  - `result.json` = 本次运行的**完整结果**：含 CFST 命令、本轮/历史 CSV 路径、
    CSV 初始化证据、新鲜度/完整性、六榜逐文件完整详情、最快节点、警告、
    `overall_status`、`failure_stage` / `failure_reason`（用于审计追溯）。
  - `last_run.json` = 最近一次运行的**轻量状态**：去掉命令、路径、警告；
    六榜精简为 `status / node_count / reason` 三项（供监控、调度、推送读取）。
- `app/safety.py` 新增 `publish_json_file()`：同目录 `mkstemp(0o600)` → 写完整内容 →
  flush → fsync → 回读文本逐字节比对 → `json.loads` 结构校验 → 凭据标记扫描 →
  `os.replace()`；任何异常都删除临时文件、保留该 JSON 旧正式版本、不向外抛。
  `_SECRET_MARKERS` 扩展为 `ghp_ / github_pat_ / Authorization / Bearer / password / passwd /
  token / api_key / private_key / SendKey / SCT`，TXT 与 JSON 共用同一套扫描规则。
- `app/pipeline.py` 阶段 E 在六个 TXT 发布与 CSV 归档**之后**独立写两个 JSON，
  各自 `try/except` 隔离；`status["status_files"]` 记录每个 JSON 的写入结果；
  `overall_status` 区分 `success` / `partial` / `failed`（`success`=六榜全更新、
  `partial`=至少一个未更新、`failed`=测速失败或六榜零更新）。
  状态 JSON 写入 / 替换失败**不破坏任何已成功发布的 TXT**。
- **注**：写入失败的状态文件无法记录自身的失败（自指限制），故完整写入结果保存在
  `run_once` 返回的 `status["status_files"]` 与后续运行日志中，不写进两个 JSON 自身。
- 状态 JSON 使用独立的 `status_replace_fn` / `status_write_overrides` /
  `status_replace_overrides` 注入通道，**不复用 TXT 的 `replace_fn`**，
  因此六个 TXT 的 `os.replace` 调用次数仍恰好为 6（N14 回归断言）。

## C.2 新增离线测试（14 项，N01～N14）

`app/main.py` `--self-test` 由 51 项扩到 **65 项通过 / 0 失败 / 2 跳过**；
`--simulate` 由 9 个场景扩到 **11 个场景**（新增场景 10 初始化失败、场景 11 状态 JSON）。

| 编号 | 覆盖 |
|---|---|
| N01 | 清理失败 → runner 0 次 / 六 TXT 与历史 CSV 不变 / `failure_stage=csv_init` / 残留现场保留 |
| N02 | 初始化成功对照 → runner 1 次 / `pre_absent=True` / 归档成功 |
| N03 | `prepare_run_csv` 四态：干净 / 已清理 → ok；清理失败 / 父目录缺失 → fail-closed |
| N04 | 新鲜度不单独依赖 mtime：无证据 / init 失败 / 缺前置证据一律拒绝 |
| N05 | auto 路径退出码 0 但未生成 CSV → 拒绝发布，六 TXT 与历史 CSV 不变 |
| N06 | 两个状态 JSON 合法落盘、必需字段齐全、完整版与轻量版内容不同 |
| N07 | 两 JSON 各经同目录临时文件 + `os.replace()`，无临时残留 |
| N08 | JSON 写入失败：该文件 failed / 另一 JSON 仍更新 / 六榜照常 |
| N09 | JSON 替换失败：旧版本字节保留 / 六 TXT 仍全部更新 / 无临时残留 |
| N10 | 两个状态 JSON 不含 Token / SendKey / 密码 / 凭据标记 |
| N11 | `success` / `partial` / `failed` 三态可区分且两个 JSON 记录一致 |
| N12 | 初始化失败也落盘状态，`failure_stage=csv_init`，不误记为测速失败 |
| N13 | 源码级确认 `init.ok` 检查、新鲜度消费证据、两 JSON 原子落盘真实存在 |
| N14 | 回归：TXT 原子替换仍恰好 6 次，状态 JSON 不干扰 TXT 发布链路 |

R1 已通过的 51 项全部保留并回归通过（含六榜独立渲染、单榜失败隔离、空榜、
陈旧 mtime 拒绝、IPv4 严格、0o600 权限、表头别名、不生成 merged.txt 等）。
S01（真实测速 / 真实 CSV 单位，4.4）与 S02（容器 Python 3.12 / 0o600 读取权限，4.2）
继续按阶段授权边界跳过。

## C.3 明确未完成 / 纳入后续阶段（本轮一律未实施）

1. **P1-3 防重入机制（Cron 上线前验收条件）**：进程锁 / 文件锁、前次未结束则跳过、
   记录跳过原因、异常退出后锁恢复、两并发实例测试 —— 尚未实现，安排在正式调度阶段。
2. **P1-4 阶段 4.2 容器集成**：Python 3.12、UID 1000 / GID 0 非 root、`data/`/`logs/`
   实际读写、0o600 TXT 能否被 EdgeTunnel / Web / GitHub 消费者读取、只读根文件系统、
   tmpfs、容器重启数据保留、不加入 Mihomo 网络、代理变量为空。**0o600 不得擅自放宽**。
3. **P1-5 阶段 4.3 网络与参数审计**：`-dn 100` 合理性、超时、并发 NAS 负载、
   Docker bridge 出口、路由器透明代理。**容器内无 HTTP_PROXY 不能证明透明代理不存在**。
4. **P1-6 阶段 4.4 真实测速（需用户明确授权）**：单次完整 CFST、真实 CSV 丢包率单位、
   普通 TCPing+下载模式 Colo 稳定性、MB/s 单位、`-dn 100` 有效下载数量、地区覆盖、
   耗时与 NAS 负载。`download_count=100` 只是初始测试值，非最终定值。
5. **P1-7 地区映射补全**：仅 `SIN→SG`、`LAX→US`；HK/JP/KR 空、DEN 待确认、AMS/N/A 排除。
   禁止猜测，只能依据真实样本经用户确认后更新 `regions.json`。
6. **P2-1 `logs/` 独立日志归档**：每次运行独立记录、开始/结束/耗时、CFST 退出码、
   六榜数量与失败原因、不记凭据、轮转策略、日志失败不破坏订阅文件 —— 尚未实现。
7. **P2-2 正式发布与外部集成**：六个 TXT 正式发布、GitHub `cf-ip-results` 仓库与六条
   Raw 订阅、EdgeTunnel 原生六订阅接入、每日 06:00/12:00/18:00 定时、Server 酱推送 —— 全部未执行。
8. **P2-3 SSH 凭据安全**：建议用户尽快改密或改用公钥认证、排查密码复用；
   本轮未对 NAS 系统设置做任何变更，也未把凭据写入任何文件、任务书、日志或脚本。
9. **状态 JSON 的正式落盘位置**：R2 只实现了「写盘能力 + 离线测试」，
   正式运行时 `data/` 下才会出现这两个文件；当前 `data/`、`logs/` 仍为空目录。

## C.4 R2 安全边界（均为「未执行」）

真实网络请求 / CFST 测速 / 网络扫描 / 容器启动 / 镜像构建 / Cron 修改 /
GitHub 上传 / EdgeTunnel 修改 / Server 酱配置 / 路由器与代理网络设置 /
NAS 权限修改 —— **全部未执行**。网络守卫拦截 0 次；`execute_cfst` 仍为拒绝占位，
`--run` 仍返回 exit 2。`Dockerfile`、`compose.yaml`、`.dockerignore`、`config/regions.json`、
`config/settings.json`、`app/ranking.py`、`app/region.py`、`app/config.py`、
CFST 二进制与 6 份历史 `samples/*.csv` 均未修改；`data/`、`logs/` 保持空目录。

## C.5 阶段结束要求

R2 完成后**停止**，不进入阶段 4.2。由 ChatGPT 做只读代码审查，
确认 P0-1 / P1-1 / P1-2 全部解决后，再单独决定是否授权阶段 4.2。
````


## 5 测试结果索引


| 项目 | 结果 |
|---|---|
| NAS Python | 3.11.2；`compileall` 9 个 .py 全通过 |
| `--check-config` | exit 0，`-dn=100`，禁用参数自检无违规 |
| `--self-test` | **通过 65 / 失败 0 / 跳过 2 / 合计 67**，exit 0，网络守卫拦截 0 次 |
| `--simulate` | 11 个场景全通过，exit 0 |
| `--run` | `[拒绝]` exit 2 |
| 权限实测 | POSIX 下六个 TXT 全部 `0o600` |
| 最终状态 | `data/`、`logs/` 仍为空；项目内无正式结果/编译产物/临时残留 |
| 跳过项 | S01 真实测速(4.4)、S02 容器 Python 3.12 与 0o600 读取权限(4.2) |

完整逐行输出见 `STAGE4_1_R2_TEST_OUTPUT.txt`。

