# 阶段 4.1-R3 代码审查报告（只读导出）

- 授权依据：`STAGE4_1-R3 任务书：CSV 证据校验与状态持久化边界修正.md`
- 本轮授权范围：**仅 R3 源码修正 + 离线测试 + `docs/TASK_BOOK.md` 更新**；不授权 4.2、不授权真实测速、不授权部署操作
- 前置版本：4.1-R2（`4.1.3-r2`）→ 本版：`4.1.4-r3` / `4.1-R3`
- 来源：NAS `/share/Container/cf-ip-optimizer/` 已部署文件；下列源码逐字取自本地同哈希副本（NAS 与本地 SHA256 已双向复核一致）
- 完整测试原始输出：`STAGE4_1_R3_TEST_OUTPUT.txt`（616 行，SHA256=`81ea84e6353acebfd9cddc50e27c8780e7873410e720ea2c5057f0d176a22102`）
- 代码块使用四反引号围栏，避免源码内三反引号字符串影响渲染

## 0 修改前后 SHA256 对照（7 个修改文件）

| 文件 | 大小 | 修改前（= R2 交付基线） | 修改后 |
|---|---:|---|---|
| `app/__init__.py` | 981 B | `b1e3d46372864cdbb7e7252c95e19fa3291afbb37702cb844573934bd83524e1` | `f7ec36ac4c3e9b0cd153931745866ac29ecb11d5d0f83b1318b1641602e139d6` |
| `app/main.py` | 113569 B | `c252219792993cc878631621ee59db6016bbb37ba3a970acca425ff9c4615b62` | `095bbd890c406673bbb9dfb8cdee109d397a1777f2fcaede1042e3a0135ab3df` |
| `app/cfst.py` | 26081 B | `7e9bfcf41e80f18ed2bd0379e07ff4bd9382685f9dbec97ef2d57694ed810860` | `9f8a805f4d59bab318e56a9bb6efc29953b606619c03de6164ef9cd9da9a0532` |
| `app/output.py` | 7454 B | `c22b866a3ded9e4c5bb26c874a942f4bd0f788a4a4f452eff6ffb83b3605d473` | `6760c5d1f56ff352b59b276a864489e57fee114a2bf1e4b37264fd0fbdf32d8a` |
| `app/safety.py` | 13935 B | `5ef487ae663f150448ab00a1c02aaa4c519ed856028f08949d97c9a9f4a90fa9` | `869e9b04f4f4d5ce4c91cf7021c913ca99c85b6ff0acf5a606017eea68f3730b` |
| `app/pipeline.py` | 23256 B | `ad06af7dd3d10edafab548daa645622b6dd30b3f284433aa62dd8c7e4a78561e` | `5f5e97d3a850f51311d38feeb6dc72959abbde2d86453ec02c235c39119b9cb2` |
| `docs/TASK_BOOK.md` | 48199 B | `aa63174b53c26e5851cfb13eb824351c0830ae091adf2ff7ed008d2d5bab1031` | `f8dc8067971a7c5f0bb9c7401fb432a9aa830fcd729745de2e367886ccef0448` |

修改前基线在写入前已逐文件与 NAS 实际哈希核对一致；写入后 NAS 与本地副本双向复核一致。

## 1 NAS 与本地副本 SHA256 最终对照（`verify` 模式，只读）

| 文件 | 本地 SHA256 | NAS SHA256 | 结论 |
|---|---|---|---|
| `app/__init__.py` | `f7ec36ac4c3e9b0cd153931745866ac29ecb11d5d0f83b1318b1641602e139d6` | `f7ec36ac4c3e9b0cd153931745866ac29ecb11d5d0f83b1318b1641602e139d6` | 一致 |
| `app/main.py` | `095bbd890c406673bbb9dfb8cdee109d397a1777f2fcaede1042e3a0135ab3df` | `095bbd890c406673bbb9dfb8cdee109d397a1777f2fcaede1042e3a0135ab3df` | 一致 |
| `app/cfst.py` | `9f8a805f4d59bab318e56a9bb6efc29953b606619c03de6164ef9cd9da9a0532` | `9f8a805f4d59bab318e56a9bb6efc29953b606619c03de6164ef9cd9da9a0532` | 一致 |
| `app/output.py` | `6760c5d1f56ff352b59b276a864489e57fee114a2bf1e4b37264fd0fbdf32d8a` | `6760c5d1f56ff352b59b276a864489e57fee114a2bf1e4b37264fd0fbdf32d8a` | 一致 |
| `app/safety.py` | `869e9b04f4f4d5ce4c91cf7021c913ca99c85b6ff0acf5a606017eea68f3730b` | `869e9b04f4f4d5ce4c91cf7021c913ca99c85b6ff0acf5a606017eea68f3730b` | 一致 |
| `app/pipeline.py` | `5f5e97d3a850f51311d38feeb6dc72959abbde2d86453ec02c235c39119b9cb2` | `5f5e97d3a850f51311d38feeb6dc72959abbde2d86453ec02c235c39119b9cb2` | 一致 |
| `docs/TASK_BOOK.md` | `f8dc8067971a7c5f0bb9c7401fb432a9aa830fcd729745de2e367886ccef0448` | `f8dc8067971a7c5f0bb9c7401fb432a9aa830fcd729745de2e367886ccef0448` | 一致 |

15 个本轮不得修改的文件，在 `source` / `docs` / `verify` 三次操作中均做过哈希核对，全部与 R2 基线一致：

```
app/config.py                                    6a0db6b78c820548c5117214157dedea124d39ce5c6bae5a9aca0d1a21ffada2
app/ranking.py                                   8be5c3ef412634f5f42633c48821f02e21b61124665c72ac04ab09ec0df7552f
app/region.py                                    4ddb1f8c03e9a29ff8c3ac361e6921d64dc794905b21ca1f24f16db5465b78b1
config/settings.json                             750b9fedde2b1f4519f996007286b951482deaa54eb90d5a5ec64d3c5f0a00e0
config/regions.json                              998745250d900520000599da43b3c1f4ef59e92a077984295079b771e8d7f83a
Dockerfile                                       2df92118e23aeb94252527cf37a892de229fd65aa822be331871fbc6cb234b42
compose.yaml                                     e1b8a795073d189b07aa75e438c65299788591e74be6e7c855e5a2290a0f20b1
.dockerignore                                    75750ad633da57a4225051d8bec39322db408b2edf494b9053b8a91c519f4792
bin/cfst_linux_amd64.tar.gz                      c4c8fc76b4e1bf2bdb5ced8b765956d82dda7bc4eb59df5c04053f0f7db98d90
samples/phase2-colo-filter-sin-lax.csv           bb92287b95982df91b304f09de176e76e2634b462afaa69217cddb8e5f25039f
samples/phase2-download-108.csv                  8bd9e10fc86dda0ede76593201b8f91dcef676ae43ff96e962db1f441d30abc8
samples/phase2-download-3ip.csv                  2eb6b5e6b5edae01b090a333872092bd250705ad3d1a4db72bc4f52419773ada
samples/phase2-download-cloudflare-108.csv       1daf346d6a0e4f33dab1aed8bd1d95ad912d45f3092ee44ea267a1a1b807e0a7
samples/phase2-robots-104.csv                    0d6cc410ccc082b21fd9faf5bfdaaceb150873bb12bbf37040646caea00778eb
samples/phase2-robots-colo-sample.csv            b2327964fb0473715e68bf6cd67c86cbcd57754374d62aca5b68fdf73a867e6c
```

## 2 文件变更清单

**修改 7 个（均为 R2 已有文件，无新增应用源码）**

- `app/__init__.py`
- `app/main.py`
- `app/cfst.py`
- `app/output.py`
- `app/safety.py`
- `app/pipeline.py`
- `docs/TASK_BOOK.md`

