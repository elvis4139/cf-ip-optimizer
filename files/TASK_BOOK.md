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

