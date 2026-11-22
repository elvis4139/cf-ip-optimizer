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

4.1-R3 修正（R3-01 / R3-02 / R3-03 / R3-05）：

  * R3-01：RunCsvInit 新增 bound_path 字段，token 升级为「路径绑定票据」
    <nonce>.<HMAC-SHA256(进程内密钥, nonce|规范化路径)>。csv_is_fresh 必须同时校验
    票据有效、bound_path 与当前 path 完全一致、票据未被消费；缺失、伪造、错配、
    跨路径或跨轮复用的证据一律 fail-closed。进程内密钥使进程外无法伪造票据。
  * R3-02：source 改为严格白名单 production / test_explicit；None、空串、未知
    字符串一律拒绝。production 必须 pre_absent=True；test_explicit 不得携带
    production 前置证明，也不得作为生产证据缺失时的自动回退。
  * R3-03：csv_is_fresh 把 is_file/stat 等文件系统观测收敛成明确的失败结果
    (False, 原因)，绝不向调用方抛出；原因统一标注为 freshness 文件系统检查异常。
    validate_csv_completeness 的文件读取同样收敛为「不完整」而非异常外溢。
  * R3-05：prepare_run_csv 改用 os.path.lexists + os.lstat 检查目录项本身：
    普通文件、目录、正常符号链接、断开符号链接都不能记为 pre_absent=True；
    目录与特殊文件一律拒绝删除，符号链接只删链接本身（不跟随目标）。
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import math
import os
import stat
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

# R3-02：初始化证据来源的严格白名单，任何其它值（含 None / ""）都拒绝。
PRODUCTION_SOURCE = "production"
TEST_EXPLICIT_SOURCE = "test_explicit"
ALLOWED_INIT_SOURCES = frozenset((PRODUCTION_SOURCE, TEST_EXPLICIT_SOURCE))

# R3-01：进程内随机密钥，只用于本进程内把「本轮证据」绑定到「规范化 CSV 路径」。
# 不写入任何文件、不进入状态 JSON；进程外无法伪造合法票据。
_EVIDENCE_SECRET = os.urandom(32)
_CONSUMED_TOKENS: set[str] = set()


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
# 本轮 CSV 初始化证据与新鲜度（R1 新增；R2 重写；R3 加证据绑定与异常收敛）
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RunCsvInit:
    """本轮 CSV 初始化证据对象（R3-01：证据必须绑定到具体路径与具体本轮）。

    ok            是否初始化成功；False 时调用方【必须】终止本轮，不得调用 runner。
    reason        成功/失败原因，写入运行状态，便于区分「初始化失败」与「测速失败」。
    pre_absent    运行前是否已确证目标【目录项】不存在（生产路径的新鲜度主证据）。
    started_ns    本轮时间基准，在确证不存在之后取（mtime 辅助校验用）。
    token         本轮「路径绑定票据」：<nonce>.<HMAC(nonce|bound_path)>；
                  csv_is_fresh 必须校验，且只允许消费一次。
    source        production（一次性路径）| test_explicit（离线测试显式路径）；
                  R3-02 起仅这两个值合法。
    bound_path    证据绑定的规范化绝对路径；csv_is_fresh 必须与当前 path 一致。
    """

    ok: bool
    reason: str
    pre_absent: bool
    started_ns: int
    token: str
    source: str
    bound_path: str = ""


def _normalise_path(path) -> str:
    """规范化为绝对路径；仅用于证据绑定比对，不创建任何目录或文件。"""
    return str(Path(path).resolve())


def _make_bound_token(path) -> str:
    """生成绑定到规范化路径的一次性票据（进程内 HMAC，外部不可伪造）。"""
    nonce = uuid.uuid4().hex
    material = ("%s|%s" % (nonce, _normalise_path(path))).encode("utf-8")
    digest = hmac.new(_EVIDENCE_SECRET, material, hashlib.sha256).hexdigest()
    return "%s.%s" % (nonce, digest)


def _token_matches(token, path) -> bool:
    """票据是否由本进程签发且绑定到当前 path。"""
    if not isinstance(token, str) or token.count(".") != 1:
        return False
    nonce, digest = token.split(".", 1)
    if not nonce or len(digest) != 64:
        return False
    material = ("%s|%s" % (nonce, _normalise_path(path))).encode("utf-8")
    expected = hmac.new(_EVIDENCE_SECRET, material, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)