**未修改（明确标注，不为凑数触碰）**：`app/config.py`、`app/ranking.py`、`app/region.py`、
`config/settings.json`（业务参数一个未动）、`config/regions.json`（地区映射未动）、
`Dockerfile`、`compose.yaml`、`.dockerignore`、CFST 二进制与 6 份 `samples/*.csv`。
六个 TXT 的文件名、格式、排名规则、发布策略与 `publish_one()` 均未改动。

**本地辅助交付脚本（非应用源码，未部署到 NAS）**：`nas_stage4_1/deploy_4_1_r3.py`
（SHA256=`289867e8f45b81cfcdaff0aa2d1097e69bc4a0bef6caba3b1ce4b9b0ad963f05`）；仅用于 SSH 逐文件写入、修改前基线核对与写入后双向 SHA256 复核，
不参与运行时代码，密码只从环境变量 `NAS_PWD` 读取、不落盘、不打印。

**本地交付文件**：`STAGE4_1_R3_TEST_OUTPUT.txt`、`STAGE4_1_R3_CODE_REVIEW.md`（本报告）、
`STAGE4_1-R3 任务书：CSV 证据校验与状态持久化边界修正.md`（用户提供，未修改）。

## 3 完整测试命令（NAS / Python 3.11.2）

```sh
PY=/share/CACHEDEV2_DATA/.qpkg/CacheMount/python/bin/python3.11
ROOT=/share/Container/cf-ip-optimizer; cd "$ROOT"
"$PY" --version
"$PY" -m compileall -q app
"$PY" -m app.main --check-config; echo "COMMAND_EXIT=$?"
"$PY" -m app.main --self-test;    echo "COMMAND_EXIT=$?"
"$PY" -m app.main --simulate;     echo "COMMAND_EXIT=$?"
"$PY" -m app.main --run;          echo "COMMAND_EXIT=$?"
ls -la data logs; find data logs -type f | sort
sha256sum samples/* | sort
sha256sum app/*.py config/*.json docs/TASK_BOOK.md
```

## 4 完整测试输出

- 路径：`STAGE4_1_R3_TEST_OUTPUT.txt`（工作区根目录）
- 行数：616；SHA256：`81ea84e6353acebfd9cddc50e27c8780e7873410e720ea2c5057f0d176a22102`
- 内容：A 解释器/编译、B `--check-config`、C `--self-test` 逐项、D `--simulate` 全场景含两个状态 JSON 全文、
  E `--run` 阶段边界、F `data/`/`logs/`/`samples/` 状态、G 源码与配置 SHA256、H 阶段边界声明。
- 远端 `REMOTE_EXIT_CODE=0`；SSH 登录提示 `Could not chdir to home directory /share/homes/HAKU` 为既有环境提示，非测试失败。

## 5 R2 原有测试回归结果

| 项目 | 结果 |
|---|---|
| `compileall`（9 个 `.py`） | 全部通过 |
| `--check-config` | exit 0（版本 `4.1.4-r3`） |
| R2 及更早回归自测 | **65 项，通过 65，失败 0** |
| R2 原有 2 项 SKIP | S01 真实 CFST/真实 CSV 单位 → 4.4；S02 容器 Python 3.12 / 0o600 读取权限 → 4.2；**原因保持，未伪通过** |
| 网络守卫 | 拦截到的连接尝试 0 次 |
| `--run` | exit 2，明确拒绝 |

**N04 的适配说明**：R3 把证据对象升级为「路径绑定票据」后，R2 中手工构造的裸字符串 `"t"` 已不再合法。
N04 改为用 `dataclasses.replace` 基于 `prepare_run_csv()` 生成的本轮真实证据构造字段变体，
四个子断言（无证据 / 初始化失败 / 缺前置证据 / 合法证据）语义与强度完全不变，
没有删除、跳过或弱化任何旧测试。其余 64 项一行未改。

## 6 R3 新增测试逐项结果（X01~X40，全部 PASS）

| 编号 | 对应条目 | 测试目的 | 结果 |
|---|---|---|---|
| X01 | R3-01 | 正确 token + 正确路径 + 本轮证据 -> 通过 | PASS |
| X02 | R3-01 | token 缺失 / 伪造 / R2 裸字符串票据 -> 一律拒绝 | PASS |
| X03 | R3-01 | 证据 bound_path 与当前 CSV 路径不匹配 -> 拒绝 | PASS |
| X04 | R3-01 | 其它运行/其它路径产生的证据不得用于本轮 -> 拒绝 | PASS |
| X05 | R3-01 | 同一证据禁止重复使用（第二次即拒绝） | PASS |
| X06 | R3-01 | 生产流程拿到绑定到其它路径的证据 -> freshness 拒绝、六榜不更新 | PASS |
| X07 | R3-02 | production 合法证据（含 pre_absent）-> 通过 | PASS |
| X08 | R3-02 | test_explicit 合法离线路径 -> 通过且标注非生产 | PASS |
| X09 | R3-02 | None / 空串 / 未知 / 大小写变体 / 非字符串 source 全拒绝 | PASS |
| X10 | R3-02 | production 缺 pre_absent / test_explicit 携带生产证明 -> 拒绝 | PASS |
| X11 | R3-02 | 生产流程不得使用 test_explicit 分支（runner 0 次、立即终止） | PASS |
| X12 | R3-03 | is_file() 抛 OSError -> 返回明确失败，不向外抛异常 | PASS |
| X13 | R3-03 | stat() 抛 OSError -> 返回明确失败，不向外抛异常 | PASS |
| X14 | R3-03 | CSV 路径被删除/替换为目录 -> 新鲜度拒绝 | PASS |
| X15 | R3-03 | runner 已执行但 freshness 异常 -> 收敛到 _abort（不归档） | PASS |
| X16 | R3-03 | 完整性校验文件系统异常也收敛到 _abort(csv_complete) | PASS |
| X17 | R3-04 | result.json 的 mkdir 失败 -> last_run.json 仍继续并成功 | PASS |
| X18 | R3-04 | result.json 的 mkstemp 失败 -> last_run.json 仍继续并成功 | PASS |
| X19 | R3-04 | last_run.json 写入失败 -> result.json 正常更新 | PASS |
| X20 | R3-04 | 单文件 replace 失败 -> 该旧 JSON 字节不变，另一文件仍更新 | PASS |
| X21 | R3-04 | 两个 JSON 均失败 -> 分别记录各自原因，状态为 failed | PASS |
| X22 | R3-04 | 两个 JSON 均成功 -> 合法 JSON + 原子替换 + 无残留 | PASS |
| X23 | R3-04 | 部分持久化失败由 status_persist_state / warnings 明确记录 | PASS |
| X24 | R3-04 | 临时文件清理失败单独记录，不掩盖原始错误 | PASS |
| X25 | R3-04 | 渲染阶段失败也独立隔离，另一个 JSON 继续写入 | PASS |
| X26 | R3-05 | 普通残留文件 -> 清理后 pre_absent=True | PASS |
| X27 | R3-05 | 正常符号链接 -> 只删链接本身，目标文件保持原样 | PASS |
| X28 | R3-05 | 断开符号链接 -> lexists 识别为存在且清理后确证不存在 | PASS |
| X29 | R3-05 | 目录占用 CSV 路径 -> 拒绝且不递归删除、目录内容不变 | PASS |
| X30 | R3-05 | 清理失败 -> fail-closed，runner 0 次 / 六 TXT 与历史 CSV 不变 | PASS |
| X31 | R3-05 | 残留清理成功后才允许进入生产流程并归档 | PASS |
| X32 | R3-06 | 大小写/字段名/Bearer/PAT/URL 参数/裸密钥全部被识别 | PASS |
| X33 | R3-06 | 字段白名单之外的字段不会被序列化进两个状态 JSON | PASS |
| X34 | R3-06 | 凭据扫描命中 -> 拒绝写入，旧 JSON 字节不变 | PASS |
| X35 | R3-06 | 失败原因不回显疑似凭据原文；正常状态 JSON 不误报 | PASS |
| X36 | R3-07 | production 归档成功 + 六榜成功 -> overall=success | PASS |
| X37 | R3-07 | production 归档失败 -> 不得 success，六榜不回滚、历史 CSV 不变 | PASS |
| X38 | R3-07 | production 部分榜单失败 -> 维持原有 partial 语义 | PASS |
| X39 | R3-07 | test_explicit 无归档 -> 不因 csv_archived=false 被误判 | PASS |
| X40 | R3-07 | 两个状态 JSON 均记录 csv_archived=false 与归档失败原因 | PASS |

