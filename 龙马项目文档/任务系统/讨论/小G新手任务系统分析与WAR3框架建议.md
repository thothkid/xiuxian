# 新手任务系统分析与 WAR3 框架建议

## 口径说明

本报告分成两层：

1. **原文事实**：第一部分以 `E:\thoth\横向\WAR3修仙项目\龙马项目文档\任务系统\小C新手任务流程_截图逐字提取.md` 为主，不把原文中的病句、重复字、占位符或前后不一致改成通顺版本。
2. **系统分析与建议**：第二至第四部分是基于 MMORPG 通用做法、WAR3 实现能力、旧项目代码和修仙项目资料的设计判断，不等同于截图原文。

---

## 一、截图中的任务数量、名称、动作与功能

### 1.1 任务总数

截图中共有 **8 个主线任务：1.1—1.8**。

| 任务 | 小C原文任务名称 | 原文中出现的主要动作类型 | 需要对接的功能 |
|---|---|---|---|
| 1.1 | 加入宗门 | 出生自动触发、与莫黎长老对话、学会移动、走到大殿广场、找到陆青 | 任务自动触发、NPC对话、移动/镜头教学、区域/到达判定、NPC任务标记、任务追踪 |
| 1.2 | 试炼幻境 — 首次击杀 | 对话、获得背包格子解锁、进入幻境、击杀4只“XXXX”、拾取掉落、使用背包道具、穿装备、吃丹、返回交任务 | 对话、背包解锁、副本进出、击杀监听、掉落生成、拾取监听、装备/物品使用监听、交付判定 |
| 1.3 | 丹道初窥 — 首次炼丹 | 前往灵植园、偶遇采药师兄（姐）、采集凝露草、获得炼丹材料、领取“引气丹”×3制作任务、炼丹、使用丹药、打坐调息 | 采集点、采集完成、材料入包、配方/炼丹、丹药使用、丹毒、调息进度、任务步骤控制 |
| 1.4 | 长老授业 - 传授功法 | 遇莫长老、获得秘籍、点击秘籍激活功法技能、进入试炼幻境、打怪、获得功法熟练度 | NPC对话、物品/秘籍使用、技能解锁、技能学习、场景/副本进出、战斗完成、熟练度变化 |
| 1.5 | 再遇陆青 - 修炼基本 | 对话、打坐30S、升1级、修为持续增长、离线闭关提示、获得门内弟子服饰 | 打坐状态、计时、修为增长、等级/境界变化、装备/装扮获得、离线结算、任务介绍文本 |
| 1.6 | 历练委托 — 首次委托任务接取 | 与孙管事对话、打开任务面板、了解世界/宗门/悬赏任务、接取第一个悬赏任务、完成一轮（10个一轮？）、与孙管事对话 | 任务栏/任务面板、任务分类、刷新、悬赏任务接取、击杀或收集委托、每日限制、任务交付、宗门贡献 |
| 1.7 | 筑基之路 — 收集突破材料 | 修为达到炼气9层、刷新突破任务、接取任务、魔化BOSS掉落筑基核心-魔气结晶、收集副材XXXX×5和灵草×3、灵石×100、交付 | 修为/境界监听、任务自动刷新、BOSS击杀、掉落/保底、物品数量、采集、灵石数量、材料齐集、任务交付 |
| 1.8 | 破境筑基 — 首次大境界突破 | 开启突破、前往“突破秘境”、击败心魔、雷劫倒计时、首次炼气突破筑基、全屏特效、世界播报、境界晋升 | 突破面板、突破事件、秘境实例、镜像分身、击杀、天气/雷劫、成功率、境界变更、播报、奖励幂等、章节结束 |

### 1.2 按动作类型汇总

| 动作类型 | 出现任务 | 说明 |
|---|---|---|
| NPC对话/交付 | 1.1—1.8 | 几乎贯穿全部主线；不能只做“靠近NPC”，要区分对话节点和任务交付节点。 |
| 移动/到达/导航 | 1.1、1.3、1.4、1.6、1.7、1.8 | 包含山门、大殿、灵植园、功法阁、勤务堂、渡劫台和秘境。 |
| 击杀怪物 | 1.2、1.4、1.6、1.7、1.8 | 既有普通怪数量，也有魔化BOSS、心魔镜像等特殊目标。 |
| 拾取/收集物品 | 1.2、1.3、1.6、1.7 | 包括地面掉落、采集材料、背包数量和突破材料齐集。 |
| 使用物品 | 1.2、1.3、1.4、1.5 | 穿装备、吃丹、点击秘籍、获得弟子服饰。 |
| 生产/炼丹 | 1.3 | 需要配方、材料、炼制结果、丹药使用和丹毒规则。 |
| 打坐/计时/离线 | 1.3、1.5 | 1.3是短时调息；1.5是30秒修炼并展现离线闭关。 |
| 任务系统自身 | 1.6、1.7 | 任务分类、任务栏、每日刷新、世界任务、宗门任务、悬赏任务。 |
| 境界/突破 | 1.7、1.8 | 炼气圆满、材料齐集、心魔、雷劫、筑基和世界播报。 |