def _entry_kind(path) -> str:
    """R3-05：用 lexists + lstat 判定【目录项本身】的类型，不跟随符号链接。

    返回 absent / file / dir / symlink / other。断开的符号链接同样是 symlink，
    绝不会被 Path.exists() 误判为不存在。目录与特殊文件不允许被删除。
    """
    raw = os.fspath(path)
    if not os.path.lexists(raw):
        return "absent"
    info = os.lstat(raw)                 # 可能抛 OSError，由调用方收敛
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    if stat.S_ISDIR(info.st_mode):
        return "dir"
    if stat.S_ISREG(info.st_mode):
        return "file"
    return "other"


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
    """运行前初始化本轮一次性 CSV 路径：清理残留并确证【目录项】不存在。

    P0-1 / R3-05 关键语义 —— fail-closed：
      * 父目录不存在或检查失败 -> ok=False（不擅自创建目录）；
      * R3-05 用 lexists + lstat 识别普通文件、目录、正常/断开符号链接；
      * 目录或特殊文件占用路径 -> 直接拒绝，绝不递归删除；
      * 普通文件 / 符号链接 -> 只 unlink 目录项本身，符号链接不跟随其目标；
      * 清理失败、清理后目录项仍在、两次观测不一致 -> ok=False；
      * 只有「父目录存在 + 目录项确证不存在」才返回 ok=True / pre_absent=True。
    只操作本轮路径，绝不触碰正式 data/result.csv 或六个正式 TXT。

    unlink_fn 仅供离线测试注入删除故障，生产路径恒为 Path.unlink。
    """
    p = Path(path)
    norm = _normalise_path(p)
    token = _make_bound_token(p)

    def _fail(reason: str) -> RunCsvInit:
        return RunCsvInit(False, reason, False, time.time_ns(), token,
                          PRODUCTION_SOURCE, norm)

    try:
        if not p.parent.is_dir():
            return _fail("本轮 CSV 父目录不存在，拒绝继续测速: %s" % p.parent)
    except OSError as exc:
        return _fail("检查本轮 CSV 父目录失败（%s）: %s" % (type(exc).__name__, exc))

    try:
        first = _entry_kind(p)
    except OSError as exc:
        return _fail("检查本轮 CSV 目录项失败（%s）: %s" % (type(exc).__name__, exc))

    if first in ("dir", "other"):
        return _fail("本轮 CSV 路径被目录/特殊文件占用，拒绝删除并继续测速: %s" % p)
    if first != "absent":
        try:
            (unlink_fn or Path.unlink)(p)
        except OSError as exc:
            return _fail("清理本轮残留 CSV 失败（拒绝继续测速）: %s: %s" %
                         (type(exc).__name__, exc))

    try:
        second = _entry_kind(p)
    except OSError as exc:
        return _fail("复核本轮 CSV 目录项失败（%s）: %s" % (type(exc).__name__, exc))
    if second != "absent":
        return _fail(("清理后本轮 CSV 目录项仍存在" if first != "absent"
                      else "本轮 CSV 目录项状态不稳定") + "，拒绝继续测速: %s" % p)

    return RunCsvInit(True, "本轮 CSV 目录项已确证为空（lexists/lstat）", True,
                      time.time_ns(), token, PRODUCTION_SOURCE, norm)


def explicit_path_evidence(path) -> RunCsvInit:
    """R3-01/R3-02：离线测试专用，为显式注入的 csv_path 构造【非生产】证据。

    pipeline.run_once 仅在测试显式传入 csv_path 时调用本函数；生产路径恒走
    prepare_run_csv。test_explicit 没有「前置不存在」证据，因此 csv_is_fresh
    对它只使用 mtime 辅助判据，并在返回原因中明确标注为非生产路径。
    票据同样绑定到 path：显式测试证据也不能被挪用到其它路径或其它轮次。
    """
    return RunCsvInit(True, "离线测试显式路径（非生产）", False,
                      time.time_ns(), _make_bound_token(path),
                      TEST_EXPLICIT_SOURCE, _normalise_path(path))