合计 **40 项，通过 40，失败 0**。所有用例都在独立 `TemporaryDirectory` 内，
零网络、零真实 CFST、零 Docker、零 NAS 外部服务依赖。

### 用户特别强调的三处，逐条给出收敛证据

1. **R3-03 异常必须真正收敛到失败处理路径（不只是补测试）**：
   `csv_is_fresh` 内部把 `is_file`/`stat` 异常转成 `(False, "freshness 文件系统检查异常…")`；
   `run_once` 再对 freshness 与 completeness 各包一层独立异常边界。X12/X13 验证异常不外抛；
   X15 在真实的 production 归档路径上让 runner **已执行 1 次并写出本轮 CSV**，
   再注入 `stat I/O 错误`，断言 `failure_stage=csv_fresh`、`csv_fresh=false`、
   `csv_archived=false`、本轮一次性路径已清理、六榜全部 `skipped`、正式历史 CSV 与六个旧 TXT 字节不变、
   两个失败状态 JSON 均落盘且 `overall_status=failed`。场景 12 给出同样的完整输出。
   X16 验证完整性校验异常收敛到 `_abort(stage="csv_complete")`。
   开发中还实际捕获并修掉一个逃逸案例：非法 `source=[]` 曾使 `in frozenset` 抛 `TypeError`，
   现改为先判类型再查白名单，X09 覆盖该边界。
2. **R3-04 两个 JSON 全流程独立隔离**：`publish_json_file` 的 `mkdir`/`mkstemp` 已移入内部 try；
   `_persist_status` 取消了覆盖整个循环的外层 try，改为每个文件一条完整独立边界。
   X17（mkdir 失败）、X18（mkstemp 失败）、X19（末位写入失败）、X20（replace 失败）、
   X21（两者全失败）、X24（清理失败）、X25（渲染失败）逐一证明第一个文件在**任何一步**失败都不阻止第二个继续尝试；
   X23 断言 `status_persist_state=partial` 且 `warnings` 明确记录；X22 验证两者均成功时 JSON 合法、原子替换、无残留。
   场景 13 给出 `13a/13b` 的完整打印。
3. **R3-07 必须区分 production 归档与 test_explicit**：`archive_expected` 仅在
   `csv_init_source=production` 且 `should_archive=True` 时为真，`overall_status_of()` 不用通用判断。
   X36（production 归档成功 → success）、X37（production 归档失败 → partial + 六榜不回滚 + 历史 CSV 不变）、
   X38（production 部分榜单失败 → 维持 partial）、X39（test_explicit 无归档 → 仍 success）构成四态对照；
   X40 验证两个状态 JSON 都记录了 `csv_archived=false` 与具体 `csv_archive_reason`。
   场景 14 的 `14a/14b` 把两种路径并列打印，可直接比对。

## 7 模拟场景结果（`--simulate`，exit 0）

| 场景 | 结果 |
|---|---|
| R2 原有 1~11（六榜生成、单榜失败、测速失败、CSV 不完整、空榜、原子替换、新鲜度、渲染/写入失败、数量边界、本轮独立 CSV 归档、初始化 fail-closed、两 JSON 落盘隔离） | 全部保留并通过 |
| 12（R3-03）freshness 文件系统异常收敛 | runner 已执行 1 次 → `failure_stage=csv_fresh`、六榜 skipped、历史 CSV/六 TXT 不变、失败状态 JSON 已落盘 |
| 13（R3-04）mkdir / mkstemp 早期失败隔离 | 13a/13b 均 `result.json=failed`、`last_run.json=updated`、`status_persist_state=partial`、六榜仍全 updated、临时残留 `[]` |
| 14（R3-07）生产归档失败 vs 离线测试无归档 | 14a `production`: `csv_archived=false`、`overall=partial`、六榜不回滚、历史 CSV 未被覆盖；14b `test_explicit`: `csv_archived=false`、`overall=success` |
| 15（R3-01/02/05/06）边界摘要 | 合法绑定证据通过、路径错配拒绝、未知 source 拒绝、符号链接 `mode=real`（含断开链接）、20 个 DUMMY 凭据变体全部命中 |

R3-05 符号链接在 NAS/Linux 侧为**真实文件系统验证**：输出明确写到
`R3-05 符号链接验证方式: 真实文件系统（symlink 可用，含断开符号链接）`，
且 `15d` 打印 `断开符号链接: lexists(前)=True  Path.exists(前)=False（R2 会误判）`。
本机 Windows 无创建符号链接权限时，同一用例由 `_entry_kind` 注入覆盖逻辑分支，
并在输出中明确标注「真实符号链接必须在 NAS/Linux 侧复验，本机不声称已覆盖」。

## 8 `data/`、`logs/`、`samples/` 变化情况

- `data/`、`logs/` **仍为空目录**：`ls -la` 显示仅 `.` / `..`，`find data logs -type f` 无输出。
  未生成六个正式 TXT、`result.json`、`last_run.json` 或正式 `data/result.csv`。
- `samples/` 仍为 6 个文件，SHA256 与 R2 基线逐个一致（见输出 F 段）。
- `compileall` 仅在 `app/__pycache__/` 产生字节码缓存，未改动任何源码、配置、历史 CSV 或正式输出。

## 9 未完成事项 / 未覆盖边界 / 风险

1. **状态 JSON 自指限制**：状态文件无法记录「本次自身写入结果」，部分持久化失败只记录在
   `run_once` 返回的 `status_persist_state` / `status_files` / `warnings` 中，不写进两个 JSON。
   这是沿用 R2 已确立的原则（避免自指不一致），若后续要求 JSON 内自指需单独设计并授权。
2. **`publish_one()`（六个 TXT）的同类边界**：其 `mkdir`/`mkstemp` 仍位于内部 try 之外，
   但 `pipeline` 的单榜 `try/except` 已把异常收敛为单榜 `failed`、不会逃逸 `run_once`。
   按最小修改原则本轮未改动，列为待确认边界。
3. **进程内 HMAC 票据边界**：票据只在同进程同轮有效，可防止跨轮/跨路径伪造；不提供跨进程持久化校验（当前架构不需要）。
4. **P1-3 防重入**：进程锁/文件锁、前次未结束则跳过、异常退出锁恢复、两并发实例测试尚未实现，正式调度前必须补齐。
5. **阶段 4.2（未授权）**：容器 Python 3.12、UID 1000/GID 0、只读根文件系统、0o600 能否被真实消费者读取。0o600 不得擅自放宽。
6. **阶段 4.3（未授权）**：`-dn 100` 合理性、超时/并发 NAS 负载、Docker bridge 出口、路由器透明代理。容器内代理变量为空不能证明透明代理不存在。
7. **阶段 4.4（未授权）**：单次完整真实 CFST、真实 CSV 丢包率单位、Colo 稳定性、MB/s 单位、地区覆盖与耗时。
8. **地区映射补全**：仍只有 `SIN→SG`、`LAX→US`；HK/JP/KR 空、DEN 待确认、AMS/N/A 排除，禁止猜测。
9. **正式发布链路**：六个 TXT 正式发布、GitHub 仓库与 Raw 订阅、EdgeTunnel 六订阅、每日 06:00/12:00/18:00 定时、Server 酱推送、`logs/` 独立日志归档 —— 全部未执行。
10. **SSH 凭据安全**：建议用户尽快改密或改用公钥认证；本轮未把任何凭据写入文件、任务书、日志、脚本或输出。

