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

## 已实现（20）

| 域 | Skill | 解决什么 |
|---|---|---|
| meta | `router` | 从症状路由到正确的 skill，拒绝在任务不清时开工 |
| workflow | `bug-fix` | 证据优先的排障顺序（复现 → 首个 `Caused by` → 判别实验 → 最小修复） |
| architecture | `layering` | 谁拥有这段代码、依赖方向、边界模型与映射位置 |
| compose | `compose-state-effects` | 每个状态的最低责任所有者 + 每个副作用的正确 effect |
| compose | `compose-navigation` | Nav3 状态驱动 vs Nav2 类型安全路由，参数/深链/ViewModel 作用域 |
| performance | `recomposition` | 只分四类原因，每类一个正确解（含 strong skipping 的过时说法纠正） |
| performance | `baseline-profiles` | 生成 / 测量 / CI 门禁，并验证 profile 真的进了 APK |
| build | `version-catalog` | 版本只有一个真相源，convention plugin 从 catalog 读 |
| quality | `screenshot-testing` | 快照测试必须「变了会红」，含故意打红验证流程 |
| security | `keystore-and-crypto` | 密钥不出硬件，含 `setInvalidatedByBiometricEnrollment` 等易漏点 |
| release | `release-flow` | 一份产物走完所有 track，分阶段放量 + 数值化止血条件 |
| architecture | `modularization` | 模块必须禁止某条依赖，否则只是多了个 build 文件 |
| architecture | `data-layer` | 单一真相源在本地，网络结果写进去而不是返回给 UI |
| architecture | `state-holders` | 一个不可变状态类型 + 单一归约入口，事件不进状态 |
| architecture | `dependency-injection` | 按生命周期定作用域，短命对象不进长命对象 |
| quality | `unit-testing` | 断言可观察结果而非交互，fake 优先于 mock |
| quality | `compose-ui-testing` | 按用户可感知的语义查找节点，tag 是最后手段 |
| build | `agp9-migration` | 逐级爬升，删掉的 API 必须**替换**而不是压制警告 |
| device | `adb-automation` | 观察→决策→执行循环 + 超时，永不 sleep |
| migration | `xml-to-compose` | 迁移单位是**一个屏幕**，两个方向互操作但有主有次 |

## Roadmap（49）

已规划、尚未落地。每个都已在 `docs/provenance.md` 中标注来源与取舍。

**00 workflow** `requirements-grill` · `feature-to-spec` · `implementation-plan` · `refactor` · `code-review` · `deliver-pr`

**10 architecture** `feature-scaffold`

**20 compose** `compose-core` · `compose-component-api` · `compose-animation` · `compose-accessibility` · `design-system` · `rtl-localization`

**30 performance** `modifier-and-layout` · `lazy-layouts` · `startup-and-perfetto` · `r8-for-compose`

**40 build** `gradle-conventions` · `kotlin-toolchain` · `ksp-processing` · `build-performance` · `ci-pipeline`

**50 quality** `e2e-device-testing` · `static-analysis` · `benchmark-testing`

**60 security** `component-exposure` · `network-dto-safety` · `masvs-audit`

**70 release** `signing-and-play-signing` · `play-metadata` · `data-safety-compliance` · `vitals-and-reports`

**80 device** `emulator-management`

**90 platform** `kmp` · `wear-os` · `tv-and-focus` · `camera` · `media3` · `notifications-fcm` · `deep-links`

**95 migration** `rxjava-to-coroutines` · `java-to-kotlin` · `nav2-to-nav3` · `hilt-to-koin` · `cocoapods-to-spm`

**99 specialized** `reverse-engineering` · `kotlin-footguns` · `kernel-lkm` · `mainline-port`

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
python3 tools/validate.py --quiet  # 只报问题
```

当前状态：**20 skills — 0 errors, 0 warnings**。

## 仓库结构

```
skills/<NN-domain>/<slug>/SKILL.md    # slug 必须等于 frontmatter name
skills/router/SKILL.md
templates/SKILL.template.md
tools/validate.py                     # 校验器
tools/install.sh                      # 安装器
docs/skill-style.md                   # 写作标准（权威）
docs/provenance.md                    # 33 个来源的取舍账本
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

## License

Apache-2.0。上游仓库多为 Apache-2.0；4 个无 License 的仓库未被逐字复制，只借用了思路。

## 英文摘要

Twenty consolidated Android agent skills distilled from 33 public repositories and 1060
`SKILL.md` files. The differentiator is a single enforced constraint — **no skill may pin a
dependency version** — plus a fixed rule/checklist/verify skeleton that makes every skill
reviewable against a diff. See `docs/provenance.md` for what was taken from where and
`docs/skill-style.md` for the authoring standard.