def csv_is_fresh(path, init, *, is_file_fn=None, stat_fn=None) -> tuple:
    """判断本轮 CSV 是否确由本次运行写出，返回 (bool, 原因)。

    生产路径的硬性证据链（R2 建立，R3 加严）：

      1. init 必须是本轮 RunCsvInit，且 ok=True；
      2. R3-02：source 必须命中严格白名单；production 必须 pre_absent=True；
      3. R3-01：token 票据必须由本进程签发、绑定到当前 path，且未被消费；
         bound_path 必须与当前 path 的规范化形式完全一致；
      4. CFST runner 退出码为 0（由 pipeline 在调用本函数前保证）；
      5. 运行后该路径存在且非空（R3-03：文件系统异常一律转化为失败结果）。

    由 3)+5) 的「不存在 -> 存在」跃迁证明文件是本轮创建的：一次性随机
    路径外部无法预知，残留旧文件在 prepare 阶段要么被删除、要么触发
    fail-closed 终止。mtime 只作为剔除「明显早于本轮开始」的辅助合理性校验
    （含 2s 容差），不再单独决定新鲜度。

    is_file_fn / stat_fn 仅用于离线测试注入文件系统异常，生产路径恒为默认值。
    本函数【绝不向外抛出异常】：任何无法确认的情况都返回 (False, 明确原因)，
    由 pipeline 统一收敛到 _abort(stage="csv_fresh") 并落盘失败状态。
    """
    if not isinstance(init, RunCsvInit):
        return False, "缺少本轮 CSV 初始化证据（fail-closed，拒绝非本轮文件）"
    if not init.ok:
        return False, "本轮 CSV 初始化未成功: %s" % init.reason

    # --- R3-02：source 严格白名单，未知来源不得落入宽松测试分支 ---
    # 非字符串（None / list / dict / int 等）不可哈希，必须先判类型，
    # 否则 `in frozenset` 会抛 TypeError 逃逸；一律按 fail-closed 拒绝。
    if not isinstance(init.source, str) or init.source not in ALLOWED_INIT_SOURCES:
        return False, ("初始化证据来源非法（source=%r；仅允许 production / "
                       "test_explicit，fail-closed）" % (init.source,))
    production = init.source == PRODUCTION_SOURCE
    if production and not init.pre_absent:
        return False, "生产路径缺少「运行前确证不存在」证据（fail-closed）"
    if not production and init.pre_absent:
        return False, "test_explicit 证据不得携带生产前置证明（fail-closed）"

    # --- R3-01：票据 + 路径绑定 + 一次性消费 ---
    p = Path(path)
    try:
        norm = _normalise_path(p)
    except (OSError, ValueError) as exc:
        return False, "freshness 路径规范化异常（%s）: %s" % (type(exc).__name__, exc)
    if not init.bound_path or init.bound_path != norm:
        return False, "初始化证据与当前 CSV 路径不匹配（fail-closed）"
    if not _token_matches(init.token, p):
        return False, "初始化证据票据无效或与其它路径/其它运行绑定（fail-closed）"
    if init.token in _CONSUMED_TOKENS:
        return False, "初始化证据已被消费，禁止跨轮重复使用（fail-closed）"
    _CONSUMED_TOKENS.add(init.token)

    # --- R3-03：所有文件系统观测收敛为失败结果，绝不逃逸 ---
    try:
        check_file = is_file_fn or p.is_file
        if not check_file():
            return False, "本轮 CSV 未生成或不是普通文件（freshness 文件系统检查失败）"
        do_stat = stat_fn or p.stat
        info = do_stat()
        size, mtime_ns = info.st_size, info.st_mtime_ns
        if not isinstance(size, int) or not isinstance(mtime_ns, int):
            return False, "本轮 CSV 元数据无法确认（freshness 文件系统检查失败）"
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return False, "freshness 文件系统检查异常（%s）: %s" % (type(exc).__name__, exc)
    if size == 0:
        return False, "本轮 CSV 为空文件"
    if mtime_ns + FRESHNESS_TOLERANCE_NS < init.started_ns:
        return False, "本轮 CSV 时间戳早于本轮开始（辅助校验不通过）"
    if production:
        return True, ("新鲜（路径绑定票据 + 前置确证不存在 + runner 退出码 0 + "
                      "本轮路径新生成 + 非空；mtime 仅辅助）")
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
    # R3-03：文件存在性 / 大小 / 读取过程中的任何文件系统异常都收敛为
    # 「不完整」，绝不向 run_once 抛出后绕过 _abort 与失败状态落盘。
    try:
        if not p.is_file():
            return False, "CSV 文件不存在", None
        if p.stat().st_size == 0:
            return False, "CSV 为空文件", None
        data = parse_csv_file(p)
    except CsvError as exc:
        return False, str(exc), None
    except (OSError, ValueError, UnicodeError) as exc:
        return False, "CSV 文件系统检查异常（%s）: %s" % (type(exc).__name__, exc), None
    missing = sorted(REQUIRED_SEMANTIC_FIELDS - set(data.resolved_fields))
    if missing:
        return False, "CSV 缺少语义字段: %s" % ", ".join(missing), data
    if data.malformed_rows:
        return False, "CSV 有 %d 行截断/列数不足" % len(data.malformed_rows), data
    if not data.rows:
        return False, "CSV 无数据行", data
    return True, "完整", data
