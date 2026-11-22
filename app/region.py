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