### 1.3 原文中仍然未定或前后不一致的地方

这些是小C原文事实，不在抽取阶段擅自修正：

- 怪物名仍是“XXXX”。
- 多处任务奖励写成“奖励种类需要确认”。
- 1.3 的炼丹教学写有“需要有配方”。
- 1.6 写有“完成一轮（10个一轮？）”。
- 1.7 有“孙执事”和“孙管事”等称呼差异。
- 1.8 的目标行写“前往突破秘境”，正文又写“前往心魔秘境”。这是原文自身的口径冲突，不能在逐字抽取层替它统一。

---

## 二、通用 MMORPG 任务系统与 WAR3 可实现功能

### 2.1 一般任务系统应有的功能层

| 层 | 通用功能 | 典型数据/接口 |
|---|---|---|
| 任务定义 | 任务ID、名称、分类、描述、NPC、地点、对话、奖励、重复规则 | `QuestDef`、配置表、版本号 |
| 触发与展示 | 自动触发、前置任务、等级/属性/区域/时间条件、NPC头顶标记 | `showCond`、`trigger`、`visible` |
| 接取 | NPC接取、任务栏接取、自动接取、每日/每周限制、主线互斥 | `tryAccept`、`accepted` |
| 目标 | 击杀、收集、交付、到达、对话、使用、装备、生产、护送、计时、事件结果 | Objective/Predicate |
| 条件组合 | 全部满足、任一满足、非、嵌套条件、前置任务链 | `all`、`any`、`not`、RuleTree |
| 运行时状态 | 未显示、可见、可接、进行中、可完成、已完成、已领奖、失败、放弃 | 状态机/任务实例 |
| 进度 | 当前值、目标值、完成百分比、分目标、阶段和步骤 | `cur/target/done`、step index |
| 事件监听 | 将游戏行为转成任务可查询事实，并刷新受影响任务 | EventBus、Fact/Anchor、DepKey |
| 对话与演出 | 条件对白、节点对白、镜头、传送、特效、音效、世界播报 | Dialogue/Sequence |
| 导航 | NPC导航、区域导航、目标点、传送、返回点、场景/副本入口 | RectID、SceneID、NPCID |
| 奖励 | 经验/修为、货币、物品、技能、配方、称号、解锁、声望、贡献 | RewardHandler |
| 领奖与幂等 | 可完成和已领奖分离，防止重复领取，背包满补发 | `completed/claimed`、邮件/临时仓库 |
| 重复与周期 | 一次性、永久重复、每日、每周、活动期、次数上限、刷新 | Period/Reset |
| 持久化 | 掉线恢复、跨场景恢复、服务器权威、版本迁移、增量保存 | Snapshot/Delta |
| UI | 任务栏、详情页、进度条、标记、追踪目标、分类页签、提示 | Custom Frame/UI |
| 工具与测试 | 配置校验、GM发任务、事实注入、事件回放、任务链验收、埋点 | Debug/Replay/Telemetry |

### 2.2 WAR3 中通常可以直接利用的事件

WAR3 原生可以提供一部分底层触发，任务系统不需要自己轮询所有对象：

- 单位死亡、单位击杀单位、单位进入区域。
- 玩家进入游戏、离开游戏、选择单位、选择物品、资源变化。
- 英雄升级、单位属性变化、技能/物品使用、施法或技能效果。
- 物品获得、丢失、叠加、装备、卸下。
- 定时器、游戏时间、日夜变化、周期刷新。
- 单位移动、到达目标、场景切换、传送完成等自定义事件。

### 2.3 WAR3 需要自己补齐的部分

WAR3 原生任务对象只能承担很薄的显示层，不能直接承担修仙项目的完整任务逻辑。以下内容要由项目自己的 Lua/TypeScript/JASS 框架和事件总线实现：