## 10 最终声明

**本次没有执行真实测速、没有扫描真实 Cloudflare IP、没有访问外网测速或下载、
没有构建/重建/启动/停止容器、没有运行 `docker compose`、没有创建或修改 Cron 与自动重启策略、
没有连接 GitHub / 创建 PAT / 上传文件、没有配置 Server 酱或 SendKey、
没有修改 EdgeTunnel / Pages / Worker、没有修改 Docker 网络 / 代理 / 路由器 / NAS 系统设置、
没有删除历史 CSV / samples / 日志 / 正式输出。**

`execute_cfst` 仍为拒绝占位，`--run` 仍返回 exit 2。R3 完成后**停止在阶段 4.1**，
等待 ChatGPT 依据本报告源码全文、哈希与完整测试输出做只读验收，再单独决定是否授权 4.2。

## 11 修改后关键源码全文（7 个修改文件 + 2 个未改配置，逐字取自本地同哈希副本）

### `app/__init__.py` — 22 行，981 B，sha256=f7ec36ac4c3e9b0cd153931745866ac29ecb11d5d0f83b1318b1641602e139d6

````
"""cf-ip-optimizer 自动测速程序（阶段 4.1 修订版：单轮测速 / 六榜独立发布）。

本阶段只做代码架构修订与离线测试：
不执行真实测速、不发网络请求、不启动容器、不创建 Cron、不上传 GitHub、
不修改 EdgeTunnel、不更新正式订阅文件。

已废弃的旧两轮逻辑（HTTPing 初筛 + 按地区分别下载）不得再出现：
任何模块都不得构造第二条 CFST 命令，也不得读取第二轮 Colo 做分类。
"""

from __future__ import annotations

__version__ = "4.1.4-r3"
__stage__ = "4.1-R3"

# 4.1-R3：CSV 证据绑定 / source 白名单 / freshness 异常收敛 / 两 JSON 独立
# 异常边界 / lexists 识别断开符号链接 / 凭据扫描补强 / 生产归档失败不得 success。
# 阶段边界不变：仍禁止真实测速、容器启动、Cron、GitHub 与任何外部发布。

__all__ = [
    "config", "cfst", "region", "ranking", "output", "safety", "pipeline", "main",
]
````

### `app/main.py` — 2126 行，113569 B，sha256=095bbd890c406673bbb9dfb8cdee109d397a1777f2fcaede1042e3a0135ab3df

````
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
````

### `app/cfst.py` — 552 行，26081 B，sha256=9f8a805f4d59bab318e56a9bb6efc29953b606619c03de6164ef9cd9da9a0532

````
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
````

### `app/output.py` — 172 行，7454 B，sha256=6760c5d1f56ff352b59b276a864489e57fee114a2bf1e4b37264fd0fbdf32d8a

````
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
````

### `app/safety.py` — 294 行，13935 B，sha256=869e9b04f4f4d5ce4c91cf7021c913ca99c85b6ff0acf5a606017eea68f3730b

````
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
````

### `app/pipeline.py` — 471 行，23256 B，sha256=5f5e97d3a850f51311d38feeb6dc72959abbde2d86453ec02c235c39119b9cb2

````
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
````

### `docs/TASK_BOOK.md` — 1122 行，48199 B，sha256=f8dc8067971a7c5f0bb9c7401fb432a9aa830fcd729745de2e367886ccef0448

````
# QNAP Cloudflare IP 优选系统：WorkBuddy 分阶段实施任务书

**项目名称：** cf-ip-optimizer  
**目标平台：** QNAP TS-453Dmini / QTS  
**项目目录：** `/share/Container/cf-ip-optimizer/`  
**执行方式：** WorkBuddy 分阶段实施，ChatGPT 负责阶段审查与验收，用户负责 NAS SSH 操作和最终授权。

---

# 第一部分：项目最终目标与不可变更要求

## 1.1 核心目标

在 QNAP NAS 上部署 Cloudflare IPv4 自动测速与优选系统。

每天北京时间 06:00、12:00、18:00 自动运行。

每次只执行一次完整 CFST 测速，从同一份完整测速结果中生成六个独立 TXT 文件，供 EdgeTunnel 的原生自定义优选 IP API 分别订阅。

六个文件：

| 文件名 | 内容 | 数量上限 |
|---|---|---:|
| HK.txt | 香港优选 IP | 5 |
| JP.txt | 日本优选 IP | 5 |
| SG.txt | 新加坡优选 IP | 5 |
| KR.txt | 韩国优选 IP | 5 |
| US.txt | 美国优选 IP | 5 |
| global_top25.txt | 全部有效候选 IP 全球排名 | 25 |

合计最多 50 条记录。

不同 TXT 之间允许出现相同 IP，不去重、不合并。

EdgeTunnel 由用户自行添加六条独立订阅地址，并由 EdgeTunnel 自身处理重复节点。

## 1.2 已确认的技术环境

以下信息已完成前期检查，不要重复安装或擅自修改：

- NAS：QNAP TS-453Dmini
- QTS：5.2.11
- Docker：27.1.2-qnap8
- 系统架构：x86_64 / amd64
- CFST：XIU2/CloudflareSpeedTest v2.3.5
- Compose：v2.29.1-qnap2
- 项目目录：`/share/Container/cf-ip-optimizer/`
- CFST 程序：`bin/cfst_linux_amd64/cfst`
- 基础镜像：`python:3.12-slim-bookworm`
- 容器运行用户：UID 1000 / GID 0
- Docker Compose 文件：`compose.yaml`
- Dockerfile：`Dockerfile`

已经通过的前置阶段：

- 阶段0：NAS 环境检查
- 阶段1：Docker bridge 出口验证
- 阶段2：CFST 安装和 HTTPing/下载测试能力验证
- 阶段3.1～3.6：容器基础环境、权限、网络和镜像构建验证
- 阶段4.0：项目代码目录和配置审计

以上阶段不得重复进行无必要的系统修改。

## 1.3 不可违反的原则

1. 每次运行只执行一次完整 CFST 测速。
2. 不允许拆成 HTTPing 初筛和下载测速两轮。
3. 不允许按地区分别启动多次测速。
4. 六个 TXT 独立生成、独立校验、独立更新。
5. 一个 TXT 更新失败，不得阻止其他 TXT 更新。
6. 不跨文件去重，不生成合并文件。
7. 全球榜允许包含未知 Colo 的有效 IP。
8. 地区榜只能使用已经确认的 Colo 映射。
9. 下载速度单位始终是 MB/s，不得混用 Mbps。
10. 任何阶段都不得擅自修改 EdgeTunnel 原有项目或其他 NAS 容器。
11. 每个阶段完成后必须暂停，等待用户验收和授权。
12. 不得将尚未验证的结果描述为已完成。

---

# 第二部分：最终测速和排名设计

## 2.1 每次只运行一次完整 CFST

使用 CFST v2.3.5 对完整 Cloudflare IPv4 候选地址段进行一次测速。

采用普通 TCPing + 下载测速模式。

主要参数：

- 不使用 `-httping`
- 不使用 `-httping-code`
- 不使用 `-dd`
- 不使用 `-cfcolo`
- 使用完整 IPv4 地址段文件 `ip.txt`
- 使用 TCP 443
- 使用官方 Cloudflare 下载测试地址：

`https://speed.cloudflare.com/__down?bytes=10000000`

- 保留并发、延迟次数、下载次数、下载时长等可配置参数。
- 一次运行只产生一份完整 CFST CSV。

建议初始配置沿用：

| 参数 | 初始值 |
|---|---:|
| concurrency | 20 |
| latency count | 4 |
| download count | 5 |
| download duration | 10 秒 |
| port | 443 |
| download URL | Cloudflare 官方测速地址 |

这些参数允许后续根据 NAS 负载和实际测速时间调整，但不得改变单轮测速原则。

