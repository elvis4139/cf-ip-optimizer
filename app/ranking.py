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