- NPC对话节点、对话完成、条件对白和交付节点。
- 背包格子解锁、炼丹、采集、功法学习、修炼、丹毒、境界突破等领域事件。
- 多步骤任务、任务阶段、教学步骤和演出编排。
- 服务器存档、重连恢复、任务实例ID和多人房间隔离。
- 自定义任务面板、导航、任务标记、提示和世界播报。

### 2.4 WAR3 实现时的硬约束

- 任务逻辑要避免每个任务单独开轮询；应由领域系统发事件，任务按 `DepKey` 增量刷新。
- UI必须区分本地玩家显示与服务器权威状态，不能把本地Frame状态当作任务完成事实。
- 打坐、倒计时、离线闭关不要每秒向服务器发送一条任务事件；用开始时间、结束时间或累计区间结算。
- 任务监听器要单例注册或可销毁，避免玩家重进/重载时重复订阅。
- 物品、单位、NPC、场景、区域最好都使用稳定的配置ID，不把显示名称作为逻辑主键。
- WAR3 地图脚本、存档大小、网络调用和同屏单位数量都有限，任务实例、进度字段和日志要控制规模。

---

## 三、上一个项目 `E:\works\legendary-map` 已实现的任务框架

### 3.1 总体链路

```text
任务配置表.xlsx
    ↓ export_quest.py
ConfigQuestDef.ts / ConfigQuestBra.ts / ConfigQuestPredDef.ts
    ↓ ImportQuestData.ts
QuestDefRepo
    ↓ 每个玩家
TaskServiceImpl
    ↓ RuleTree + AnchorManager + EventBus
任务状态 / 进度 / 快照 / 奖励 / UI / 服务器任务API
```

### 3.2 已实现的核心框架

#### A. 配置与任务定义

旧项目已经把任务从代码中抽成配置：

- 主线、支线、日常、周常四类入口。
- 任务名、描述、接取NPC、交付NPC、发布对白、完成对白、未完成对白。
- 显示条件、接取条件、完成条件和参数数组。
- 奖励经验、金币、灵符、最多5项物品。
- 接取后的目标区域 `TargetRectID`，支持场景名转换成区域ID。
- `ONCE`、`REPEATABLE`、`PERIODIC DAILY/WEEKLY` 三类重复策略。

#### B. 状态机与任务视图

服务器快照层有：

- `NOT_ACCEPTED`、`ACCEPTED`、`COMPLETED`。
- `claimed`、`completedTotal`、`completedInPeriod`、`periodKeySec`。
- 任务实例ID、版本号、基线数据、进度数据。

面向UI又有一层视图状态：

- `HIDDEN`、`VISIBLE`、`ACCEPTABLE`、`ACTIVE`、`COMPLETABLE`、`COMPLETED`。

这两个状态层分开是正确方向：服务器事实不等同于玩家看到的任务栏状态。

#### C. RuleTree 条件树

旧项目不是在任务里写死一堆 `if`，而是：

- 任务定义引用 `showCondId`、`acceptCondId`、`completeCondId`。
- 条件配置支持 `pred`、`all`、`any`、`not`。
- `PredRegistry` 注册具体谓词，解析参数、声明依赖、计算 TRUE/FALSE/UNKNOWN。
- `depKey` 建立“事实变化 → 受影响任务”索引。
- 只有相关事实变化时才刷新相关任务。

#### D. 事实锚点与事件监听

旧项目用 `se.on(...)` 监听领域事件，把结果写入 `AnchorManager`，再交给任务服务：

| 旧项目谓词 | 监听事件/事实 | 作用 |
|---|---|---|
| `kill_count_ge` | `单位-击杀单位`，累计 `kill.monster.{id}` | 击杀指定怪物数量 |
| `collect_items` | 获得/失去/叠加物品，读取背包数量 | 持有指定物品数量，领奖时扣除 |
| `completed_quest` | `玩家-结束任务`，累计已结束任务 | 任务前置链 |
| `enhance_equipment_count` | `物品-强化成功` | 强化次数 |
| `equip_target_grade_equipment` | 装备/卸下物品，重算各档次装备数量 | 穿戴指定档次装备 |
| `player_level_ge/lt` | 进入游戏、单位升级成功 | 等级条件 |
| `find_target_npc` | 当前代码无实际监听 | 代码占位，不能视为已实现找NPC |
| `recycle_equipment_count` | 当前代码无实际监听 | 代码占位，不能视为已实现回收装备 |