**注意：** 阶段2曾经验证 CFST 普通下载模式能够产生下载速度和 Colo 数据，但正式运行前仍需在阶段4.2确认完整 CSV 字段、地区码和丢包率单位。

## 2.2 一份 CSV 生成六个榜单

数据流：

完整 IPv4 地址段
→ 一次 CFST 测速
→ 一份完整 CSV
→ 解析全部有效记录
→ 根据 Colo 映射地区
→ 排序
→ 生成六个 TXT
→ 六个文件分别校验和更新。

不再建立第一轮和第二轮映射。

不再建立两轮 CSV 对照关系。

不再重复测速。

## 2.3 排名规则

六个榜单统一按照以下顺序排序：

1. 下载速度 MB/s：降序，越快越靠前。
2. 平均延迟 ms：升序，越低越靠前。
3. 丢包率：升序，越低越靠前。

有效记录必须满足：

- IP 地址合法。
- 下载速度大于 0。
- 延迟是有效有限数值。
- 丢包率是有效有限数值。
- 不允许 NaN。
- 不允许 Infinity。
- 不允许负数。
- 不允许将 N/A 速度当作有效记录。

如果排序字段完全相同，可以使用 IP 地址作为最后的稳定排序条件。

全球榜取全部有效候选中的 Top 25，不限制地区归属。

地区榜只取已经确认属于对应地区的有效 IP。

地区榜不足5条时输出实际数量，不允许其他地区 IP 凑数。

---

# 第三部分：地区识别与节点输出格式

## 3.1 地区识别

使用本轮 CFST CSV 中的地区码 Colo 进行地区归类。

当前已有真实证据：

| Colo | 地区 | 当前状态 |
|---|---|---|
| SIN | SG | 已有多次测试证据 |
| LAX | US | 已有多次测试证据，但美国列表不完整 |
| DEN | 未确认 | 待核实 |
| AMS | 未确认 | 暂不纳入 |
| N/A | 未知 | 排除地区归类 |

HK、JP、KR 目前没有确认的 Colo 映射。

禁止根据 IP 地址或网络常识自动猜测国家。

以后发现新的 Colo，先记录真实测试结果，提供给用户确认后才能加入 `regions.json`。

地区映射建议使用独立配置文件维护：

`config/regions.json`

要求：

- HK、JP、SG、KR、US 五个地区固定存在。
- 每个地区允许包含多个已确认 Colo。
- 一个 Colo 只能属于一个地区。
- 不允许已确认、待确认、排除三类配置互相冲突。
- 未确认 Colo 一律归类为 UNKNOWN。

## 3.2 节点 TXT 格式

每行采用以下格式：

`172.64.150.190:443#SG-Singapore-SIN-92ms`

格式：

`IP:443#地区代码-英文地区名称-Colo-延迟毫秒数`

固定地区英文名称：

| 地区代码 | 英文名称 |
|---|---|
| HK | HongKong |
| JP | Japan |
| SG | Singapore |
| KR | SouthKorea |
| US | UnitedStates |

示例：

`172.64.150.190:443#SG-Singapore-SIN-92ms`

`104.16.0.1:443#US-UnitedStates-LAX-202ms`

延迟取 CFST 平均延迟，四舍五入为整数毫秒。

下载速度参与排名，但不写入节点备注。

全球榜允许未知地区节点。未知节点使用明确格式：

`172.64.150.190:443#UNKNOWN-Unknown-DEN-92ms`

不能把未知节点伪装成某个国家。

地区榜不允许出现 UNKNOWN。

---

# 第四部分：六个文件独立更新机制

## 4.1 文件列表

固定六个文件：

- HK.txt
- JP.txt
- SG.txt
- KR.txt
- US.txt
- global_top25.txt

不生成：

- merged.txt
- global_top15.txt
- 任何合并订阅文件

## 4.2 独立发布原则

六个文件各自生成、各自校验、各自更新。

例如：

HK 成功 → 更新 HK.txt。

JP 成功 → 更新 JP.txt。

SG 失败 → 保留旧 SG.txt。

KR 成功 → 更新 KR.txt。

US 成功 → 更新 US.txt。

全球榜成功 → 更新 global_top25.txt。

任何单个文件失败，不得阻止其他文件更新。

## 4.3 原子更新

每个 TXT 使用单文件原子更新：

1. 生成临时文件。
2. 写入完整内容。
3. 校验文件格式、行数、IP、备注和排名。
4. 校验成功后使用同文件系统 `os.replace()` 替换正式文件。
5. 校验失败时删除临时文件，保留旧正式文件。

不再需要六文件整体原子切换。

不再需要 current symlink 版本指针事务。

## 4.4 空榜处理

需要严格区分两种情况：

**情况A：完整测速成功，某地区没有有效节点。**

该地区 TXT 应更新为空文件，不能保留上次旧节点。

**情况B：文件生成、写入或校验发生异常。**

只保留该文件上次成功版本。

如果完整 CFST 测速本身失败或 CSV 不完整，则不更新任何榜单，保留全部旧文件。

## 4.5 运行状态记录

每次运行记录：

- 运行时间
- CFST 退出码
- CSV 是否完整
- CSV 总记录数
- 有效 IP 数量
- 六个文件分别生成的节点数
- 六个文件分别更新成功或失败的状态
- 失败原因
- 本次最快节点

不得因为一个文件失败而把整个运行标记为全部失败。

---

# 第五部分：项目实施阶段与验收标准

## 阶段4.1：代码架构修订和离线测试

### 工作内容

在现有项目上修改代码，使其完全符合本任务书。

重点文件：

- `app/config.py`
- `app/cfst.py`
- `app/region.py`
- `app/ranking.py`
- `app/output.py`
- `app/safety.py`
- `app/main.py`
- `config/settings.json`
- `config/regions.json`

可以根据实际架构新增模块，但不得无必要重写已经验证的 Docker 环境。

必须删除或废弃旧两轮测速逻辑。

### 必须完成的测试

1. 只构造一条完整 CFST 测速命令。
2. 命令不包含 `-httping`。
3. 命令不包含 `-dd`。
4. 命令不包含 `-cfcolo`。
5. 命令使用官方 Cloudflare 下载地址。
6. 命令使用完整 IPv4 文件。
7. SIN 正确归类 SG。
8. LAX 正确归类 US。
9. DEN、AMS、N/A、未知代码不能自动归类。
10. 未知 Colo 的有效 IP 可以进入全球榜。
11. 未知 Colo 不能进入地区榜。
12. 全球榜数量上限25。
13. 地区榜数量上限5。
14. 排序规则正确。
15. 速度为0的记录排除。
16. NaN、Infinity、负数排除。
17. 非法 IP 排除。
18. 丢包率单位和计算正确。
19. 六个文件允许出现重复 IP。
20. 不生成 merged.txt。
21. 六个文件格式正确。
22. 单个文件更新失败不影响其他文件。
23. 单个文件更新失败保留旧文件。
24. 成功测速但地区空榜时输出空文件。
25. 完整测速失败时所有旧文件不变。
26. 文件使用临时文件及 os.replace()。
27. 运行状态正确记录六个文件的独立结果。
28. 配置检查通过。

### 严禁事项

- 不运行真实测速。
- 不执行网络扫描。
- 不创建 Cron。
- 不上传 GitHub。
- 不修改 EdgeTunnel。
- 不启动或重建 Docker 容器。
- 不修改现有 NAS 系统设置。

### 验收标准

WorkBuddy 提交：

- 修改文件清单。
- 修改前后 SHA256。
- 完整自测结果。
- 六个文件模拟生成结果。
- 单文件失败测试。
- 完整测速失败测试。
- 空榜测试。
- 原子替换测试。
- 确认没有执行真实网络请求。

所有测试通过后暂停，等待用户验收。

---

## 阶段4.2：容器内离线集成测试

### 工作内容

使用现有 Docker Compose 构建的镜像和现有项目环境，验证修改后的程序。

