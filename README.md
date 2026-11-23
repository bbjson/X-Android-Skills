# X-Android-Skills

> Android agent skills that cannot rot.
> 从 33 个公开 skill 仓库、1060 个 `SKILL.md` 里去重凝练出的 Android 开发技能集。

---

## 这是什么

一套遵循 [Agent Skills 规范](https://agentskills.io/specification) 的 Android 开发技能，供
pi / Claude Code / Codex / Cursor / Gemini CLI / Copilot 等直接加载。

**不是** 上游仓库的合集或镜像。每个 skill 都是重新写的：多条来源冲突时只保留经得起检验的
规则，重复的合并，过时的删除。每条规则都注明来源（`metadata.sources`），取舍理由记录在
[`docs/provenance.md`](docs/provenance.md)。

## 为什么需要重做一遍

审计 33 个仓库后的实测结论：

| 发现 | 数据 |
|---|---|
| 安卓相关 skill 总数 | ≈ 330 个 |
| 其中真正不同的「决策」 | ≈ 90 个（重复率约 3.6 : 1） |
| 存在硬编码过期版本的仓库 | 4 个直接踩坑（AGP 8.2.0 / Kotlin 1.9.20 / espresso 3.5.1） |
| 当前实际版本（`maven-metadata.xml` 实测） | AGP 9.6.0-alpha05 · Kotlin 2.5.0-RC · Hilt 2.60.1 |
| 违反长度预算（>400 行）的 skill | 5 个（最长 2605 行） |

**过期方式高度一致**：把版本号写进自然语言，agent 抄进新项目，撞 Kotlin/Compose 编译器
耦合报错。所以本项目的核心约束是：

> **任何 skill 都不写死依赖版本。版本只来自项目的 `gradle/libs.versions.toml`。**

这条规则由 `tools/validate.py` 自动检查（迁移类 skill 是唯一豁免，因为它的主题就是版本迁移）。

## 设计原则

1. **规则必须改变决策。** "要用 Compose" 不是规则；"UI 不能丢事件时用 Channel 而非
   `SharedFlow(replay=1)`" 是规则。
2. **可验证。** 每个 skill 有 `## Checklist`（能对着 diff 打勾）和 `## Verify`（能真跑的命令）。
3. **单一决策面。** 一个 skill 只回答一个问题；两个互不相关的话题 = 两个 skill。
4. **有预算。** core ≤ 200 行，advanced ≤ 260，specialized/migration ≤ 400。超了就说明在讲课
   而不是在约束。

写作标准详见 [`docs/skill-style.md`](docs/skill-style.md)。

## 已实现（69）

入口是 `router`：任何模糊请求先经它路由，避免"从症状开工"。

| 域 | Skills | 该域的核心主张 |
|---|---|---|
| meta | `router` | 从症状路由到 artefact；两个 skill 同时适用 = 该拆任务 |
| 00 workflow | `requirements-grill` `feature-to-spec` `implementation-plan` `code-review` | 需求未定不写码；状态集必须封闭；每个任务结束于绿色 |
| 10 architecture | `layering` `modularization` `data-layer` `state-holders` `dependency-injection` `feature-scaffold` | 模块必须能说出它禁止了什么；单一真相源在本地 |
| 20 compose | `compose-core` `compose-component-api` `compose-state-effects` `compose-navigation` `compose-animation` `compose-accessibility` `design-system` `rtl-localization` | 一个状态一个所有者；slot 代替布尔；token 代替字面量 |
| 30 performance | `recomposition` `modifier-and-layout` `lazy-layouts` `startup-and-perfetto` `baseline-profiles` `r8-for-compose` | 没有 before/after 数字就不算修复 |
| 40 build | `version-catalog` `agp9-migration` `gradle-conventions` `kotlin-toolchain` `ksp-processing` `build-performance` `ci-pipeline` | 版本只有一个真相源；配置只写一次；测过再优化 |
| 50 quality | `unit-testing` `compose-ui-testing` `screenshot-testing` `e2e-device-testing` `static-analysis` `benchmark-testing` | 断言可观察结果；测试必须见过红；基线只减不增 |
| 60 security | `keystore-and-crypto` `component-exposure` `network-dto-safety` `masvs-audit` | 密钥不出硬件；导出的组件是没有版本的公开 API；审计要控制项+证据 |
| 70 release | `release-flow` `signing-and-play-signing` `play-metadata` `data-safety-compliance` `vitals-and-reports` | 一份产物走完所有 track；表单/政策/APK 三方一致 |
| 80 device | `adb-automation` `emulator-management` | 观察→决策→执行循环，永不 sleep；AVD 的锁/快照/端口是三个故障源 |
| 90 platform | `kmp` `wear-os` `tv-and-focus` `camera` `media3` `notifications-fcm` `deep-links` | 共享无平台语义的部分；焦点就是光标；资源有所有者 |
| 95 migration | `xml-to-compose` `rxjava-to-coroutines` `java-to-kotlin` `nav2-to-nav3` `hilt-to-koin` `cocoapods-to-spm` | 热/冷与作用域是迁移的真正风险；一次只动一个变量 |
| 99 specialized | `reverse-engineering` `kotlin-footguns` `kernel-lkm` `mainline-port` | 授权先于分析；编译通过 ≠ 正确；内核 API 以目标树为准 |

几个只有对照多个上游才写得出的规则：

- **`StrongSkippingMode` 已默认开启，不要显式加** —— 上游旧材料仍在教这个
- `@Stable` 加在含 `var` 的类上是「谎言，会产生陈旧 UI」
- `SharedFlow(replay=1)` 做一次性事件会在旋转后重放，`StateFlow` 会丢事件 → 用 `Channel`
- `Modifier.padding(16.dp).clickable {}` 与反过来的点击区域不同，这是设计决策不是细节
- Play 放量前必须有**数值**止血条件，且「回滚 = 撤销放量 + 重推旧版本号」
- `coerceInputValues` 会让 DTO 类型漂移静默变默认值，这是掩盖而非修复

## Roadmap

**全部 69 个已实现，roadmap 为空。** 后续如果新增，规则是：先在 `docs/roadmap.txt` 登记名字，
实现后从该文件移除 —— `tools/check_refs.py` 用它区分「规划中」和「写错了名字」。

尚未覆盖、但可能有价值的后续方向（非承诺）：Robolectric 单元测试细节、Compose Multiplatform 专门技能、
Kotlin 编译器插件编写、AAB 体积优化（resource shrink / abi splits）、baseline profile 与 macrobenchmark
的 CI 矩阵、Firebase App Distribution / TestFlight 双平台发布。

## 安装

```bash
# 装到 agent 的默认 skill 目录（~/.agents/skills）
./tools/install.sh

# 只装一个域 / 只装 core 级
./tools/install.sh --domain compose
./tools/install.sh --level core

# 软链接（仓库保持唯一真相源，改完立即生效）
./tools/install.sh --link

# 查看将安装什么 / 卸载
./tools/install.sh --list
./tools/install.sh --uninstall
```

pi / Claude Code / Codex 会在启动时扫描该目录，把每个 skill 的 `name` + `description` 放进
系统提示，命中任务时才加载全文。也可强制加载：`/skill:recomposition`。

## 校验

```bash
python3 tools/validate.py          # 结构、frontmatter、硬编码版本、长度预算
python3 tools/check_refs.py        # 邻居引用必须落在「已实现 ∪ roadmap」内
python3 tools/check_routing.py     # 75 条 routing 断言：任务 → 期望 skill
python3 tools/check_routing.py --verbose   # 逐条显示
python3 tools/audit_duplicates.py          # 规则重叠最高的 skill 对（辅助复核，不做判定）
```

`audit_duplicates` 的实测结果是：最高重叠 0.18（`compose-navigation` ~ `nav2-to-nav3`），
且全部 top 对都是「基础 skill ~ 它的迁移/工具 skill」，属于必然交叉而非重复条款。

三者角色不同：`validate` 管单个 skill 的形状，`check_refs` 管 skill 之间的指认，
`check_routing` 管「路由器是否真的把任务送到对的地方」—— 它是本仓库唯一的**行为测试**。

当前状态：

```
69 skills — 0 errors, 0 warnings
69 installed, 0 roadmap — 0 unknown references
75 routing cases, 68/69 skills covered — 0 failures
## Verify 已实跑：198 条 / 150 条执行 / 0 失败 / 14 缺陷已修（docs/verify-report.md）
```

`router` 是 meta，不需要 eval 用例；其余 68 个 skill 每个至少被一条 routing 断言覆盖。

## 仓库结构

```
skills/<NN-domain>/<slug>/SKILL.md    # slug 必须等于 frontmatter name
skills/router/SKILL.md
templates/SKILL.template.md
tools/validate.py                     # 结构 + 版本规则校验
tools/check_refs.py                   # 悬空 skill 引用检测
tools/check_routing.py                # routing 断言（行为测试）
tools/audit_duplicates.py             # 规则级重叠报告（供人工复核）
tools/verify_skills.py                # 逐条执行 ## Verify（需真实项目 + 设备）
tools/install.sh                      # 安装器
docs/skill-style.md                   # 写作标准（权威）
docs/provenance.md                    # 33 个来源的取舍账本
docs/roadmap.txt                      # 规划中的 skill 名（当前为空 = 全部已实现）
docs/verify-report.md                 # Verify 实跑记录：环境、证据、8 条缺陷、未验证清单
evals/routing.tsv                     # 75 条 任务→skill 断言
AGENTS.md                             # 给 agent 的项目约定
```

## 与上游的差别（一句话版）

| 上游普遍做法 | 这里 |
|---|---|
| 写死 `agp = "8.2.0"` | 只写 catalog key，校验器拦硬编码 |
| 罗列 API（"用 StateFlow 管理状态"） | 给决策边界（什么时候*不*用 StateFlow） |
| 1000 行教程 | ≤200 行约束 + 可打勾清单 |
| 每个仓库各自一套术语 | 统一骨架：Use when / Rules / Checklist / Anti-patterns / Verify |
| 覆盖率优先 | 冲突消解优先，重复的合并 |

## 验证状态

**198 条 `## Verify` 命令逐条实跑**（2026-11-23，真实项目 + 模拟器 + 真机）：

| skill 状态 | 数量 | 含义 |
|---|---|---|
| **VERIFIED** | **54** | 非跳过命令全部执行、全部 exit 0 |
| INCONCLUSIVE | 1 | `component-exposure`：3 条命令都是"期望失败"型断言，脚本无法判分 |
| SKIPPED-ONLY | 6 | `screenshot-testing` `benchmark-testing` `kmp` `cocoapods-to-spm` `kernel-lkm` `vitals-and-reports` —— 依赖不在 fixture |
| 无命令 | 8 | 纯文字判据（workflow/meta），已有 `Expected:` 行 |

| 命令状态 | 数量 |
|---|---|
| 提取 | 198 |
| 执行 | **150** |
| 非零退出 | **0** |
| 跳过（依赖缺失 / 占位符 / 危险操作） | 26 / 8 / 14 |

**发现并修复 14 个缺陷**（详见 `docs/verify-report.md`）：6 条命令写错、4 条规则失真、
62 处裸 `adb`（与 `adb-automation` 自己的规则冲突，双设备环境必挂）。

环境：AGP 9.1.1 · Gradle 9.7 · Kotlin 2.4.21（AGP 内置）· Compose BOM 2026.02.00 · compileSdk 36 ·
JDK 17 · Pixel_9_API_36 + 一台真机。

典型的 6 条命令错误：`--tests` 用在聚合 task（`:x:test`）、Gradle 9 的 `project ':x'` 引号、
`androidx.compose.compiler.reports` 属性失效、`-Pandroid.injected.build.api=...` 无法解析、
`cmd notification get_notification_channels` 不存在、AGP 9 改了 `javap` 的类输出路径。

复跑：

```bash
python3 tools/verify_skills.py --fixture ~/Desktop/verify-fixture --dry   # 打印执行计划
python3 tools/verify_skills.py --fixture ~/Desktop/verify-fixture         # 实跑
```

## 成本与取舍

69 个 `name` + `description` 合计 **26,662 字符 ≈ 6,700 tokens**，安装后会全部进入 agent 的系统提示。
这是可以接受但不免费的：如果上下文紧张，用子集安装。

```bash
./tools/install.sh --level core                     # 只装 core 级
./tools/install.sh --domain compose                 # 只装 compose 域
./tools/install.sh --domain compose --domain build  # 一次一个域，跑多次
```

`description` 中位数 393 字符（最短 297，最长 474）—— 这是刻意的：routing 靠它选 skill，
压到 150 字符能省一半 token，但命中率会下降。如果你更在意上下文，可以压；两者不可兼得。

## License

Apache-2.0。上游仓库多为 Apache-2.0；4 个无 License 的仓库未被逐字复制，只借用了思路。

## 英文摘要

Sixty-nine consolidated Android agent skills distilled from 33 public repositories and 1060
`SKILL.md` files. The differentiator is a single enforced constraint — **no skill may pin a
dependency version** — plus a fixed rule/checklist/verify skeleton that makes every skill reviewable
against a diff. See `docs/provenance.md` for what was taken from where and `docs/skill-style.md` for
the authoring standard.