#### E. 进度视图与UI

- 每个谓词可注册自己的 `ProgressSpec` 和玩家态渲染器。
- 进度统一为 `cur/target/done`，任务可以显示多个分目标。
- 进度写入快照 `progressData`，支持增量比较。
- 任务面板最多显示5个槽位。
- 主线优先显示进行中/可完成任务，没有进行中的主线时显示下一个可接主线。
- 支线按任务ID排序。
- 支持NPC导航；找不到NPC时可传送到出生点或NPC所在区域，再移动到NPC附近并自动开启对话。

#### F. 奖励、存档和网络

- 领取时执行经验、金币、灵符和物品奖励。
- 物品奖励支持概率字段。
- 奖励发放后发出 `玩家-获得任务奖励` 事件并显示提示。
- 任务生命周期事件包括接取、完成条件达成、结束/领奖、状态变化、视图更新。
- 通过 `createTask`、`setTaskProgress`、`finishTask` 对接服务器任务接口。
- 使用 `rev/baseRev/changedTasks` 做快照增量同步。

### 3.3 旧项目已实现程度与问题

| 项目 | 判断 |
|---|---|
| 击杀任务 | 已有完整监听、事实累计、条件判定和进度渲染。 |
| 收集物品 | 有监听和领奖扣除；进度百分比代码目前未按当前值计算，属于实现缺陷。 |
| 等级/前置任务 | 已有。 |
| 装备/强化 | 已有部分。 |
| 找NPC | 目前是占位实现，谓词直接返回 TRUE，不能作为真实完成条件。 |
| 回收装备 | 目前只有谓词和渲染，触发器为空。 |
| 日常/周常 | 有周期轮转；代码中周常创建时 `category` 写成了 `DAILY`，需要修正。 |
| 任务多步骤 | 旧框架偏向“一个任务一棵条件树”，没有为新手教学提供完整的显式步骤机。 |
| NPC交付 | `NPCID2`主要被UI用于导航；完成条件本身必须显式配置对话/交付谓词，否则存在绕过交付的风险。 |
| 快照键名 | `loadFromSnapshot`读取 `task_{id}`，而 `getFullSnapshot`写入数字ID键，存在序列化/恢复键名不一致风险。 |
| 测试 | `TestQuest.ts`提供了演示流程，但关键事实变更和日志多处注释掉，不能当作完整自动化验收。 |

---

## 四、修仙新项目任务框架建议

### 4.1 总原则：任务系统只做“编排层”

任务系统不要自己实现战斗、背包、炼丹、修炼或突破。它只做四件事：

1. 监听其他系统发出的稳定事件。
2. 把事件转换成玩家任务事实和进度。
3. 按任务定义推进阶段、判定条件和开放下一任务。
4. 调用奖励、对话、导航、教学、演出和存档接口。

这样可以复用旧项目的 `QuestDefRepo + RuleTree + TaskServiceImpl + ProgressView`，但要把新项目的事件和多步骤能力补上。

### 4.2 建议的任务事件/事实类型

#### 玩家与场景

- `player.enter_game`
- `player.create_character`
- `player.reconnect`
- `scene.enter / scene.exit`
- `region.enter / region.leave`
- `teleport.completed`
- `movement.arrived`
- `instance.enter / instance.exit`

#### NPC、对话和教学

- `npc.interact`
- `dialogue.started`
- `dialogue.node_completed`
- `dialogue.completed`
- `task.delivery_completed`
- `tutorial.step_completed`
- `tutorial.system_unlocked`

#### 战斗、掉落和拾取

- `combat.unit_killed`
- `combat.boss_killed`
- `combat.instance_kill`
- `drop.created`
- `drop.picked`
- `item.obtained / item.lost / item.stacked`
- `unique_boss.killed_once`

#### 采集、炼丹、物品和装备

- `gather.node_completed`
- `gather.item_obtained`
- `alchemy.started`
- `alchemy.recipe_completed`
- `item.used`
- `item.equipped / item.unequipped`
- `manual.learned`
- `skill.unlocked`
- `skill.proficiency_changed`

#### 修炼、境界和突破

- `cultivation.started`
- `cultivation.tick_batch`
- `cultivation.ended`
- `cultivation.offline_settled`
- `cultivation.value_changed`
- `realm.changed`
- `breakthrough.started`
- `heart_demon.defeated`
- `tribulation.result`
- `breakthrough.succeeded / breakthrough.failed`

