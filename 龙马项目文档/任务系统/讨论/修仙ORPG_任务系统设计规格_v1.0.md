# 修仙 ORPG · 任务系统设计规格 v1.0

> 定位：任务系统的设计规格文档。面向策划和程序，不含讨论过程和版本历史。所有标记标注已清除——本文件为可交付设计权威。

---

## 1. 概述

### 1.1 任务系统的定位

任务系统是**编排层**，不做万能系统。它只做四件事：

1. 接收战斗/背包/对话/修炼/突破等领域系统的事实变化
2. 按任务定义推进当前步骤/进度/状态
3. 调用导航/教学/演出/奖励/解锁/存档接口
4. 向 HUD/任务面板/NPC 标记提供任务视图

业务系统不应知道"某任务是否存在"，只广播 `alchemy.recipe_completed`、`realm.changed` 这类事实。任务、成就、图鉴、埋点、世界事件共享同一批事件源。

```
战斗/背包/对话/采集/炼丹/修炼/突破/宗门
                  ↓ 领域事件 (se.emit)
       玩家事实层（Fact / Anchor / DepKey）
                  ↓ 增量刷新
     QuestRuntime（状态 + 当前Step + 条件树 + 进度）
         ↓                 ↓                 ↓
      任务UI             奖励/解锁          存档/服务器同步
```

### 1.2 设计前提

- 玩家开局已是宗门弟子，无"加入宗门"任务。省去山门→大殿→找 NPC 的入门任务链编排。
- 新手任务以大任务节点组织，每个节点中间穿插多个小任务逐步引导，避免节奏过快或过慢。
- 参考一念逍遥的新手流程作为节奏基准。

### 1.3 新手任务链全景

> 以下为截图原文中的新手任务链设计。1.1「加入宗门」已移除——玩家开局即宗门弟子。保留此表作为原始设计参考和后续任务依赖分析的完整语境。

| ID | 任务名称 | 关键NPC/场景 | 核心教学与玩家动作 | 任务系统需编排的能力 |
|---|---|---|---|---|
| 1.1 | 加入宗门 | — | — | —（已移除） |
| 1.2 | 试炼幻境·首次击杀 | 陆青；山门广场/试炼幻境 | 击杀4只怪、拾取、背包、穿装、吃丹 | 副本进出、击杀计数、掉落拾取、背包解锁、装备/道具使用、交付 |
| 1.3 | 丹道初窥·首次炼丹 | 药童、周文扬；灵植园/炼丹房 | 采凝露草、炼引气丹×3、服丹、调息 | 采集、材料入包、配方炼丹、丹药使用、短时打坐、步骤锁定 |
| 1.4 | 长老授业·传授功法 | 莫黎长老；功法阁/试炼幻境 | 秘籍激活、学功法、试炼打怪、熟练度 | 秘籍使用、技能解锁、功法熟练度、副本试炼、交付 |
| 1.5 | 再遇陆青·修炼基础 | 陆青；大殿广场 | 打坐30S、修为增长、离线提示、服饰 | 打坐状态、批量计时、修为/等级变化、离线结算、功能引导 |
| 1.6 | 历练委托·首次委托 | 孙管事；勤务堂 | 任务面板、分类、悬赏接取—完成—交付 | 任务栏、固定新手悬赏、追踪、交付、奖励、宗门贡献 |
| 1.7 | 筑基之路·收集突破材料 | 孙执事/孙管事；全区域/勤务堂 | 炼气九层、BOSS核心、材料、灵石、交付 | 境界/修为触发、BOSS掉落、持有量、采集、货币校验、材料保护 |
| 1.8 | 破境筑基·首次大突破 | 莫黎长老等；渡劫台/秘境 | 心魔、雷劫、首次突破、世界播报 | 突破入口、个人秘境、镜像战、雷劫结算、境界变更、奖励/播报幂等 |

新手线所需的原子能力：对话与交付（前后对白不同；条件完成≠已交付）· 到达与导航（区域/NPC/场景/副本/返回点均需稳定ID）· 战斗与物品（击杀/掉落/拾取/持有量/使用/装备/秘籍学习均需发领域事件）· 生产与修炼（采集/炼丹/服丹/打坐/离线结算/熟练度/境界突破是任务监听的外部事实，非任务内部逻辑）· 教学与演出（多步骤严格顺序，需锁定/高亮 UI）。

