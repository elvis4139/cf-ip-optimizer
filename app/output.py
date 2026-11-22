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

4.1-R3：字段白名单结构保持不变（不重构 build_*_payload），仅为 R3-07 增加
csv_archived / csv_archive_reason 两个审计字段，使生产 CSV 归档失败时
两个状态 JSON 都能明确记录「归档未成功 + 具体失败原因」。
status_persist_state 属于「本次状态文件写入结果」，依 R2 已确立的
「状态 JSON 不自指记录自身写入结果」原则，只保留在 run_once 返回的 status 中。
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
    "csv_archived", "csv_archive_reason", "csv_total_rows", "valid_ip_count",
    "files", "failed_files",
    "skipped_files", "updated_files", "fastest_node", "measurement_success",
    "all_files_updated", "overall_status", "failure_stage", "failure_reason",
    "warnings", "speed_unit",
)
_LIGHT_FIELDS = (
    "run_time", "timezone", "run_mode", "overall_status", "failure_stage",
    "failure_reason", "measurement_success", "all_files_updated",
    "cfst_exit_code", "csv_init_ok", "csv_fresh", "csv_complete",
    "csv_archived", "csv_archive_reason",
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