#### 宗门、委托和时间

- `task_board.opened`
- `bounty.accepted / bounty.completed / bounty.turned_in`
- `sect.contribution_changed`
- `sect.reputation_changed`
- `time.daily_reset / weekly_reset`
- `time.period_window_opened`
- `weather.changed`
- `world_event.started / ended`

事件只携带稳定ID和必要参数，例如 `monsterId`、`itemId`、`recipeId`、`npcId`、`dialogueNodeId`、`sceneId`、`realmId`，不要把中文显示名作为任务逻辑条件。

### 4.3 建议的修仙谓词

在旧项目谓词基础上，优先增加：

| 谓词 | 典型参数 | 对应任务 |
|---|---|---|
| `dialogue_node_completed` | npcId、dialogueId、nodeId | 1.1—1.8 |
| `arrived_at_region` | sceneId/rectId | 1.1、1.4、1.6、1.7 |
| `tutorial_step_completed` | tutorialId、stepId | 1.1、1.2、1.3、1.5 |
| `instance_completed` | instanceId、result | 1.2、1.4、1.8 |
| `kill_count_ge` | monsterId、count、scene/instance过滤 | 1.2、1.6、1.7、1.8 |
| `item_count_ge` | itemId、count、scope | 1.2、1.7 |
| `gather_count_ge` | nodeType/itemId、count | 1.3、1.7 |
| `recipe_crafted_ge` | recipeId、count | 1.3 |
| `item_used_ge` | itemId、count | 1.2、1.3 |
| `equipment_equipped` | slot/item/grade | 1.2、1.5 |
| `manual_learned` | manualId/skillId | 1.4 |
| `proficiency_ge` | skillId、value | 1.4 |
| `meditation_duration_ge` | durationSec | 1.3、1.5 |
| `realm_ge` | realm、subLevel | 1.7 |
| `cult_ge` | currentCult、threshold | 1.5、1.7 |
| `breakthrough_materials_ready` | breakthroughId | 1.7、1.8 |
| `breakthrough_result` | breakthroughId、success | 1.8 |
| `bounty_completed` | bountyId/type/count | 1.6 |
| `sect_contribution_ge` | value | 后续宗门任务 |
| `completed_quest` | taskId | 主线链和解锁链 |

旧项目的 `all/any/not` 继续复用；新手任务必须补“有序步骤”或“当前步骤”机制，不能只把所有目标并列放进一棵 `all` 树，否则玩家可能跳过教学顺序。

### 4.4 建议的运行时模型

定义层和实例层分开：

```text
QuestDef（配置，不随玩家变化）
  └─ StepDef[ ]（阶段、目标、对白、演出、下一步）

QuestInstance（玩家运行时）
  ├─ status
  ├─ currentStep
  ├─ progressData
  ├─ claimed
  ├─ instanceId
  ├─ startedAt/updatedAt
  └─ baseline/fact snapshot
```

每个 Step 至少应有：

- `stepId`
- `enterTrigger`
- `showCondition`
- `objectives`
- `onEnter`
- `onProgress`
- `onComplete`
- `nextStep`
- `fail/timeout`（需要时）

例如任务1.3不应只是一个“炼丹完成”条件，而应是：到达灵植园 → 与药童对话 → 采集完成 → 获取材料 → 找周丹师 → 炼制3颗 → 使用1颗 → 调息完成。

### 4.5 任务配置字段建议

在旧项目字段基础上增加：

- `triggerType`：自动、NPC、区域、前置任务、境界、世界事件、任务栏。
- `scope`：个人、房间共享、全服/唯一。
- `steps`：步骤数组。
- `objectiveMode`：全部、任一、顺序、并行。
- `deliveryRule`：必须与哪个NPC、哪个对话节点完成交付。
- `scene/instanceRule`：允许在哪个场景或副本内计数。
- `progressMode`：累计、持有量、事件次数、当前状态、持续时间。
- `resetRule`：不重置、每日、每周、活动期、境界阶段。
- `rewardPolicy`：直接入包、邮件补发、失败重试、唯一奖励。
- `unlockFlags`：背包格、技能、配方、任务栏、区域、突破入口。
- `sequenceId`/`chapterId`：章节和任务链索引。
- `version`：配置迁移和旧存档兼容。

### 4.6 与修仙项目资料的结合