---

## 2. 旧项目可复用资产

以旧 QuestSystem 的配置/RuleTree/事件依赖刷新/快照/奖励/UI 为底座，新增修仙领域事件与显式步骤机。**不重新发明任务系统。**

### 2.1 可复用骨架

| 模块 | 已有能力 | 修仙处理 |
|---|---|---|
| `QuestDefRepo` + `ImportQuestData` | 配置导入任务/NPC/对白/奖励/条件/目标区域 | 复用结构，换修仙任务/步骤表 |
| `TaskServiceImpl` | 每玩家运行时、接取/领奖、状态刷新、主线互斥、周期轮转 | 复用为核心服务，补 StepRuntime 与修仙作用域 |
| RuleTree | `pred/all/any/not`、三态、依赖索引、增量刷新 | 直接保留，作为底座 A8 条件树的任务接入层 |
| `AnchorManager` + `se.on` | 领域事件写事实，只刷新依赖它的任务 | 抽象为统一玩家事实层，事件名重新规范 |
| ProgressView / Renderer | 多目标 cur/target/done，进度写回快照 | 复用，增步骤标题/目标图标/教学高亮 |
| RewardHandler | 经验/货币/物品、概率、提示、奖励事件 | 改修为/灵石/宗门贡献/配方/功法/邮件补发 |
| TaskPanelUI | 主线优先、支线排序、NPC导航 | 保留交互思路，按修仙 HUD 重做视觉 |
| QuestAPI | 创建/上传进度/完成任务 | 按 KK 服务器接口改造，任务实例 ID 保留 |

### 2.2 已实现谓词

`kill_count_ge`、`collect_items`、`completed_quest`、`enhance_equipment_count`、`equip_target_grade_equipment`、`player_level_ge/lt` 有实际代码；`find_target_npc`、`recycle_equipment_count` 为桩。

### 2.3 迁移前必修项

| # | 问题 | 位置 | 修仙处理 |
|---|---|---|---|
| ① | `find_target_npc` 无触发器、eval 恒 TRUE、进度 key 误写 `enhance_equipment_count` | `CustomDefinition/FindNPC.ts` | 改为"对话节点完成/到达区域/NPC交互"谓词 |
| ② | `recycle_equipment_count` 触发器空 `{}` | `CustomDefinition/RecycleEquipment.ts` | 回收系统真正发成功事件后才接入 |
| ③ | 收集进度未完成时百分比恒 0 | `CustomDefinition/CollectItems.ts` | 用真实 cur/target |
| ④ | 周常导入分类写成 DAILY | `Import/ImportQuestData.ts` | 独立周常类别或统一周期字段 |
| ⑤ | 快照键疑似读写不一致 | `Impl/QuestServiceImpl.ts` | 补"接取→推进→存档→读档→领奖"回归测试，通过后统一序列化协议 |
| ⑥ | 击杀监听耦合+每杀同步全刷 | `CustomDefinition/KillCount.ts` | 监听器单一职责 + flush 每 tick 合批 |
| ⑦ | 残留 `print/print_r` | `Impl/QuestServiceImpl.ts` | 上线前清理 |
| ⑧ | 一任务一条件树，缺显式步骤机 | 框架级 | 新手 1.2—1.8 必须新增 StepRuntime（见 §3） |
| ⑨ | 交付可被绕过 | `NPCID2` 主要给 UI 导航 | 交付须成为明确步骤/条件，不靠 UI 约束 |
| ⑩ | 测试非自动化 | `test/TestQuest.ts` 关键断言注释 | 建事件→状态→进度→领奖→重载自动验收 |

---

## 3. 任务 + 步骤 双层模型

旧框架条件树只判"是否满足"，新手教学还要判"现在该教什么"，因此必须新增显式步骤机。

```
QuestDef
  ├─ taskId / category / scope / trigger / repeat / rewards
  └─ StepDef[]
       ├─ stepId / title / objectiveMode
       ├─ enterCondition / objectives
       ├─ onEnter（导航/教学/传送/演出）
       ├─ onComplete（对白/解锁/下一步骤）
       └─ deliveryRule / failRule

QuestInstance
  ├─ status / currentStepId / stepProgress
  ├─ claimed / instanceId / baseline facts
  └─ updatedAt / version
```

