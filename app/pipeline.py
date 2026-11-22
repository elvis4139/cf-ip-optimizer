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

4.1-R3 关键修正（R3-03 / R3-04 / R3-07）：

6) freshness / completeness 文件系统异常收敛（R3-03）
   - csv_is_fresh 与 validate_csv_completeness 内部把 OSError 等转成失败结果；
   - run_once 仍对两处调用各自再包一层异常边界，任何异常都进入 _abort，
     记录 csv_fresh=false、failure_stage=csv_fresh（或 csv_complete），
     落盘失败状态 JSON；绝不逃逸 run_once、绝不归档、绝不更新六个 TXT。

7) 两个 JSON 完整独立异常边界（R3-04）
   - 每个文件的「渲染 -> mkdir -> mkstemp -> 写 -> fsync -> 回读 -> json 校验
     -> 凭据扫描 -> os.replace」整条链路各有独立 try/except；
   - 第一个文件在任何一步失败都不阻止第二个文件继续尝试；
   - 部分持久化失败由 status_persist_state=partial、status_files 逐项结果与
     warnings 明确记录；不改写已成功发布的六个 TXT。

8) 生产 CSV 归档失败不得报告 success（R3-07）
   - 仅当 csv_init_source=production 且本轮确实要求归档时，归档失败才把
     overall_status 从 success 降为 partial；
   - test_explicit 离线路径本就不要求归档，不因 csv_archived=false 被误判；
   - 失败原因写入 csv_archive_reason 与 warnings，六榜不回滚、TXT 不破坏。

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
    status_io_overrides       {JSON 文件名: {"mkdir":异常,"mkstemp":异常,
                              "unlink":异常}} 注入 R3-04 早期/清理故障
    archive_replace_fn        注入 production CSV 归档失败（R3-07 测试）
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
               R3-07：production 且本轮要求归档，但 CSV 归档失败时也降为 partial；
    success  : 测速成功、六个榜单全部 updated，且（生产归档要求下）归档成功。

    R3-07 关键：归档是否参与判断由 archive_expected 决定，它只在
    csv_init_source=production 且 should_archive=True 时为 True；
    test_explicit 离线路径 archive_expected=False，绝不因 csv_archived=false
    被误判为失败。不改动 over-all 三态体系，也不重构状态系统。
    """
    if not status["measurement_success"]:
        return "failed"
    updated = [n for n in EXPECTED_RESULT_FILES
               if status["files"].get(n, {}).get("status") == "updated"]
    if len(updated) == len(EXPECTED_RESULT_FILES):
        if status.get("archive_expected") and not status.get("csv_archived"):
            return "partial"
        return "success"
    return "partial" if updated else "failed"


def run_once(settings: dict, regions: dict, *, runner=None, csv_path=None,
             formal_csv_path=None, output_dir=None,
             validator_overrides=None, render_overrides=None,
             replace_overrides=None, replace_fn=None,
             prepare_unlink_fn=None,
             status_write_overrides=None, status_replace_overrides=None,
             status_replace_fn=None, status_io_overrides=None,
             archive_replace_fn=None,
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
    status_io_overrides = status_io_overrides or {}
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
        # R3-07：仅 production + should_archive 时为 True；test_explicit 恒 False
        "archive_expected": False,
        "csv_archive_reason": None,
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
        # R3-04：状态文件整体持久化结果 ok / partial / failed（run_once 返回）
        "status_persist_state": "pending",
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
        """R3-04：result.json / last_run.json 各自拥有【完整独立】的异常边界。

        每个 JSON 的「渲染 -> 父目录创建 -> mkstemp -> 写入 -> fsync -> 回读 ->
        json 校验 -> 凭据扫描 -> os.replace -> 清理」整条链路都在自己的
        try/except 内；第一个文件在任何一步失败都不会阻止第二个继续尝试。
        publish_json_file 内部同样覆盖全流程，形成双重收敛。

        状态 JSON 无法自指记录「本次写入结果」（R2 已确立的原则），因此
        overall_status 不因状态文件自身写入失败而改变；部分持久化失败由
        status_persist_state、status_files 逐项结果与 warnings 明确记录。
        """
        try:
            status["updated_files"] = [
                n for n in EXPECTED_RESULT_FILES
                if status["files"].get(n, {}).get("status") == "updated"
            ]
            status["overall_status"] = overall_status_of(status)
        except Exception as exc:
            status["warnings"].append(
                "状态汇总计算异常（不影响六个 TXT）: %s: %s" %
                (type(exc).__name__, exc))

        def _persist_one(name, renderer) -> dict:
            """单个状态文件的完整流程；异常只属于该文件，绝不外溢到循环。"""
            try:
                content = renderer(status)

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

                io = status_io_overrides.get(name) or {}

                def _io_error(kind, _io=io):
                    err = _io.get(kind)
                    raise (err if isinstance(err, BaseException) else OSError(str(err)))

                mkdir_fn = (lambda parent: _io_error("mkdir")) if "mkdir" in io else None
                mkstemp_fn = (lambda **kw: _io_error("mkstemp")) if "mkstemp" in io else None
                unlink_fn = (lambda path: _io_error("unlink")) if "unlink" in io else None

                return safety.publish_json_file(
                    out_dir / name, content,
                    replace_fn=do_replace, write_fn=write_fn,
                    mkdir_fn=mkdir_fn, mkstemp_fn=mkstemp_fn,
                    unlink_fn=unlink_fn)
            except Exception as exc:
                return {
                    "status": "failed", "size_bytes": None,
                    "reason": "状态 %s 完整流程异常（%s）: %s" %
                              (name, type(exc).__name__, exc),
                    "temp_file": None, "atomic_replace": False,
                    "cleanup_warning": None,
                }

        # 不再有一个覆盖整个循环的外层异常边界；每次迭代都是独立边界
        writes = {}
        for name, renderer in ((output.RESULT_JSON, output.render_result_json),
                              (output.LAST_RUN_JSON, output.render_last_run_json)):
            writes[name] = _persist_one(name, renderer)

        status["status_files"] = writes
        ok = [n for n, info in writes.items() if info.get("status") == "updated"]
        state = "ok" if len(ok) == len(writes) else ("partial" if ok else "failed")
        status["status_persist_state"] = state
        if state != "ok":
            missing = [n for n, info in writes.items()
                       if info.get("status") != "updated"]
            status["warnings"].append(
                "状态 JSON 部分持久化失败（%s；不影响六个 TXT）: 未更新 %s" %
                (state, ", ".join(missing)))

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

    # R3-02：生产流程不得拿到 test_explicit 证据；显式测试路径不得伪造生产证据。
    # 这也是「测试模式不得成为生产证据缺失时的自动回退路径」的显式代码保障。
    expected_source = (cfst.PRODUCTION_SOURCE if auto_csv
                       else cfst.TEST_EXPLICIT_SOURCE)
    if init.source != expected_source:
        return _abort("CSV 初始化证据来源与运行模式不匹配: 期望 %s，实际 %r" %
                      (expected_source, init.source),
                      stage="csv_init", cleanup=False)

    # R3-07：只有 production + 本轮确实要求归档时，归档失败才影响 overall_status。
    status["archive_expected"] = bool(should_archive and auto_csv
                                      and init.source == cfst.PRODUCTION_SOURCE)

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

    # R3-03：csv_is_fresh 内部已把文件系统异常转成失败结果；这里再包一层独立
    # 异常边界，确保任何未预期的异常也收敛到 _abort(stage="csv_fresh")，
    # 绝不逃逸 run_once、绝不归档、绝不更新六个 TXT。
    try:
        fresh, fresh_reason = cfst.csv_is_fresh(run_csv, init)
    except Exception as exc:
        fresh, fresh_reason = False, (
            "freshness 文件系统检查异常（%s）: %s" % (type(exc).__name__, exc))
    status["csv_fresh"] = fresh
    if not fresh:
        return _abort("本轮 CSV 新鲜度校验失败: %s" % fresh_reason,
                      stage="csv_fresh")

    # 同一类边界：完整性校验的文件系统异常也不得逃逸
    try:
        complete, reason, csv_data = cfst.validate_csv_completeness(run_csv)
    except Exception as exc:
        complete, reason, csv_data = False, (
            "CSV 完整性文件系统检查异常（%s）: %s" % (type(exc).__name__, exc)), None
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
    # R3-07：归档失败必须留下 csv_archived=false + 具体失败原因；六榜不回滚。
    if should_archive:
        try:
            formal.parent.mkdir(parents=True, exist_ok=True)
            do_archive = archive_replace_fn or os.replace
            do_archive(str(run_csv), str(formal))
            status["csv_archived"] = True
            status["csv_archive_reason"] = None
        except Exception as exc:
            status["csv_archive_reason"] = "CSV 归档失败（%s）: %s" % (
                type(exc).__name__, exc)
            status["warnings"].append(
                "本轮 CSV 归档失败（不影响六个 TXT）: %s: %s" %
                (type(exc).__name__, exc))
            _cleanup_run_csv()
    else:
        status["csv_archive_reason"] = "本轮为离线测试显式路径，不要求正式 CSV 归档"
        _cleanup_run_csv()

    # --- 阶段 E：两个状态 JSON 独立落盘（P1-2；失败不影响六个 TXT）---
    _persist_status()
    return status