#### A. 任务是个人进度，世界事件另建作用域

修仙项目已经区分个人存档世界、房间实例世界和全服经济世界。主线、突破材料、独有BOSS和首次筑基应按个人任务实例处理；普通刷怪、普通掉落和部分悬赏可使用房间事件；世界播报是表现层，不应把“播报成功”当作玩家任务事实。

#### B. 任务条件要接修仙真实事实

- 修为不是旧传奇经验，监听 `cultivation.value_changed` 或批量结算结果。
- 境界由境界系统权威变更，任务只读 `realm/realm_sub`。
- 丹药既可能即时增加修为，也可能产生持续加成和丹毒，任务监听“使用/炼制/效果结算”，不要只监听背包数量变化。
- 打坐每3秒结算一次或离线按时间结算，任务只接收批量结果，避免每秒刷事件。
- 突破是“修为满 + 材料齐 + 突破事件”的组合，不应由任务系统自己修改境界。
- 灵植、妖丹、魔核、突破主药要以物品ID和来源标签区分，避免“收集到同名物品”误计。

#### C. 任务链要与世界观口径先对齐

目前资料存在需要策划裁决的冲突：

- 世界观开发锚点写“上线即炼气一层外门弟子、跳过入门任务链”，而小C流程从“加入宗门”开始。
- 世界观写长老不排他、五堂开放服务；截图任务仍以加入宗门和单条长老主线表达。
- 小C 1.8 目标写“突破秘境”，正文写“心魔秘境”。
- 炼气九层/炼气圆满、孙执事/孙管事、灵植园/灵植圃等名称需要在配置字典中定稿。

任务代码不应替策划自动统一这些口径；应等正式ID、阶段和命名表确定后写入配置。

### 4.7 WAR3 落地建议

#### 第一阶段：复用旧框架，先做通用骨架

- 复用配置导入、任务仓库、玩家任务服务、RuleTree、依赖索引、快照增量和进度渲染层。
- 把旧项目的 `AnchorManager` 抽象为新项目统一的玩家事实层。
- 把 `se.on` 事件命名整理成稳定的领域事件枚举。
- 先完成 `dialogue_node_completed`、`region/scene_arrived`、`item_count`、`item_used`、`kill_count`、`gather_count`、`recipe_crafted`、`meditation_duration`、`realm_changed`、`breakthrough_result`。

#### 第二阶段：补多步骤新手任务

- 实现 StepRuntime、当前步骤、步骤进入/退出事件。
- 任务栏显示当前步骤，不显示一堆未来步骤。
- 每个步骤完成后写一次存档并支持掉线恢复。
- 1.1—1.8 作为第一条验收链，先不做复杂随机任务。

#### 第三阶段：接宗门、悬赏、世界事件

- 宗门任务、悬赏任务、世界任务共享同一任务定义和条件树。
- 日常/周常使用周期重置，不复制三套系统。
- 任务奖励统一接修为、灵石、宗门贡献、物品、功法/配方解锁和称号接口。
- 独有BOSS、机缘、屠魔录使用更高层的事件作用域，但仍可以复用任务条件和奖励模块。

### 4.8 旧项目代码迁移前必须修的点

1. `FindNPC` 不能再直接返回 TRUE，要接入对话/到达事件。
2. `RecycleEquipment` 要接入回收成功事件。
3. `collect_items` 的百分比应按 `cur/target` 计算。
4. 修正周常导入时的分类值。
5. 统一快照任务键的读写格式。
6. 明确 `COMPLETABLE` 与“找NPC交付”之间的关系，不能只靠UI提示保证玩家交付。
7. 给多步骤任务增加步骤运行时，不要把1.2、1.3、1.8压成一个完成谓词。
8. 把 `TestQuest.ts` 改成有实际断言的测试：事件输入、状态变化、进度、领奖幂等、重载恢复和周期轮转都要验收。

---

## 五、结论

当前最合理的路线不是重新发明一套任务系统，而是：

**以旧项目的 QuestSystem 为底座，保留配置导入、RuleTree、事实依赖刷新、快照增量、奖励处理和UI渲染；补齐修仙领域事件、多步骤 StepRuntime、NPC交付、采集/炼丹/打坐/突破谓词，以及WAR3下的存档和性能边界。**

新手1.1—1.8可以作为第一条任务系统验收链，但在进入配置和编码前，必须先裁决世界观“跳过入门任务链”与截图“加入宗门”这类口径冲突。