例：1.3 炼丹任务的顺序步骤——到灵植园 → 药童对白 → 采集凝露草 → 周文扬对白 → 炼 3 颗引气丹 → 服 1 颗 → 调息完成。这些不能平铺进一个 `all` 条件树，否则玩家可能在教学前就满足后续条件。

---

## 4. 事件与谓词契约

事件由领域系统广播，谓词由 RuleTree 调用，任务只写谓词 + 参数。

复用度：★ 直搬 / ◐ 旧有需改 / ＋ 修仙新增

| 领域事件 | 谓词示例 | 复用度 | 优先级 | 适用任务 | 说明 |
|---|---|---|---|---|---|
| `combat.unit_killed` | `kill_count_ge(monsterId,count,scope)` | ★ | V1 | 1.2/1.6/1.7/1.8 | scope 分个人/房间/实例 |
| `quest.claimed` | `completed_quest(taskId)` | ★ | V1 | 全链 | 后续任务显示/接取条件 |
| `dialogue.node_completed` | `dialogue_node_completed(npcId,dialogueId,nodeId)` | ＋ | V1 | 1.2—1.8 | 对话完成，非"打开过对话框" |
| `region.entered` / `movement.arrived` | `arrived_at_region(sceneId,rectId)` | ◐ | V1 | 1.3—1.8 | 区域场景均用配置 ID |
| `item.changed` | `item_count_ge(itemId,count,invScope)` | ◐ | V1 | 1.2/1.7 | 持有型判定 |
| `drop.picked` | `pickup_count_ge(itemId,count)` | ＋ | V1 | 1.2 | 首次拾取教学，区别于持有量 |
| `item.used` / `item.equipped` | `item_used_ge` / `equipment_equipped` / `manual_learned` | ◐/＋ | V1 | 1.2—1.5 | 背包解锁/穿戴/服丹/秘籍激活 |
| `player.level_changed` | `player_level_ge/_lt` | ★ | V2 | 1.5 | V0/V1 无修为增长 |
| `gather.completed` | `gather_count_ge(nodeType/itemId,count)` | ＋ | V4 | 1.3/1.7 | 采集行为与持有量分别判定 |
| `alchemy.recipe_completed` | `recipe_crafted_ge(recipeId,count)` | ＋ | V4 | 1.3 | 以配方/产物 ID 判定 |
| `cultivation.settled` | `meditation_duration_ge` / `cult_ge` | ＋ | V2 | 1.3/1.5/1.7 | 在线每 3 秒/离线批量结算 |
| `skill.proficiency_changed` | `proficiency_ge(skillId,value)` | ＋ | V5 | 1.4 | 功法学习与熟练度分开 |
| `realm.changed` | `realm_ge(realm,subLevel)` | ＋ | V2 | 1.7 | 境界系统权威发出 |
| `breakthrough.finished` | `breakthrough_result(id,success)` | ＋ | V2 | 1.8 | 首次保底/心魔/雷劫由突破系统结算 |
| `bounty.turned_in` | `bounty_completed` / `turn_in_at_npc` | ＋ | V1+ | 1.6 | 新手首单固定可用，不被日刷池顶掉 |
| `sect.contribution_changed` | `sect_contribution_ge` | ＋ | V5 | 宗门线 | 宗门/声望 |
| 组合子 | `all/any/not` 递归 | ★ | V1 | 复合条件 | 境界+材料+灵石同时满足等 |

事件只带稳定 ID（monsterId/itemId/recipeId/npcId/dialogueNodeId/sceneId/realmId），不用中文显示名做逻辑条件。

---

## 5. 作用域、存档与领奖规则

### 5.1 三种作用域

| 作用域 | 适用内容 | 例子 |
|---|---|---|
| 个人存档 | 主线、突破材料、首次筑基、独有 BOSS、教学解锁 | 1.2—1.8 主进度 |
| 房间实例 | 普通怪击杀、普通掉落、可组队悬赏、临时副本 | 1.2/1.4 副本、部分 1.6 悬赏 |
| 全服表现 | 世界播报、活动状态、排行榜 | 1.8 筑基播报（非任务完成事实） |

### 5.2 最小存档字段

`task_id / status / current_step_id / step_progress` · `claimed / completed_total / period_key / completed_in_period` · `instance_id / baseline_facts / updated_at / version` · **奖励幂等键**（防断线重登/重复点击/网络重试的二次扣料或二次发奖）。