只进行离线测试。

要求：

- 使用容器 Python 3.12。
- 使用模拟 CSV，不运行真实 CFST。
- 不连接外网。
- 不扫描 Cloudflare IP。
- 不更新正式订阅文件。
- 不创建定时任务。
- 不上传 GitHub。

验证：

1. 配置文件读取。
2. CSV 解析。
3. 地区映射。
4. 六榜排序。
5. TXT 输出。
6. 单文件原子更新。
7. 单文件失败隔离。
8. 日志和运行状态。
9. 容器非 root 权限。
10. 只读根文件系统和目录权限。

### 验收标准

- 容器内自测全部通过。
- 无真实测速网络请求。
- 无正式文件更新。
- 无权限错误。
- 提交容器日志和测试报告。

完成后暂停，等待验收。

---

## 阶段4.3：真实测速前的参数与安全审计

### 工作内容

检查真实测速前的所有参数。

确认：

- CFST v2.3.5。
- 完整 IPv4 文件。
- 官方下载测速地址。
- 并发数。
- 延迟测试次数。
- 下载测试次数。
- 下载时长。
- 运行超时。
- 输出 CSV 路径。
- 日志路径。
- 容器无应用层代理变量。
- NO_PROXY=*。
- Docker bridge 网络。
- 不加入 Mihomo 网络。
- 不改变现有 NAS 网络设置。

同时确认 Docker daemon 拉镜像代理与容器运行时代理相互独立。

注意：应用层代理变量为空不能证明路由器透明代理不存在。不要宣称已经排除了路由器透明代理。

### 验收标准

输出完整 CFST 最终命令、配置文件和安全检查结果。

不执行真实测速。

完成后暂停，等待用户批准真实测速。

---

## 阶段4.4：一次完整真实测速验证

### 前提

必须得到用户明确授权。

### 工作内容

执行一次完整 CFST 测速。

只运行一次，不分两轮，不按地区重复测速。

输出：

- 原始完整 CSV。
- CFST 运行日志。
- 运行时间。
- 总耗时。
- 候选 IP 数量。
- 有效记录数量。
- 下载速度分布。
- Colo 分布。
- 丢包率实际单位验证。
- 实际地区码列表。

### 重点检查

1. CSV 是否完整。
2. 普通 TCPing + 下载模式是否输出 Colo。
3. 下载速度是否为 MB/s。
4. 丢包率单位是否与解析程序一致。
5. 是否有大量 N/A。
6. 测速是否在可接受时间内完成。
7. NAS 负载是否正常。
8. 容器是否通过预期 Docker bridge 出口运行。

### 验收标准

必须提供真实 CSV 和日志，不能只提供汇总数字。

检查真实 Colo 是否足够支持 HK、JP、SG、KR、US 五个地区。

如果缺少地区样本，不允许猜测映射。

本阶段只验证测速和数据，不自动安装 Cron，不上传 GitHub。

完成后暂停，等待验收。

---

## 阶段5：正式六文件生成和发布

### 工作内容

根据阶段4.4通过的真实测速结果，生成六个 TXT。

分别生成：

HK.txt
JP.txt
SG.txt
KR.txt
US.txt
global_top25.txt

每个文件单独校验和发布。

记录每个文件的成功状态和节点数量。

保留历史 CSV、JSON 和日志。

### 验收标准

1. 六个文件全部存在。
2. 文件格式符合要求。
3. 地区榜没有未知地区。
4. 全球榜允许未知地区。
5. 排序正确。
6. 地区榜最多5条。
7. 全球榜最多25条。
8. 不跨文件去重。
9. 没有 merged.txt。
10. 单个文件失败不影响其他文件。
11. 成功测速但地区空榜时更新为空文件。
12. 文件异常时保留该文件旧版本。
13. 正式文件可通过 HTTP/HTTPS 访问（如果已完成对应服务配置）。

此阶段不自动修改 EdgeTunnel。

完成后暂停，等待验收。

---

## 阶段6：GitHub Raw 订阅发布

### 工作内容

创建独立 Public GitHub 仓库：

`cf-ip-results`

六个 TXT 分别上传：

- HK.txt
- JP.txt
- SG.txt
- KR.txt
- US.txt
- global_top25.txt

可另外保留 CSV、JSON、运行状态和日志，但不得把 Token 或敏感配置上传。

使用 Fine-grained PAT。

权限只授予该仓库 Contents Read/Write。

Token 只保存在 NAS `.env` 文件中。

不得打印 Token。

不得将 `.env` 纳入 Git。

### 验收标准

1. 六个 Raw URL 均可公开访问。
2. 六个文件内容与 NAS 当前文件一致。
3. 更新一个文件不需要修改其他文件。
4. GitHub 上传失败时，不破坏 NAS 本地结果。
5. Token 不出现在日志和仓库中。
6. 不提交 `.env`。

提交六个 Raw URL 和验证结果。

完成后暂停，等待验收。

---

## 阶段7：EdgeTunnel 六订阅接入

### 工作内容

由用户在 EdgeTunnel 设置页面添加六条独立自定义优选 IP API 订阅。

只使用 EdgeTunnel 原生功能。

不部署 WorkerVless2sub。

不修改 EdgeTunnel 源码。

不修改用户原有 Pages 项目。

不改变原有节点、订阅和其他配置。

### 验收标准

1. 六条订阅分别成功读取。
2. 六个榜单内容正确。
3. 重复 IP 的处理由 EdgeTunnel 自己完成。
4. 节点信息能够正常解析。
5. 更新后能看到新节点。
6. 不影响原有订阅和节点。

提交设置截图或可验证日志。

完成后暂停，等待验收。

---

## 阶段8：每日三次定时运行

### 工作内容

每天北京时间：

06:00
12:00
18:00

Cron：

`0 6,12,18 * * *`

时区：

`Asia/Shanghai`

每次只执行一次完整 CFST 测速。

必须有防重入机制：

- 前一次运行未结束时，禁止启动第二次。
- 记录跳过原因。
- 不能产生并发测速。
- 每次运行有独立日志。

### 验收标准

1. 时区正确。
2. Cron 表达式正确。
3. 测试触发成功。
4. 防重入有效。
5. 日志按日期或运行时间归档。
6. 不影响其他 NAS 定时任务。
7. 容器重启后任务配置仍然有效。
8. 连续观察至少两个计划周期，确认运行和文件更新正常。

完成后暂停，等待验收。

---

## 阶段9：Server 酱微信推送（最后实施）

### 工作内容

官网：

https://sct.ftqq.com

最后阶段才实现，不提前申请或配置 SendKey。

先核对官网最新接口文档，再确定调用方式。

推送内容：

- 本次测速时间。
- 本次测速是否成功。
- 六个文件分别更新成功或失败。
- 每个榜单实际节点数量。
- 各榜单最快节点。
- 最快节点延迟。
- 最快节点下载速度 MB/s。
- 失败文件及原因。
- 六个订阅 Raw URL。

某一个榜单失败，其他榜单仍可更新并正常推送。

SendKey：

- 只保存在 NAS `.env`。
- 不写入源码。
- 不上传 GitHub。
- 不输出到日志。
- 不显示在错误信息中。

推送失败不得影响六个 TXT 文件的生成和发布。

### 验收标准

1. Server 酱微信推送成功。
2. 六个榜单的状态准确。
3. 失败情况能正确报告。
4. SendKey 不泄露。
5. 推送服务不可用时测速和发布仍正常。
6. 不重复发送同一次运行结果，除非明确需要重试。

完成后提交最终部署报告。

---

# 第六部分：每阶段统一交付格式

每个阶段完成后，WorkBuddy 必须提供以下内容：

## 6.1 工作记录

- 本阶段目标。
- 实际完成内容。
- 修改的文件。
- 新增的文件。
- 删除的文件。
- 未完成内容。

## 6.2 文件校验

对所有修改文件提供：

