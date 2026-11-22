"""主流程入口（阶段 4.1-R3）。

可用命令：
  --check-config   加载并校验两份配置，打印唯一一条 CFST 命令（只构造，不执行）
  --self-test      任务书 28 项 + R1 新增 18 项 + R2 新增 14 项 + R3 新增 X 项，
                   含网络守卫；零真实测速、零真实网络请求
  --simulate       在临时目录用模拟 CSV 演示六榜生成 / 单文件失败 / 完整测速失败 /
                   空榜 / 原子替换 / CSV 新鲜度 / CSV 初始化失败 /
                   状态 JSON 落盘与失败隔离 / R3 异常收敛与归档状态等场景，
                   不写 NAS 正式订阅文件
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
from dataclasses import replace
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
# 4.1-R3 离线测试辅助（全部使用明显的 DUMMY 假值，绝不使用真实凭据）
# --------------------------------------------------------------------------
def _evidence(path, **changes):
    """用公开 API 生成绑定到 path 的本进程合法证据，再按测试需要改字段。

    仅用于【单元级】边界测试；端到端 production 路径仍走 prepare_run_csv，
    端到端 test_explicit 路径仍走 explicit_path_evidence，不在生产代码里开后门。
    """
    return replace(cfst.explicit_path_evidence(path), **changes)


def _prod_evidence(path, **changes):
    options = {"source": cfst.PRODUCTION_SOURCE, "pre_absent": True}
    options.update(changes)
    return _evidence(path, **options)


def _symlink_capable() -> bool:
    with tempfile.TemporaryDirectory(prefix="cf41r3-symprobe-") as td:
        try:
            os.symlink("missing-target", os.path.join(td, "probe"))
            return True
        except (OSError, NotImplementedError, AttributeError):
            return False


def _dummy_secret_cases() -> tuple:
    """R3-06 凭据扫描用例；全部为 DUMMY 假值，不是任何真实 Token / SendKey / PAT。"""
    return (
        "TOKEN=DUMMY-VALUE", "token=DUMMY-VALUE",
        "SendKey=DUMMY-VALUE", "sendkey=DUMMY-VALUE",
        "Bearer DUMMYVALUE123", "BEARER DUMMYVALUE123",
        "Authorization: DUMMYVALUE123", "authorization: DUMMYVALUE123",
        "github_pat_DUMMY000000", "GITHUB_PAT_DUMMY000000",
        "ghp_DUMMY000000", "api_key=DUMMY-VALUE", "API-KEY: DUMMY-VALUE",
        "password=DUMMY-VALUE", "passwd=DUMMY-VALUE",
        "private_key: DUMMY-VALUE", "secret=DUMMY-VALUE",
        "https://example.invalid/x?sendKey=DUMMY0000",
        "https://example.invalid/x?access_token=DUMMY0000",
        "A" * 40,  # 无字段标记的裸长十六进制串
    )


def _r3_symlink_results(base: Path) -> dict:
    """R3-05：正常符号链接 / 断开符号链接 / 目录占用的目录项判定与清理。

    支持 symlink 的平台（NAS/Linux）做真实文件系统验证；不支持的平台
    （本机 Windows 无开发者权限时）用 _entry_kind 注入覆盖同一逻辑分支，
    并由调用方在输出中明确标注，绝不把未覆盖说成通过。
    """
    out = {"mode": "real" if _symlink_capable() else "injected",
           "normal": False, "broken": False, "target_kept": False,
           "dir": False, "dir_kept": False}
    # 目录占用：不依赖 symlink 能力，任何平台都做真实验证
    occupied = base / "r3-dir-occupied.csv"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("KEEP-DIR\n", encoding="utf-8")
    init_dir = cfst.prepare_run_csv(occupied)
    out["dir"] = (not init_dir.ok) and "目录" in init_dir.reason
    out["dir_kept"] = occupied.is_dir() and (
        occupied / "keep.txt").read_text(encoding="utf-8") == "KEEP-DIR\n"

    if out["mode"] == "real":
        target = base / "r3-link-target.txt"
        target.write_text("KEEP-TARGET\n", encoding="utf-8")
        normal = base / "r3-normal-link.csv"
        os.symlink(target.name, normal)
        init_normal = cfst.prepare_run_csv(normal)
        out["normal"] = init_normal.ok and init_normal.pre_absent
        out["target_kept"] = (not os.path.lexists(normal)
                              and target.read_text(encoding="utf-8") == "KEEP-TARGET\n")

        broken = base / "r3-broken-link.csv"
        os.symlink("definitely-missing-target", broken)
        out["broken_lexists_before"] = os.path.lexists(broken)
        out["broken_exists_before"] = broken.exists()  # 关键：exists() 会误判为不存在
        init_broken = cfst.prepare_run_csv(broken)
        out["broken"] = (init_broken.ok and init_broken.pre_absent
                         and not os.path.lexists(broken))
    else:
        # 注入：第一次观测为符号链接，清理后为不存在；unlink 不真正删文件
        for key in ("normal", "broken"):
            link = base / ("r3-%s-injected.csv" % key)
            with mock.patch.object(cfst, "_entry_kind",
                                   side_effect=["symlink", "absent"]):
                init = cfst.prepare_run_csv(link, unlink_fn=lambda p: None)
            out[key] = init.ok and init.pre_absent
        out["target_kept"] = True
        out["broken_lexists_before"] = True
        out["broken_exists_before"] = False
    return out


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
    print("  R3 证据  : token 为「路径绑定票据」，bound_path 与当前 CSV 路径必须一致，")
    print("           票据只允许消费一次；source 仅允许 production / test_explicit。")
    print("  R3 目录项: 用 lexists + lstat 检查，断开符号链接/目录占用不得记为 pre_absent。")
    print("  新鲜度    : 生产路径要求「运行前确证不存在 + 本轮新生成」，mtime 仅辅助；")
    print("           文件系统异常一律转为 freshness 失败，进入统一 _abort，不逃逸。")
    print("  状态 JSON : data/result.json（完整结果）与 data/last_run.json（轻量状态），")
    print("           各自临时文件 + fsync + 回读 JSON 校验 + os.replace() 原子替换；")
    print("           写入失败不影响六个 TXT；两者字段不同，均不含凭据。")
    print("  R3 隔离  : 每个 JSON 的 mkdir/mkstemp/写/fsync/回读/扫描/replace 全流程")
    print("           各有独立异常边界；一个失败不阻止另一个继续尝试。")
    print("  R3 状态  : 仅 production 归档失败会把 overall_status 降为 partial；")
    print("           test_explicit 离线路径不要求归档，不因 csv_archived=false 误判。")
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

        # N04 P1-1：mtime 很新也不能单独证明新鲜，必须消费本轮证据。
        # R3 适配：证据对象升级为「路径绑定票据」，因此把 R2 手工构造的
        # 裸字符串 "t" 换成【本轮真实证据的字段变体】（dataclasses.replace）。
        # 四个子断言的语义与强度完全不变，没有删除/跳过/弱化任何旧检查。
        now_ns4 = time.time_ns()
        os.utime(residual, ns=(now_ns4, now_ns4))
        fresh_none = cfst.csv_is_fresh(residual, None)
        fresh_bad = cfst.csv_is_fresh(residual, init_denied)

        p_n4a = base / "n4-no-pre.csv"
        init_n4a = cfst.prepare_run_csv(p_n4a)
        _write_text(p_n4a, fixture)
        evidence_no_pre = replace(init_n4a, pre_absent=False)
        fresh_no_pre = cfst.csv_is_fresh(p_n4a, evidence_no_pre)

        p_n4b = base / "n4-ok.csv"
        init_n4b = cfst.prepare_run_csv(p_n4b)
        _write_text(p_n4b, fixture)
        fresh_ok = cfst.csv_is_fresh(p_n4b, init_n4b)
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

        # ==================================================================
        # 4.1-R3 新增 X01~X40：R3-01 / 02 / 03 / 04 / 05 / 06 / 07
        # 全部在独立临时目录内，零网络、零真实 CFST、零 Docker、零 NAS 依赖。
        # ==================================================================
        csv_x = base / "x-common.csv"
        _write_fixture(csv_x)

        # ---- R3-01：证据绑定 token / bound_path / 一次性消费 ----
        p_xa, p_xb = base / "x01-a.csv", base / "x01-b.csv"
        _write_fixture(p_xa)
        _write_fixture(p_xb)
        ev_a = _prod_evidence(p_xa)
        x01 = cfst.csv_is_fresh(p_xa, ev_a)
        check("X01", "R3-01 正确 token + 正确路径 + 本轮证据 -> 通过",
              lambda: x01[0] is True and "路径绑定票据" in x01[1])

        x02_missing = cfst.csv_is_fresh(p_xa, _prod_evidence(p_xa, token=""))
        x02_forged = cfst.csv_is_fresh(
            p_xa, _prod_evidence(p_xa, token="deadbeef." + "0" * 64))
        x02_r2style = cfst.csv_is_fresh(p_xa, cfst.RunCsvInit(
            True, "ok", True, time.time_ns(), "t", "production",
            cfst._normalise_path(p_xa)))
        check("X02", "R3-01 token 缺失 / 伪造 / R2 裸字符串票据 -> 一律拒绝",
              lambda: x02_missing[0] is False and x02_forged[0] is False
              and x02_r2style[0] is False
              and all("fail-closed" in r[1] or "票据" in r[1]
                      for r in (x02_missing, x02_forged, x02_r2style)))

        ev_bound_a = _prod_evidence(p_xa)
        x03 = cfst.csv_is_fresh(p_xb, ev_bound_a)
        check("X03", "R3-01 证据 bound_path 与当前 CSV 路径不匹配 -> 拒绝",
              lambda: x03[0] is False and "路径" in x03[1])

        ev_other_run = _prod_evidence(p_xb)
        x04 = cfst.csv_is_fresh(p_xa, ev_other_run)
        check("X04", "R3-01 其它运行/其它路径产生的证据不得用于本轮 -> 拒绝",
              lambda: x04[0] is False and "fail-closed" in x04[1])

        ev_reuse = _prod_evidence(p_xa)
        reuse_first = cfst.csv_is_fresh(p_xa, ev_reuse)
        reuse_second = cfst.csv_is_fresh(p_xa, ev_reuse)
        check("X05", "R3-01 同一证据禁止重复使用（第二次即拒绝）",
              lambda: reuse_first[0] is True and reuse_second[0] is False
              and "重复使用" in reuse_second[1])

        out_x06 = _prep_run_dir(base, "x06")
        formal_x06 = base / "x06-history.csv"
        _write_text(formal_x06, "X06-KEEP\n")
        old_x06 = _old_bytes(out_x06)
        x06_calls = []

        def _runner_x06(c, p, t):
            x06_calls.append(1)
            return 0

        with mock.patch.object(cfst, "prepare_run_csv",
                               return_value=_prod_evidence(base / "x06-elsewhere.csv")):
            st_x06 = pipeline.run_once(
                settings, regions, runner=_runner_x06,
                formal_csv_path=formal_x06, output_dir=out_x06, run_id="r3-x06")
        check("X06", "R3-01 生产流程拿到绑定到其它路径的证据 -> freshness 拒绝、六榜不更新",
              lambda: len(x06_calls) == 1
              and st_x06["failure_stage"] == "csv_fresh"
              and st_x06["csv_fresh"] is False
              and "路径不匹配" in st_x06["failure_reason"]
              and all(st_x06["files"][n]["status"] == "skipped"
                      for n in EXPECTED_RESULT_FILES)
              and all((out_x06 / n).read_bytes() == old_x06[n]
                      for n in EXPECTED_RESULT_FILES)
              and formal_x06.read_text(encoding="utf-8") == "X06-KEEP\n")

        # ---- R3-02：source 严格白名单 ----
        x07 = cfst.csv_is_fresh(p_xa, _prod_evidence(p_xa))
        p_x08 = base / "x08.csv"
        _write_fixture(p_x08)
        x08 = cfst.csv_is_fresh(p_x08, cfst.explicit_path_evidence(p_x08))
        check("X07", "R3-02 production 合法证据（含 pre_absent）-> 通过",
              lambda: x07[0] is True and "非空" in x07[1])
        check("X08", "R3-02 test_explicit 合法离线路径 -> 通过且标注非生产",
              lambda: x08[0] is True and "非生产路径" in x08[1])

        bad_sources = (None, "", "unknown", "production ", "test-explicit",
                       "TEST_EXPLICIT", 123, [], "prod")
        x09 = [cfst.csv_is_fresh(p_xa, _evidence(p_xa, source=s, pre_absent=False))
               for s in bad_sources]
        check("X09", "R3-02 None / 空串 / 未知 / 大小写变体 / 非字符串 source 全拒绝",
              lambda: all(r[0] is False and "来源非法" in r[1] for r in x09)
              and len(x09) == len(bad_sources))

        x10 = cfst.csv_is_fresh(p_xa, _evidence(
            p_xa, source=cfst.PRODUCTION_SOURCE, pre_absent=False))
        x10b = cfst.csv_is_fresh(p_xa, _evidence(
            p_xa, source=cfst.TEST_EXPLICIT_SOURCE, pre_absent=True))
        check("X10", "R3-02 production 缺 pre_absent / test_explicit 携带生产证明 -> 拒绝",
              lambda: x10[0] is False and "确证不存在" in x10[1]
              and x10b[0] is False and "test_explicit" in x10b[1])

        out_x11 = _prep_run_dir(base, "x11")
        formal_x11 = base / "x11-history.csv"
        _write_text(formal_x11, "X11-KEEP\n")
        old_x11 = _old_bytes(out_x11)
        x11_calls = []

        def _runner_x11(c, p, t):
            x11_calls.append(1)
            return 0

        with mock.patch.object(cfst, "prepare_run_csv",
                               return_value=_evidence(base / "x11-elsewhere.csv",
                                                      source=cfst.TEST_EXPLICIT_SOURCE)):
            st_x11 = pipeline.run_once(
                settings, regions, runner=_runner_x11,
                formal_csv_path=formal_x11, output_dir=out_x11, run_id="x11")
        check("X11", "R3-02 生产流程不得使用 test_explicit 分支（runner 0 次、立即终止）",
              lambda: len(x11_calls) == 0
              and st_x11["failure_stage"] == "csv_init"
              and "来源与运行模式不匹配" in st_x11["failure_reason"]
              and st_x11["csv_init_source"] == "test_explicit"
              and all((out_x11 / n).read_bytes() == old_x11[n]
                      for n in EXPECTED_RESULT_FILES)
              and formal_x11.read_text(encoding="utf-8") == "X11-KEEP\n")

        # ---- R3-03：freshness 文件系统异常 fail-closed ----
        def _fs_boom(*_a, **_k):
            raise OSError("注入：文件系统 I/O / 权限错误")

        p_x12 = base / "x12.csv"
        _write_fixture(p_x12)
        x12 = cfst.csv_is_fresh(p_x12, _prod_evidence(p_x12), is_file_fn=_fs_boom)
        x13 = cfst.csv_is_fresh(p_x12, _prod_evidence(p_x12), stat_fn=_fs_boom)
        check("X12", "R3-03 is_file() 抛 OSError -> 返回明确失败，不向外抛异常",
              lambda: x12[0] is False and "freshness 文件系统检查异常" in x12[1]
              and "OSError" in x12[1])
        check("X13", "R3-03 stat() 抛 OSError -> 返回明确失败，不向外抛异常",
              lambda: x13[0] is False and "freshness 文件系统检查异常" in x13[1]
              and "OSError" in x13[1])

        p_x14_missing = base / "x14-not-created.csv"
        x14_missing = cfst.csv_is_fresh(p_x14_missing,
                                        _prod_evidence(p_x14_missing))
        p_x14_dir = base / "x14-directory.csv"
        p_x14_dir.mkdir()
        x14_dir = cfst.csv_is_fresh(p_x14_dir, _prod_evidence(p_x14_dir))
        check("X14", "R3-03 CSV 路径被删除/替换为目录 -> 新鲜度拒绝",
              lambda: x14_missing[0] is False and x14_dir[0] is False
              and "文件系统检查失败" in x14_missing[1])

        out_x15 = _prep_run_dir(base, "x15")
        formal_x15 = base / "x15-history.csv"
        _write_text(formal_x15, "X15-KEEP\n")
        old_x15 = _old_bytes(out_x15)
        x15_calls = []

        def _runner_x15(c, p, t):
            x15_calls.append(1)
            _write_text(Path(p), fixture)   # 本轮 CSV 确实被写出，但 freshness 仍应失败
            return 0

        with mock.patch.object(cfst, "csv_is_fresh",
                               side_effect=OSError("注入：stat I/O 错误")):
            st_x15 = pipeline.run_once(
                settings, regions, runner=_runner_x15,
                formal_csv_path=formal_x15, output_dir=out_x15,
                run_id="r3-x15")
        full_x15 = json.loads((out_x15 / output.RESULT_JSON).read_text(encoding="utf-8"))
        check("X15", "R3-03 runner 已执行但 freshness 异常 -> 统一收敛到 _abort（不归档）",
              lambda: len(x15_calls) == 1
              and st_x15["failure_stage"] == "csv_fresh"
              and st_x15["csv_fresh"] is False
              and "freshness 文件系统检查异常" in st_x15["failure_reason"]
              and st_x15["csv_archived"] is False
              and not os.path.lexists(st_x15["run_csv_path"])
              and all(st_x15["files"][n]["status"] == "skipped"
                      for n in EXPECTED_RESULT_FILES)
              and all((out_x15 / n).read_bytes() == old_x15[n]
                      for n in EXPECTED_RESULT_FILES)
              and formal_x15.read_text(encoding="utf-8") == "X15-KEEP\n"
              and full_x15["failure_stage"] == "csv_fresh"
              and full_x15["overall_status"] == "failed")

        with mock.patch.object(cfst, "validate_csv_completeness",
                               side_effect=OSError("注入：CSV 读取 I/O 错误")):
            st_x16 = pipeline.run_once(
                settings, regions, runner=_runner_ok, csv_path=csv_x,
                output_dir=_prep_run_dir(base, "x16"))
        check("X16", "R3-03 完整性校验文件系统异常也收敛到 _abort(csv_complete)",
              lambda: st_x16["failure_stage"] == "csv_complete"
              and st_x16["csv_complete"] is False
              and all(st_x16["files"][n]["status"] == "skipped"
                      for n in EXPECTED_RESULT_FILES))

        # ---- R3-04：两个状态 JSON 完整独立持久化 ----
        out_x17 = _prep_run_dir(base, "x17")
        st_x17 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_x,
            output_dir=out_x17,
            status_io_overrides={output.RESULT_JSON: {
                "mkdir": OSError("注入：mkdir 权限错误")}})
        check("X17", "R3-04 result.json 的 mkdir 失败 -> last_run.json 仍继续并成功",
              lambda: st_x17["status_files"][output.RESULT_JSON]["status"] == "failed"
              and "mkdir 权限错误" in st_x17["status_files"][output.RESULT_JSON]["reason"]
              and st_x17["status_files"][output.LAST_RUN_JSON]["status"] == "updated"
              and (out_x17 / output.LAST_RUN_JSON).exists()
              and all(st_x17["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES))

        out_x18 = _prep_run_dir(base, "x18")
        st_x18 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_x,
            output_dir=out_x18,
            status_io_overrides={output.RESULT_JSON: {
                "mkstemp": OSError("注入：mkstemp 磁盘错误")}})
        check("X18", "R3-04 result.json 的 mkstemp 失败 -> last_run.json 仍继续并成功",
              lambda: st_x18["status_files"][output.RESULT_JSON]["status"] == "failed"
              and "mkstemp 磁盘错误" in st_x18["status_files"][output.RESULT_JSON]["reason"]
              and st_x18["status_files"][output.LAST_RUN_JSON]["status"] == "updated"
              and st_x18["status_persist_state"] == "partial"
              and safety.leftover_temp_files(out_x18) == [])

        out_x19 = _prep_run_dir(base, "x19")
        st_x19 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_x,
            output_dir=out_x19,
            status_write_overrides={output.LAST_RUN_JSON: OSError("注入：末位 JSON 写入失败")})
        check("X19", "R3-04 last_run.json 写入失败 -> result.json 正常更新",
              lambda: st_x19["status_files"][output.RESULT_JSON]["status"] == "updated"
              and st_x19["status_files"][output.LAST_RUN_JSON]["status"] == "failed"
              and json.loads((out_x19 / output.RESULT_JSON).read_text(
                  encoding="utf-8"))["document_type"] == "result")

        out_x20 = _prep_run_dir(base, "x20")
        (out_x20 / output.RESULT_JSON).write_text("OLD-X20-RESULT\n", encoding="utf-8")
        st_x20 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_x,
            output_dir=out_x20,
            status_replace_overrides={output.RESULT_JSON: OSError("注入：replace 失败")})
        check("X20", "R3-04 单文件 replace 失败 -> 该旧 JSON 字节不变，另一文件仍更新",
              lambda: (out_x20 / output.RESULT_JSON).read_text(encoding="utf-8")
              == "OLD-X20-RESULT\n"
              and st_x20["status_files"][output.LAST_RUN_JSON]["status"] == "updated"
              and safety.leftover_temp_files(out_x20) == [])

        out_x21 = _prep_run_dir(base, "x21")
        st_x21 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_x,
            output_dir=out_x21,
            status_io_overrides={
                output.RESULT_JSON: {"mkdir": OSError("注入：A-mkdir 失败")},
                output.LAST_RUN_JSON: {"mkstemp": OSError("注入：B-mkstemp 失败")},
            })
        r21a = st_x21["status_files"][output.RESULT_JSON]["reason"]
        r21b = st_x21["status_files"][output.LAST_RUN_JSON]["reason"]
        check("X21", "R3-04 两个 JSON 均失败 -> 分别记录各自原因，状态为 failed",
              lambda: all(v["status"] == "failed"
                          for v in st_x21["status_files"].values())
              and "A-mkdir" in r21a and "B-mkstemp" in r21b and r21a != r21b
              and st_x21["status_persist_state"] == "failed"
              and all(st_x21["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES))

        out_x22 = _prep_run_dir(base, "x22")
        st_x22 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                   csv_path=csv_x, output_dir=out_x22)
        check("X22", "R3-04 两个 JSON 均成功 -> 合法 JSON + 原子替换 + 无残留",
              lambda: all(v["status"] == "updated" and v["atomic_replace"] is True
                          for v in st_x22["status_files"].values())
              and all(json.loads((out_x22 / n).read_text(encoding="utf-8"))[
                          "document_type"] in ("result", "last_run")
                      for n in output.STATUS_JSON_FILES)
              and st_x22["status_persist_state"] == "ok"
              and safety.leftover_temp_files(out_x22) == [])

        check("X23", "R3-04 部分持久化失败由 status_persist_state / warnings 明确记录",
              lambda: st_x17["status_persist_state"] == "partial"
              and any("部分持久化失败" in w for w in st_x17["warnings"])
              and st_x17["status_files"][output.RESULT_JSON]["status"] == "failed"
              and st_x17["status_files"][output.LAST_RUN_JSON]["status"] == "updated"
              and st_x17["overall_status"] == "success")  # 不因状态文件自身失败误判业务

        out_x24 = _prep_run_dir(base, "x24")
        st_x24 = pipeline.run_once(
            settings, regions, runner=_runner_ok, csv_path=csv_x,
            output_dir=out_x24,
            status_write_overrides={output.RESULT_JSON: OSError("注入：原始写入失败")},
            status_io_overrides={output.RESULT_JSON: {
                "unlink": OSError("注入：清理失败")}})
        r24 = st_x24["status_files"][output.RESULT_JSON]
        x24_leftover = safety.leftover_temp_files(out_x24)
        check("X24", "R3-04 临时文件清理失败单独记录，不掩盖原始错误",
              lambda: r24["status"] == "failed"
              and "原始写入失败" in r24["reason"]
              and r24["cleanup_warning"] is not None
              and "清理失败" in r24["cleanup_warning"]
              and len(x24_leftover) == 1)  # 注入模拟清理失败，残留被如实记录

        out_x25 = _prep_run_dir(base, "x25")
        with mock.patch.object(output, "render_result_json",
                               side_effect=ValueError("注入：渲染失败")):
            st_x25 = pipeline.run_once(
                settings, regions, runner=_runner_ok, csv_path=csv_x,
                output_dir=out_x25)
        check("X25", "R3-04 渲染阶段失败也独立隔离，另一个 JSON 继续写入",
              lambda: st_x25["status_files"][output.RESULT_JSON]["status"] == "failed"
              and "渲染失败" in st_x25["status_files"][output.RESULT_JSON]["reason"]
              and st_x25["status_files"][output.LAST_RUN_JSON]["status"] == "updated"
              and all(st_x25["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES))

        # ---- R3-05：lexists / lstat 识别断开符号链接与目录占用 ----
        p_x26 = base / "x26.csv"
        _write_text(p_x26, "STALE-X26\n")
        init_x26 = cfst.prepare_run_csv(p_x26)
        check("X26", "R3-05 普通残留文件 -> 清理后 pre_absent=True",
              lambda: init_x26.ok and init_x26.pre_absent
              and not p_x26.exists() and cfst._entry_kind(p_x26) == "absent")

        sym = _r3_symlink_results(base)
        check("X27", "R3-05 正常符号链接 -> 只删链接本身，目标文件保持原样",
              lambda: sym["normal"] and sym["target_kept"])
        check("X28", "R3-05 断开符号链接 -> lexists 识别为存在且清理后确证不存在",
              lambda: sym["broken"]
              and sym["broken_lexists_before"] is True
              and sym["broken_exists_before"] is False)
        check("X29", "R3-05 目录占用 CSV 路径 -> 拒绝且不递归删除、目录内容不变",
              lambda: sym["dir"] and sym["dir_kept"])

        out_x30 = _prep_run_dir(base, "x30")
        formal_x30 = base / "x30-history.csv"
        _write_text(formal_x30, "X30-KEEP\n")
        old_x30 = _old_bytes(out_x30)
        residual_x30 = cfst.new_run_csv_path(formal_x30, run_id="r3-x30")
        _write_text(residual_x30, "STALE-X30\n")
        x30_calls = []

        def _runner_x30(c, p, t):
            x30_calls.append(1)
            return 0

        st_x30 = pipeline.run_once(
            settings, regions, runner=_runner_x30,
            formal_csv_path=formal_x30, output_dir=out_x30, run_id="r3-x30",
            prepare_unlink_fn=_unlink_denied)
        check("X30", "R3-05 清理失败 -> fail-closed，runner 0 次 / 六 TXT 与历史 CSV 不变",
              lambda: len(x30_calls) == 0
              and st_x30["csv_init_ok"] is False
              and st_x30["failure_stage"] == "csv_init"
              and all((out_x30 / n).read_bytes() == old_x30[n]
                      for n in EXPECTED_RESULT_FILES)
              and formal_x30.read_text(encoding="utf-8") == "X30-KEEP\n"
              and residual_x30.exists())

        out_x31 = _prep_run_dir(base, "x31")
        formal_x31 = base / "x31-history.csv"
        _write_text(formal_x31, "OLD-X31\n")
        residual_x31 = cfst.new_run_csv_path(formal_x31, run_id="r3-x31")
        _write_text(residual_x31, "STALE-X31\n")
        st_x31 = pipeline.run_once(
            settings, regions, runner=_runner_writes(fixture),
            formal_csv_path=formal_x31, output_dir=out_x31, run_id="r3-x31")
        check("X31", "R3-05 残留清理成功后才允许进入生产流程并归档",
              lambda: st_x31["csv_init_ok"] is True
              and st_x31["csv_init_pre_absent"] is True
              and st_x31["csv_fresh"] is True
              and st_x31["csv_archived"] is True
              and formal_x31.read_text(encoding="utf-8") == fixture
              and not os.path.lexists(residual_x31)
              and st_x31["overall_status"] == "success")

        # ---- R3-06：凭据扫描大小写与边界 ----
        secret_cases = _dummy_secret_cases()
        x32 = [safety.contains_secret_markers(c) for c in secret_cases]
        check("X32", "R3-06 大小写/字段名/Bearer/PAT/URL 参数/裸密钥全部被识别",
              lambda: all(x32) and len(x32) == len(secret_cases))

        payload_x33 = output.build_result_payload(
            dict(st_n6, NOT_ALLOWED_FIELD="DUMMY", GH_PAT="DUMMY"))
        payload_x33b = output.build_last_run_payload(
            dict(st_n6, NOT_ALLOWED_FIELD="DUMMY"))
        check("X33", "R3-06 字段白名单之外的字段不会被序列化进两个状态 JSON",
              lambda: "NOT_ALLOWED_FIELD" not in payload_x33
              and "GH_PAT" not in payload_x33
              and "NOT_ALLOWED_FIELD" not in payload_x33b
              and "_FULL_FIELDS" in (APP_DIR / "output.py").read_text(encoding="utf-8")
              and "_LIGHT_FIELDS" in (APP_DIR / "output.py").read_text(encoding="utf-8"))

        target_x34 = base / "x34.json"
        target_x34.write_text("OLD-X34-JSON\n", encoding="utf-8")
        r_x34 = safety.publish_json_file(
            target_x34, '{"note":"TOKEN=DUMMY-VALUE"}\n')
        check("X34", "R3-06 凭据扫描命中 -> 拒绝写入，旧 JSON 字节不变",
              lambda: r_x34["status"] == "failed"
              and "拒绝发布" in r_x34["reason"]
              and target_x34.read_text(encoding="utf-8") == "OLD-X34-JSON\n"
              and safety.leftover_temp_files(base) == [])

        check("X35", "R3-06 失败原因不回显疑似凭据原文；正常状态 JSON 不误报",
              lambda: "DUMMY-VALUE" not in r_x34["reason"]
              and not safety.contains_secret_markers(
                  (out_n6 / output.RESULT_JSON).read_text(encoding="utf-8"))
              and not safety.contains_secret_markers(
                  (out_n6 / output.LAST_RUN_JSON).read_text(encoding="utf-8")))

        # ---- R3-07：生产归档失败不得 success，且不误伤 test_explicit ----
        formal_x36 = base / "x36-history.csv"
        _write_text(formal_x36, "OLD-X36\n")
        out_x36 = _prep_run_dir(base, "x36")
        st_x36 = pipeline.run_once(
            settings, regions, runner=_runner_writes(fixture),
            formal_csv_path=formal_x36, output_dir=out_x36, run_id="r3-x36")
        check("X36", "R3-07 production 归档成功 + 六榜成功 -> overall=success",
              lambda: st_x36["csv_init_source"] == "production"
              and st_x36["archive_expected"] is True
              and st_x36["csv_archived"] is True
              and st_x36["overall_status"] == "success")

        formal_x37 = base / "x37-history.csv"
        _write_text(formal_x37, "X37-HISTORY-KEEP\n")
        out_x37 = _prep_run_dir(base, "x37")

        def _archive_boom(src, dst):
            raise OSError("注入：归档 os.replace 失败")

        st_x37 = pipeline.run_once(
            settings, regions, runner=_runner_writes(fixture),
            formal_csv_path=formal_x37, output_dir=out_x37,
            run_id="r3-x37", archive_replace_fn=_archive_boom)
        full_x37 = json.loads((out_x37 / output.RESULT_JSON).read_text(encoding="utf-8"))
        light_x37 = json.loads((out_x37 / output.LAST_RUN_JSON).read_text(encoding="utf-8"))
        check("X37", "R3-07 production 归档失败 -> 不得 success，六榜不回滚、历史 CSV 不变",
              lambda: st_x37["overall_status"] != "success"
              and st_x37["overall_status"] == "partial"
              and st_x37["csv_archived"] is False
              and st_x37["csv_archive_reason"] is not None
              and "归档 os.replace 失败" in st_x37["csv_archive_reason"]
              and any("CSV 归档失败" in w for w in st_x37["warnings"])
              and all(st_x37["files"][n]["status"] == "updated"
                      for n in EXPECTED_RESULT_FILES)
              and formal_x37.read_text(encoding="utf-8") == "X37-HISTORY-KEEP\n")

        out_x38 = _prep_run_dir(base, "x38")
        formal_x38 = base / "x38-history.csv"
        _write_text(formal_x38, "OLD-X38\n")
        st_x38 = pipeline.run_once(
            settings, regions, runner=_runner_writes(fixture),
            formal_csv_path=formal_x38, output_dir=out_x38, run_id="r3-x38",
            validator_overrides={"SG.txt": _failing_validator})
        check("X38", "R3-07 production 部分榜单失败 -> 维持原有 partial 语义",
              lambda: st_x38["overall_status"] == "partial"
              and st_x38["csv_archived"] is True
              and st_x38["files"]["SG.txt"]["status"] == "failed"
              and len(st_x38["updated_files"]) == 5)

        out_x39 = _prep_run_dir(base, "x39")
        st_x39 = pipeline.run_once(settings, regions, runner=_runner_ok,
                                   csv_path=csv_x, output_dir=out_x39)
        check("X39", "R3-07 test_explicit 无归档 -> 不因 csv_archived=false 被误判",
              lambda: st_x39["csv_init_source"] == "test_explicit"
              and st_x39["archive_expected"] is False
              and st_x39["csv_archived"] is False
              and st_x39["overall_status"] == "success")

        check("X40", "R3-07 两个状态 JSON 均记录 csv_archived=false 与归档失败原因",
              lambda: full_x37["csv_archived"] is False
              and light_x37["csv_archived"] is False
              and full_x37["csv_archive_reason"] is not None
              and light_x37["csv_archive_reason"] is not None
              and full_x37["overall_status"] == "partial"
              and light_x37["overall_status"] == "partial")

        sym_mode = sym["mode"]

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

    r2_items = [r for r in results if not r[0].startswith("X")]
    r3_items = [r for r in results if r[0].startswith("X")]
    print("=== 阶段 %s 离线必测：R2 及更早回归 + R3 新增 X01~X40 ===" % __stage__)
    print("R3 范围: R3-01 证据绑定 / R3-02 source 白名单 / R3-03 freshness 异常收敛 /")
    print("         R3-04 两 JSON 独立持久化 / R3-05 lexists 符号链接 /")
    print("         R3-06 凭据扫描 / R3-07 生产归档失败不得 success")
    print("R3-05 符号链接验证方式: %s" % (
        "真实文件系统（symlink 可用，含断开符号链接）" if sym_mode == "real"
        else "本机不支持创建符号链接 -> 逻辑分支由 _entry_kind 注入覆盖；"
             "真实符号链接必须在 NAS/Linux 侧复验，本机不声称已覆盖"))
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
    r2_failed = [r for r in r2_items if not r[2]]
    r3_failed = [r for r in r3_items if not r[2]]
    print("--- R2 及更早回归: %d 项，通过 %d，失败 %d ---" %
          (len(r2_items), len(r2_items) - len(r2_failed), len(r2_failed)))
    print("--- R3 新增测试: %d 项，通过 %d，失败 %d ---" %
          (len(r3_items), len(r3_items) - len(r3_failed), len(r3_failed)))
    print("--- 通过 %d，失败 %d，跳过 %d，合计 %d ---" %
          (len(results) - len(failed), len(failed), len(skipped), len(results) + len(skipped)))
    print("--- 网络守卫拦截到的连接尝试: %d 次 ---" % len(attempts))
    if attempts:
        print("    %s" % attempts[:3])
    print("--- 临时数据: 全部位于独立 TemporaryDirectory，退出后自动清理 ---")
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

        # ===== R3 新增场景 12~15 =====
        # 场景 12：freshness 文件系统异常真正收敛到 _abort
        print("\n----- 场景 12：R3-03 freshness 文件系统异常收敛（runner 已执行）-----")
        out12 = _prep_run_dir(base, "s12")
        formal12 = base / "s12-history.csv"
        _write_text(formal12, "S12-HISTORY-KEEP\n")
        old12 = _old_bytes(out12)
        s12_calls = []

        def _runner12(c, p, t):
            s12_calls.append(1)
            return 0

        with mock.patch.object(cfst, "csv_is_fresh",
                               side_effect=OSError("注入：stat I/O 错误")):
            st12 = pipeline.run_once(settings, regions, runner=_runner12,
                                     csv_path=csv11s, formal_csv_path=formal12,
                                     output_dir=out12)
        print("  runner 调用次数=%d（已执行）  failure_stage=%s  csv_fresh=%s" %
              (len(s12_calls), st12["failure_stage"], st12["csv_fresh"]))
        print("  failure_reason=%s" % st12["failure_reason"])
        print("  六榜状态=%s  六个旧 TXT 全部保持不变=%s  历史 CSV 不变=%s" %
              ({n: st12["files"][n]["status"] for n in EXPECTED_RESULT_FILES},
               all((out12 / n).read_bytes() == old12[n] for n in EXPECTED_RESULT_FILES),
               formal12.read_text(encoding="utf-8") == "S12-HISTORY-KEEP\n"))
        print("  失败状态 JSON 已落盘=%s  overall=%s" %
              ({n: json.loads((out12 / n).read_text(encoding="utf-8"))[
                    "overall_status"] for n in output.STATUS_JSON_FILES},
               st12["overall_status"]))

        # 场景 13：mkdir / mkstemp 早期失败不阻止另一个 JSON
        print("\n----- 场景 13：R3-04 mkdir / mkstemp 早期失败的独立隔离 -----")
        for tag, kind, message in (("13a", "mkdir", "注入：mkdir 权限错误"),
                                   ("13b", "mkstemp", "注入：mkstemp 磁盘错误")):
            out13 = _prep_run_dir(base, "s" + tag)
            st13 = pipeline.run_once(
                settings, regions, runner=_runner_ok, csv_path=csv11s,
                output_dir=out13,
                status_io_overrides={output.RESULT_JSON: {kind: OSError(message)}})
            print("  %s result.json=%s(%s)  last_run.json=%s  status_persist_state=%s" %
                  (tag, st13["status_files"][output.RESULT_JSON]["status"], kind,
                   st13["status_files"][output.LAST_RUN_JSON]["status"],
                   st13["status_persist_state"]))
            print("      六榜仍全部 updated=%s  临时残留=%s" %
                  (all(st13["files"][n]["status"] == "updated"
                       for n in EXPECTED_RESULT_FILES),
                   safety.leftover_temp_files(out13)))

        # 场景 14：production 归档失败 vs test_explicit 无归档（R3-07 核心对照）
        print("\n----- 场景 14：R3-07 生产归档失败 / 离线测试无归档的状态区分 -----")
        formal14 = base / "s14-history.csv"
        _write_text(formal14, "S14-HISTORY-KEEP\n")
        out14 = _prep_run_dir(base, "s14")

        def _archive_boom14(src, dst):
            raise OSError("注入：归档 os.replace 失败")

        st14 = pipeline.run_once(
            settings, regions, runner=_runner_writes(fixture),
            formal_csv_path=formal14, output_dir=out14,
            run_id="sim-s14", archive_replace_fn=_archive_boom14)
        print("  14a production 归档失败: source=%s archive_expected=%s csv_archived=%s" %
              (st14["csv_init_source"], st14["archive_expected"], st14["csv_archived"]))
        print("      overall_status=%s（不得为 success）  csv_archive_reason=%s" %
              (st14["overall_status"], st14["csv_archive_reason"]))
        print("      六榜仍全部 updated=%s  历史 CSV 未被覆盖=%s" %
              (all(st14["files"][n]["status"] == "updated"
                   for n in EXPECTED_RESULT_FILES),
               formal14.read_text(encoding="utf-8") == "S14-HISTORY-KEEP\n"))
        print("      result.json: csv_archived=%s overall=%s / last_run.json: csv_archived=%s overall=%s" %
              (json.loads((out14 / output.RESULT_JSON).read_text(
                  encoding="utf-8"))["csv_archived"],
               json.loads((out14 / output.RESULT_JSON).read_text(
                   encoding="utf-8"))["overall_status"],
               json.loads((out14 / output.LAST_RUN_JSON).read_text(
                   encoding="utf-8"))["csv_archived"],
               json.loads((out14 / output.LAST_RUN_JSON).read_text(
                   encoding="utf-8"))["overall_status"]))
        out14b = _prep_run_dir(base, "s14b")
        st14b = pipeline.run_once(settings, regions, runner=_runner_ok,
                                  csv_path=csv11s, output_dir=out14b)
        print("  14b test_explicit 无归档: source=%s archive_expected=%s csv_archived=%s overall=%s" %
              (st14b["csv_init_source"], st14b["archive_expected"],
               st14b["csv_archived"], st14b["overall_status"]))

        # 场景 15：R3-01/02/05/06 边界摘要
        print("\n----- 场景 15：R3-01/02/05/06 边界检查摘要 -----")
        p15 = base / "s15.csv"
        _write_fixture(p15)
        ev15 = _prod_evidence(p15)
        print("  15a 合法路径绑定证据: %s" % (cfst.csv_is_fresh(p15, ev15),))
        print("  15b 路径错配证据    : %s" %
              (cfst.csv_is_fresh(p15, _prod_evidence(base / "s15-other.csv")),))
        print("  15c 未知 source     : %s" %
              (cfst.csv_is_fresh(p15, _evidence(p15, source="unknown")),))
        sym15 = _r3_symlink_results(base)
        print("  15d 符号链接验证方式=%s  正常链接=%s 断开链接=%s 目录占用拒绝=%s 目录内容保留=%s" %
              (sym15["mode"], sym15["normal"], sym15["broken"],
               sym15["dir"], sym15["dir_kept"]))
        if sym15["mode"] == "real":
            print("      断开符号链接: lexists(前)=%s  Path.exists(前)=%s（R2 会误判）" %
                  (sym15["broken_lexists_before"], sym15["broken_exists_before"]))
        cases15 = _dummy_secret_cases()
        print("  15e 凭据扫描: %d 个 DUMMY 变体全部命中=%s（不含任何真实凭据）" %
              (len(cases15), all(safety.contains_secret_markers(c) for c in cases15)))

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
        description="cf-ip-optimizer 阶段 4.1-R3（CSV 证据绑定 / 异常收敛 / 状态隔离；不执行真实测速）",
    )
    parser.add_argument("--check-config", action="store_true",
                         help="加载并校验 settings.json / regions.json")
    parser.add_argument("--self-test", action="store_true",
                         help="运行 R2 及更早全部回归项 + R3 新增 X01~X40 离线必测")
    parser.add_argument("--simulate", action="store_true",
                         help="临时目录离线模拟 R2 十一类场景 + R3 新增场景")
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