### 5.3 领奖原子顺序

服务端校验当前步骤和交付 NPC → 原子扣除任务材料 → 写任务完成/领奖幂等记录 → 发奖或进补发邮件 → 保存 → 发 UI/播报事件。任何一步失败可回滚，幂等键保证重放不二次发奖。

---

## 6. 版本路线

### 6.1 总览

| 版本 | 项目版本名 | 任务系统范围 |
|---|---|---|
| V0 | 内部技术验收 | 仅存档占位字段，不跑任务 |
| V1 | 战斗首爽版 | 任务引擎内核 + 新手 1.2 |
| V2 | 修炼突破版 | 修炼/境界/突破谓词 + 1.5/1.7/1.8 |
| V3 | 暗黑刷宝版 | 可选装备/词缀谓词接入 |
| V4 | 生产消化版 | 炼丹谓词 + 1.3 + 宗门任务框架 |
| V5 | 长线生活版 | 功法谓词 + 1.4 + 日常/周常/悬赏池 |
| V6 | 飞升轮回版 | 轮回相关任务类型 |
| V7 | 全服生态版 | 世界事件/排行榜/异步 PVP 任务 |

### 6.2 V0 — 内部技术验收

**任务系统不做任何可玩内容。** 依据 P01 边界：V0 正面清单 10 项（房间/建角/属性/战斗/怪物/掉落/背包/存档/配置加载/UI）不含任务系统；需完整内容才有效果的系统一律后置。

唯一动作：在 V0 存档结构中预留任务占位字段（int/空表，与命格/道器/轮回占位同级），使 V1 起任务落盘不必迁移旧档。对应工单：`QUEST-SAVE-00`。

RuleTree 引擎可在此版本以纯 dev 单元测试先行验证，但不作为 V0 交付项。

### 6.3 V1 — 战斗首爽版

**任务引擎首次落地，跑通新手 1.2。**

任务引擎内核：
- 移植 QuestSystem 内核：RuleTree 三态引擎 + Anchor 事件总线 + StepRuntime 双层状态机 + rev 增量快照
- 修复迁移清单第 ③④⑥⑦ 项，回归测试验证第 ⑤ 项
- 谓词最小集：`kill_count_ge` / `completed_quest` / `dialogue_node_completed` / `arrived_at_region` / `item_count_ge` + `_init` 注册
- 重写 `find_target_npc`（原为桩，eval 恒 TRUE）

步骤与 UI：
- StepRuntime + 步骤存档/恢复
- 任务追踪 HUD + 任务面板 + NPC 头顶气泡
- 新手 1.2「试炼幻境·首次击杀」全链配置（事件→步骤→状态→存档点→UI 提示）
- 1.6「首次委托」框架就绪：固定新手悬赏，不被日刷池顶掉

V1 结束时状态：玩家进房 → 进试炼幻境 → 杀怪 → 拾取 → 背包解锁 → 穿装吃丹 → 交付 → 完整任务闭环。

### 6.4 V2 — 修炼突破版

**修炼/境界/突破谓词接入，跑通 1.5/1.7/1.8。**

新增谓词：
- `cultivation.settled`（打坐结算）
- `player.level_changed`（修为/等级变化）
- `realm.changed`（境界变更）
- `breakthrough.finished`（突破结果）

新增任务：
- 1.5「修炼基础」：打坐 30S、修为增长、离线结算、功能引导
- 1.7「收集突破材料」：炼气九层触发、BOSS 掉落、持有量校验、材料保护
- 1.8「破境筑基」：突破入口、个人秘境、心魔/雷劫结算、世界播报

V2 结束时状态：完整的新手修炼→突破闭环。玩家从击杀教学自然过渡到修炼成长，首次突破是体验高峰。

### 6.5 V3 — 暗黑刷宝版

**任务系统不新增独立内容线。** V3 聚焦装备/词缀/偷渡/高难区域的刷宝循环，任务系统不与之耦合。

可选接入：装备相关谓词（如"穿戴 X 品质装备"）供后续日常/周常复用，但不强制。

### 6.6 V4 — 生产消化版

**炼丹系统就绪，跑通 1.3。宗门任务框架启动。**

新增谓词：
- `gather.completed`（采集完成）
- `alchemy.recipe_completed`（炼丹完成）