- 文件路径。
- 文件大小。
- SHA256。
- 修改前 SHA256（如文件原先存在）。
- 修改后 SHA256。

## 6.3 测试记录

提供：

- 实际执行命令。
- 完整关键输出。
- 测试通过数量。
- 测试失败数量。
- 测试跳过数量。
- 失败原因。

不得只提供“全部通过”的文字结论。

## 6.4 安全记录

明确说明是否执行过：

- 真实网络请求。
- CFST 测速。
- 网络扫描。
- Docker 容器启动。
- Docker 镜像构建。
- Cron 修改。
- GitHub 上传。
- EdgeTunnel 修改。

没有执行的事项必须明确写“未执行”。

## 6.5 阶段结束要求

每个阶段完成后：

1. 停止继续操作。
2. 不擅自进入下一阶段。
3. 不擅自扩大任务范围。
4. 等待用户将报告交给 ChatGPT 审核。
5. 收到明确授权后才能继续。

---

# 第七部分：最终项目验收目标

最终系统必须达到：

- QNAP NAS 自动运行。
- 每天三次完整测速。
- 每次只运行一轮 CFST。
- 六个独立 TXT。
- 五个地区榜各 Top 5。
- 全球榜 Top 25。
- 下载速度 MB/s 排名。
- 节点备注格式统一。
- 六个文件独立更新。
- 不跨文件去重。
- 不生成 merged.txt。
- GitHub Raw 六条订阅可用。
- EdgeTunnel 原生订阅正常。
- 失败不覆盖对应文件旧版本。
- 防止并发测速。
- Server 酱微信推送正常。
- 不影响 NAS 现有容器、Mihomo、AdGuard、其他业务和 EdgeTunnel 原有配置。

**当前执行授权仅到阶段4.1。其余阶段均须逐阶段验收和授权，不得提前执行。**

---

# 附：用户补充的执行顺序与验收控制（同一次授权消息）

为了避免 WorkBuddy 一次性改太多、后续难以排查，严格按下面的顺序推进：

**当前授权范围：仅阶段 4.1**

1. **4.1 代码修订**：先改程序和配置，完成离线单元测试。ChatGPT 检查代码和 SHA256。
2. **4.2 容器离线集成**：验证 Python 3.12、权限、六文件输出和故障隔离。
3. **4.3 真实测速前审计**：确认 CFST 参数、网络路径、资源和安全配置。
4. **4.4 单次真实测速**：用户批准后只测一次，先拿到真实完整 CSV。
5. **5～8 正式发布和自动运行**：六文件发布、GitHub、EdgeTunnel、每日三次定时。
6. **9 Server 酱推送**：最后接入微信通知。

**三个验收重点**

1. **单轮测速是否真正成立**：不能只是把原来的两轮命令合并成一条，而是必须确认普通 CFST 下载模式能够提供可用的 Colo、延迟、速度和丢包率。
2. **地区榜映射不能猜**：目前只有 SIN 和 LAX 有实际测试依据，HK、JP、KR 需要后续真实样本确认。
3. **六个文件必须独立更新**：完整测速失败时六个文件都不更新；完整测速成功后，某一个榜单生成失败，只保留该文件旧版本，其他成功的榜单照常更新。

**补充要求**：阶段 4.1 不要顺手安装 Cron、上传 GitHub 或运行真实测速。先把代码做正确，后面的每一步都有独立验收门槛。

---

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

---

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

---

# 附录 D：阶段 4.1-R3 执行记录（CSV 证据校验与状态持久化边界修正）

**授权依据**：`STAGE4_1-R3 任务书：CSV 证据校验与状态持久化边界修正.md`
**授权范围**：仅限 R3 源码修正 + 离线测试 + 本文档更新；不授权 4.2、不授权真实测速、不授权部署操作。
**前置版本**：4.1-R2（`4.1.3-r2`）→ **本版**：`4.1.4-r3`。

## D.1 七项修正与实现方式

| 编号 | 修正 | 实现要点 |
|---|---|---|
| R3-01 | 证据绑定 | `RunCsvInit` 新增 `bound_path`；`token` 升级为 `<nonce>.<HMAC-SHA256(进程内密钥, nonce\|规范化路径)>`。`csv_is_fresh` 必须校验票据签名、`bound_path` 与当前 path 一致、票据未被消费；缺失/伪造/错配/跨轮复用一律 fail-closed。 |
| R3-02 | source 严格白名单 | 仅 `production` / `test_explicit` 合法；`None`、空串、未知串、非字符串（含不可哈希类型）一律拒绝。`production` 必须 `pre_absent=True`；`test_explicit` 不得携带生产前置证明。`run_once` 额外校验证据来源与 `auto_csv` 一致，杜绝生产流程走测试分支。 |
| R3-03 | freshness 异常收敛 | `csv_is_fresh` 把 `is_file`/`stat` 等文件系统观测全部收进 try，返回 `(False, "freshness 文件系统检查异常…")`；`validate_csv_completeness` 同样收敛；`run_once` 对两处调用再各包一层独立异常边界，任何异常都进入 `_abort(stage="csv_fresh"/"csv_complete")` 并落盘失败状态，不归档、不更新六 TXT。 |
| R3-04 | 两 JSON 完整隔离 | `publish_json_file` 把 `mkdir`/`mkstemp` 纳入内部 try；`_persist_status` 不再有覆盖整个循环的外层 try，改为每个 JSON 的完整链路各自 `try/except`。新增 `mkdir_fn`/`mkstemp_fn`/`unlink_fn` 注入点；临时文件清理失败单独记入 `cleanup_warning`，不掩盖原始错误。 |
| R3-05 | 断开符号链接 | `prepare_run_csv` 改用 `os.path.lexists + os.lstat` 的 `_entry_kind()`：普通文件/目录/正常或断开符号链接都不能记为 `pre_absent=True`；目录与特殊文件拒绝删除，符号链接只删链接本身（不跟随目标）。 |
| R3-06 | 凭据扫描补强 | 保留 `_FULL_FIELDS`/`_LIGHT_FIELDS` 字段白名单；新增 `contains_secret_markers()`，大小写不敏感 + 正则覆盖 `TOKEN=`/`token=`、`SendKey`/`sendkey`、`Bearer`/`BEARER`、`github_pat_`/`ghp_`、常见密钥字段名、URL 参数凭据与裸长十六进制串；命中拒绝发布且不回显原文。测试全部使用 DUMMY 假值。 |
| R3-07 | 生产归档失败不得 success | `status["archive_expected"]` 仅在 `production + should_archive` 时为真；`overall_status_of()` 在该标志为真且 `csv_archived=False` 时返回 `partial`。归档失败原因写入 `csv_archive_reason` 与 `warnings`，并加入两个状态 JSON 的字段白名单。`test_explicit` 离线路径不要求归档，不因 `csv_archived=false` 被误判。六榜不回滚、TXT 不破坏。 |

**状态粒度补充说明**：CSV 归档失败属于「业务部分成功」，按任务书要求降为 `partial`；状态 JSON 自身写入失败属于「状态持久化失败」，不改变 `overall_status`（避免把测速成功误判为业务失败），由 `status_persist_state`（`ok`/`partial`/`failed`）、`status_files` 逐项结果与 `warnings` 三者明确记录。沿用 R2 已确立的「状态 JSON 不自指记录本次写入结果」原则，故 `status_persist_state` 只存在于 `run_once` 返回值，不写入两个 JSON。

## D.2 修改文件与 SHA256（修改前 = R2 交付基线）

