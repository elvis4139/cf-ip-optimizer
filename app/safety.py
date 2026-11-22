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

4.1-R3（R3-04 / R3-06）：
  * R3-04：publish_json_file 的【父目录创建、临时文件创建】也纳入同一个 try，
    全流程（mkdir -> mkstemp -> 写 -> fsync -> 回读 -> json.loads -> 凭据扫描 ->
    os.replace）任何一步失败都只返回该文件的失败结果，绝不向外抛；
    新增 mkdir_fn / mkstemp_fn / unlink_fn 注入点供离线测试覆盖早期失败；
    临时文件清理失败单独记入 cleanup_warning，不掩盖原始失败原因。
  * R3-06：凭据扫描改为大小写不敏感 + 正则规则，覆盖 TOKEN=/token=、
    SendKey/sendkey、Bearer /BEARER、github_pat_、常见密钥字段名、
    URL 参数中的凭据与裸长十六进制密钥；命中时拒绝发布且不回显原文。
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
# R3-06：字面量标记（大小写不敏感比较）。去掉裸 "SCT" 以免误伤同名 Colo，
# 改用下方 _SECRET_PREFIX_RE 精确匹配 Server 酱 SCT<数字> 形式。
_SECRET_MARKERS = ("ghp_", "github_pat_", "Authorization:", "Bearer ",
                   "password=", "passwd=", "token=", "api_key", "private_key",
                   "SendKey")

# 常见密钥字段名 + 赋值/冒号分隔符（大小写不敏感）
_SECRET_FIELD_RE = re.compile(
    r"(?i)\b(?:authorization|bearer|passwd|password|pwd|secret|sendkey|"
    r"api[_-]?key|access[_-]?key|private[_-]?key|access[_-]?token|"
    r"token|github[_-]?pat)\b\s*[=:]"
)
# Bearer <值>（大小写不敏感）
_SECRET_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{6,}")
# 已知密钥前缀：GitHub PAT / ghp / Server 酱 SCT<数字>
_SECRET_PREFIX_RE = re.compile(
    r"(?i)\b(?:ghp_[A-Za-z0-9]{6,}|github[_-]?pat[_-][A-Za-z0-9_]{6,}|"
    r"sct[0-9]{4,}[A-Za-z0-9]*)\b"
)
# URL 查询参数里的凭据：?token=... / &api_key=...
_SECRET_URL_RE = re.compile(
    r"(?i)[?&](?:token|key|secret|password|passwd|sendkey|"
    r"access[_-]?token|api[_-]?key)\s*=\s*[^&\s]{4,}"
)
# 没有字段标记的裸长十六进制密钥（>=40 位），只判断存在、不回显内容
_SECRET_BARE_RE = re.compile(r"\b[0-9a-fA-F]{40,}\b")


class SafetyError(RuntimeError):
    """单文件内容校验失败或原子替换被拒绝。"""


def contains_secret_markers(content: str) -> bool:
    """R3-06：判断内容是否疑似含凭据；只返回布尔值，绝不回显疑似原文。

    字段白名单（output.build_*_payload）是第一道防线，本函数是落盘前第二道。
    """
    if not isinstance(content, str):
        return True
    lowered = content.lower()
    if any(marker.lower() in lowered for marker in _SECRET_MARKERS):
        return True
    return any(rx.search(content) for rx in (
        _SECRET_FIELD_RE, _SECRET_BEARER_RE, _SECRET_PREFIX_RE,
        _SECRET_URL_RE, _SECRET_BARE_RE,
    ))


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
    if contains_secret_markers(content):
        raise SafetyError("%s 疑似包含凭据内容（不回显原文）" % filename)

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
                      write_fn=None, mkdir_fn=None, mkstemp_fn=None,
                      unlink_fn=None) -> dict:
    """单文件原子写入 JSON 状态文件（R2 新增；R3-04 补全异常边界）。

    R3-04：从【父目录创建】到【原子替换】的全部步骤都在同一个 try 内：
      mkdir -> mkstemp -> 写入 -> flush -> fsync -> 回读比对 -> json.loads
      -> 凭据扫描 -> os.replace()。
    任何一步失败都只产生该文件自己的失败结果，绝不向外抛、绝不破坏该文件
    旧版本；调用方据此让另一个 JSON 继续尝试。临时文件清理失败单独记入
    cleanup_warning，不覆盖也不掩盖原始失败原因。

    write_fn / replace_fn / mkdir_fn / mkstemp_fn / unlink_fn 仅供离线测试
    注入故障；生产路径恒为默认值（None 即使用标准库实现）。
    """
    target = Path(target)
    tmp_path = None
    try:
        # 1) 父目录创建（R2 时位于 try 之外，R3-04 纳入）
        if mkdir_fn is not None:
            mkdir_fn(target.parent)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)

        # 2) 同目录临时文件创建（R2 时位于 try 之外，R3-04 纳入）
        prefix, suffix = ".tmp-%s-" % target.name, ".part"
        if mkstemp_fn is not None:
            fd, tmp = mkstemp_fn(dir=str(target.parent), prefix=prefix, suffix=suffix)
        else:
            fd, tmp = tempfile.mkstemp(prefix=prefix, suffix=suffix,
                                       dir=str(target.parent))
        tmp_path = Path(tmp)
        do_replace = replace_fn or os.replace

        # 3) 写入 + fsync
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            if write_fn is not None:
                write_fn(content)          # 注入点；抛异常时 with 仍会关闭 fd
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())

        # 4) 回读逐字节比对
        raw = tmp_path.read_text(encoding="utf-8")
        if raw != content:
            raise SafetyError("%s 临时文件回读不一致" % target.name)
        # 5) JSON 结构校验
        json.loads(raw)
        # 6) 凭据扫描（R3-06：大小写不敏感 + 正则）
        if contains_secret_markers(raw):
            raise SafetyError("%s 疑似包含凭据内容，拒绝发布（不回显原文）" % target.name)
        # 7) 原子替换
        do_replace(str(tmp_path), str(target))
        return {
            "status": "updated",
            "size_bytes": len(content.encode("utf-8")),
            "reason": None,
            "temp_file": tmp_path.name,
            "atomic_replace": True,
            "cleanup_warning": None,
        }
    except Exception as exc:  # 该状态文件的完整流程失败，不影响其它文件
        cleanup_warning = None
        if tmp_path is not None:
            try:
                (unlink_fn or Path.unlink)(tmp_path)
            except Exception as cleanup_exc:
                cleanup_warning = "临时文件清理失败（%s）: %s" % (
                    type(cleanup_exc).__name__, cleanup_exc)
        return {
            "status": "failed",
            "size_bytes": None,
            "reason": "%s: %s" % (type(exc).__name__, exc),
            "temp_file": tmp_path.name if tmp_path is not None else None,
            "atomic_replace": False,
            "cleanup_warning": cleanup_warning,
        }


def leftover_temp_files(directory) -> list:
    p = Path(directory)
    return sorted(x.name for x in p.glob(".tmp-*.part")) if p.is_dir() else []