新增任务：
- 1.3「丹道初窥·首次炼丹」：采凝露草 → 炼引气丹×3 → 服丹 → 调息

宗门任务框架：
- 长老服务任务（五堂基础交付类任务）
- 宗门贡献与声望挂钩

V4 结束时状态：炼丹教学接入新手线，宗门任务体系初具框架。

### 6.7 V5 — 长线生活版

**功法系统就绪，跑通 1.4。任务内容层全面铺开。**

新增谓词：
- `skill.proficiency_changed`（功法熟练度）
- `sect.contribution_changed`（宗门贡献）

新增任务：
- 1.4「长老授业·传授功法」：秘籍激活 → 学功法 → 试炼打怪 → 熟练度 → 交付

任务内容层：
- 日常任务系统（每日刷新，简单交付/击杀/采集）
- 周常任务系统（周期计数，奖励梯度）
- 悬赏池完整（分类/接取/追踪/交付，防新手断链）
- 师门任务链
- 宗门声望任务完整

V5 结束时状态：新手线全部七任务可跑通（含占位补丁衔接），日常/周常/悬赏/师门形成稳定的任务内容供给。

### 6.8 V6 — 飞升轮回版

轮回相关任务类型：
- 轮回引导任务（首次飞升/轮回流程教学）
- 跨轮回任务（保留部分任务进度或给予轮回专属任务）
- 轮回记录与大事记展示

### 6.9 V7 — 全服生态版

世界级任务：
- 世界事件驱动任务（全服状态变化触发）
- 排行榜关联任务
- 异步 PVP 任务（斗法擂台/丹道大会等）

---

## 7. 需产品确认项

以下决策必须在进入字段/编码前裁定。

| 优先级 | 事项 | 影响范围 |
|---|---|---|
| P0 | 1.8 正式入口是"突破秘境"还是"心魔秘境" | 场景 ID、任务文案 |
| P0 | 新手任务是否严格按步骤顺序、不允许提前完成 | StepRuntime 设计、回溯计数策略 |
| P0 | 提前击杀/提前持有材料/提前炼成丹能否计入 | 事实基线、教学跳过风险（旧代码 BaseLineQuery 默认不回溯） |
| P0 | "可完成"后是否必须在指定 NPC 对话交付 | COMPLETABLE 状态、领奖按钮与 NPC 交付关系 |
| P0 | 首次筑基材料何时扣、失败如何处理、首次是否恒 100% 成功 | 幂等、补救、存档、世界播报 |
| P1 | 1.6 首个悬赏是固定任务还是日刷池保底项 | 新手断链防护 |
| P1 | 悬赏周期规则（完成一轮需几个？） | 周期计数、奖励、面板文案 |
| P1 | 起始境界数值（炼气一层/炼气七重）与 1.2 对白统一 | 1.2/1.5/1.7 阈值配置 |
| P1 | 炼丹(1.3)/功法(1.4)在其系统就位前是否做简化占位 | 新手线在 V2-V4 间是否断链 |

---

## 8. 附录：工单拆分建议

对应《工作任务拆分表》中任务系统缺口，建议新增以下工单：

| 编号 | 版本 | 层级 | 内容 |
|---|---|---|---|
| `QUEST-SAVE-00` | V0 | 核心层 | 存档结构预留任务占位字段 |
| `QUEST-CORE-01` | V1 | 核心层 | 移植 QuestSystem 内核：RuleTree + Anchor + StepRuntime + rev 快照，修 bug ③④⑥⑦，回归测试验证 ⑤ |
| `QUEST-CORE-02` | V1 | 核心层 | 谓词最小集 + `_init` 注册，重写 `find_target_npc` |
| `QUEST-STEP-01` | V1 | 核心层 | StepRuntime + 步骤存档/恢复 |
| `QUEST-UI-01` | V1 | UI 层 | 任务追踪 HUD + 任务面板 + NPC 头顶气泡 |
| `QUEST-FLOW-01` | V1 | 核心层 | 新手 1.2 全链配置 |
| `QUEST-FLOW-02` | V2 | 核心层 | 1.5/1.7/1.8 全链配置 |
| `QUEST-FLOW-03` | V4 | 核心层 | 1.3 全链配置 + 宗门任务框架 |
| `QUEST-FLOW-04` | V5 | 核心层 | 1.4 全链配置 + 日常/周常/悬赏池/师门任务 |