| 文件 | 修改前 | 修改后 |
|---|---|---|
| `app/__init__.py` | `b1e3d46372864cdbb7e7252c95e19fa3291afbb37702cb844573934bd83524e1` | `f7ec36ac4c3e9b0cd153931745866ac29ecb11d5d0f83b1318b1641602e139d6` |
| `app/main.py` | `c252219792993cc878631621ee59db6016bbb37ba3a970acca425ff9c4615b62` | `095bbd890c406673bbb9dfb8cdee109d397a1777f2fcaede1042e3a0135ab3df` |
| `app/cfst.py` | `7e9bfcf41e80f18ed2bd0379e07ff4bd9382685f9dbec97ef2d57694ed810860` | `9f8a805f4d59bab318e56a9bb6efc29953b606619c03de6164ef9cd9da9a0532` |
| `app/output.py` | `c22b866a3ded9e4c5bb26c874a942f4bd0f788a4a4f452eff6ffb83b3605d473` | `6760c5d1f56ff352b59b276a864489e57fee114a2bf1e4b37264fd0fbdf32d8a` |
| `app/safety.py` | `5ef487ae663f150448ab00a1c02aaa4c519ed856028f08949d97c9a9f4a90fa9` | `869e9b04f4f4d5ce4c91cf7021c913ca99c85b6ff0acf5a606017eea68f3730b` |
| `app/pipeline.py` | `ad06af7dd3d10edafab548daa645622b6dd30b3f284433aa62dd8c7e4a78561e` | `5f5e97d3a850f51311d38feeb6dc72959abbde2d86453ec02c235c39119b9cb2` |
| `docs/TASK_BOOK.md` | `aa63174b53c26e5851cfb13eb824351c0830ae091adf2ff7ed008d2d5bab1031` | 本附录写入后单独核算并记入交付报告 |

修改前基线已逐文件与 NAS 实际哈希核对一致后才写入；写入后 NAS 与本地副本 SHA256 双向复核一致。
`app/config.py`、`app/ranking.py`、`app/region.py`、`config/settings.json`、`config/regions.json`、
`Dockerfile`、`compose.yaml`、`.dockerignore`、CFST 二进制与 6 份 `samples/*.csv`
（共 15 个禁改文件）在写入前后两次核对，全部与 R2 基线一致。

## D.3 测试结果（NAS / Python 3.11.2，完整输出见 `STAGE4_1_R3_TEST_OUTPUT.txt`）

| 命令 | 结果 |
|---|---|
| `python3.11 -m compileall -q app` | 9 个 `.py` 全部编译通过 |
| `python3.11 -m app.main --check-config` | exit 0，版本 `4.1.4-r3` |
| `python3.11 -m app.main --self-test` | exit 0；**R2 及更早回归 65/65 通过**，**R3 新增 X01~X40 共 40/40 通过**，合计 105 通过 / 0 失败 / 2 跳过；网络守卫拦截 0 次 |
| `python3.11 -m app.main --simulate` | exit 0；R2 原有 11 类场景 + R3 新增场景 12~15 全部通过 |
| `python3.11 -m app.main --run` | exit 2（阶段 4.1 明确拒绝真实测速） |

- R2 的 2 项 SKIP（S01 真实 CFST / 真实 CSV 单位留 4.4；S02 容器 Python 3.12 / 0o600 读取权限留 4.2）**保持原有原因，未改成伪通过**。
- R2 的 N04 因证据对象结构升级，改用 `dataclasses.replace` 基于本轮真实证据构造字段变体；四个子断言的语义与强度完全未弱化，未删除或跳过任何旧检查。
- R3-05 的符号链接用例在 NAS/Linux 侧走**真实文件系统**路径，输出明确显示
  `R3-05 符号链接验证方式: 真实文件系统（symlink 可用，含断开符号链接）`，
  并验证 `lexists(断开链接)=True` 而 `Path.exists(断开链接)=False`（R2 会误判）。
  本机 Windows 无创建符号链接权限时，同一用例改由 `_entry_kind` 注入覆盖逻辑分支并在输出中明确标注，绝不声称真实文件系统已覆盖。
- 新增测试全部位于独立 `TemporaryDirectory`，测试结束自动清理；X22/X18/X20 等用例同时断言 `.tmp-*.part` 无残留；X24 对「注入模拟的清理失败」如实断言存在 1 个残留并记录 `cleanup_warning`。
- 所有凭据扫描测试数据均为明显的 `DUMMY` 假值，未使用任何真实 GitHub PAT / Server 酱 SendKey / 密码。

## D.4 目录与边界状态

- `data/`、`logs/` **仍为空目录**（未生成六个正式 TXT、未生成 `result.json`/`last_run.json`、未生成正式 CSV）。
- `samples/` 6 份历史 CSV 文件数与 SHA256 全部与 R2 基线一致。
- 未构建/重建/启动/停止任何 Docker 容器；未运行 `docker compose`；未创建或修改 Cron、定时任务、自动重启策略。
- 未连接 GitHub、未创建 PAT、未上传文件；未配置 Server 酱/SendKey；未修改 EdgeTunnel、Pages、Worker。
- 未修改 Docker 网络、代理、路由器、NAS 系统设置或 `/share/homes` 权限。
- 未执行真实 CFST、未扫描真实 Cloudflare IP、未访问外网测速或下载；`execute_cfst` 仍是拒绝占位。
- 未修改 `config/settings.json` 任何业务参数、`config/regions.json` 地区映射、六个 TXT 文件名/格式/排名规则/发布策略。

## D.5 未完成事项 / 未覆盖边界 / 风险（本轮一律未实施）

1. **状态 JSON 自指限制**：状态文件无法记录「本次自身写入结果」，部分持久化失败只记录在 `run_once` 返回的 `status_persist_state` / `status_files` / `warnings` 中，不写进两个 JSON。若后续要求 JSON 内自指，需单独设计并授权。
2. **`publish_one()`（六个 TXT）的同类边界**：其 `mkdir`/`mkstemp` 仍位于内部 try 之外，但 `pipeline` 的单榜 `try/except` 已把异常收敛为单榜 `failed`、不会逃逸 `run_once`。按最小修改原则本轮未改动，留待确认。
3. **进程内 HMAC 密钥的边界**：票据只在同进程同轮有效，可防止跨轮/跨路径伪造；不提供跨进程持久化校验（当前架构不需要）。
4. **P1-3 防重入机制**：进程锁/文件锁、并发实例测试尚未实现（正式调度阶段前必须完成）。
5. **阶段 4.2**：容器 Python 3.12、UID 1000/GID 0、只读根文件系统、0o600 能否被真实消费者读取 —— 未验证，**0o600 不得擅自放宽**。
6. **阶段 4.3**：`-dn 100` 合理性、超时/并发 NAS 负载、Docker bridge 出口、路由器透明代理 —— 未审计；容器内代理变量为空不能证明透明代理不存在。
7. **阶段 4.4**：单次完整真实 CFST、真实 CSV 丢包率单位、Colo 稳定性、MB/s 单位、地区覆盖与耗时 —— 需用户另行授权。
8. **地区映射补全**：仍只有 `SIN→SG`、`LAX→US`；HK/JP/KR 空、DEN 待确认、AMS/N/A 排除，禁止猜测。
9. **正式发布链路**：六个 TXT 正式发布、GitHub 仓库与 Raw 订阅、EdgeTunnel 六订阅、每日 06:00/12:00/18:00 定时、Server 酱推送、`logs/` 独立日志归档 —— 全部未执行。
10. **SSH 凭据安全**：建议用户尽快改密或改用公钥认证；本轮未把任何凭据写入文件、任务书、日志、脚本或输出。

## D.6 阶段结束要求

R3 完成后**停止**，仍停留在阶段 4.1，不进入 4.2。
由 ChatGPT 依据 R3 源码全文、修改前后 SHA256、NAS/本地对照与完整测试输出做只读验收，
再单独决定是否授权阶段 4.2。本次**没有执行真实测速、容器启动或任何外部发布**。
````

### `config/settings.json` — 31 行，2409 B，sha256=750b9fedde2b1f4519f996007286b951482deaa54eb90d5a5ec64d3c5f0a00e0

````
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

### `config/regions.json` — 42 行，2086 B，sha256=998745250d900520000599da43b3c1f4ef59e92a077984295079b771e8d7f83a

````
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

