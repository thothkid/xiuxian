# 修仙 ORPG · 任务系统优化基线 v1

> 本文以「小G新手任务系统分析与WAR3框架建议」为骨架，合并「小C修仙ORPG任务系统框架分析与建议」的路线图、监听速查表、拆分表缺口，并补充：事件优先级分层、已验证代码 bug 的文件锚点、以及**决定性的 V0 任务系统切片定义**（第六部分）。
>
> 目标定位：这是"整体规划 + 明确 V0 先做什么"的基线文档，供后续深入讨论使用。核心结论在第五、六部分。
>
> 口径：第一部分为原文事实（不改小C逐字稿的病句/占位符）；二至六部分为设计判断。

---

## 一、截图中的任务数量、名称、动作与功能

共 **8 个主线任务 1.1—1.8**（加入宗门 → 首次筑基，"通天大道第一章"）。

| 任务 | 名称 | 主要动作 | 需对接功能 |
|---|---|---|---|
| 1.1 | 加入宗门 | 出生自动触发、与莫黎长老对话、学移动、到大殿广场、找陆青 | 自动触发、NPC对话、移动/镜头教学、到达判定、NPC标记、任务追踪 |
| 1.2 | 试炼幻境·首次击杀 | 对话、背包解锁、进副本、杀4只"XXXX"、拾取、用背包道具、穿装、吃丹、交付 | 对话、背包解锁、副本进出、击杀监听、掉落、拾取监听、装备/物品使用、交付判定 |
| 1.3 | 丹道初窥·首次炼丹 | 到灵植园、遇药童、采凝露草、得材料、领引气丹×3、炼丹、服丹、调息 | 采集点、采集完成、材料入包、配方/炼丹、丹药使用、丹毒、调息进度、步骤控制 |
| 1.4 | 长老授业·传授功法 | 遇莫长老、得秘籍、点秘籍激活功法、进幻境、打怪、得熟练度 | NPC对话、秘籍使用、技能解锁/学习、副本进出、战斗完成、熟练度变化 |
| 1.5 | 再遇陆青·修炼基础 | 对话、打坐30S、升1级、修为增长、离线闭关提示、得弟子服饰 | 打坐状态、计时、修为增长、等级/境界变化、装扮获得、离线结算 |
| 1.6 | 历练委托·首次委托 | 与孙管事对话、开任务面板、了解三类任务、接首个悬赏、完成一轮(10个?)、交付 | 任务面板、任务分类、刷新、悬赏接取、击杀/收集委托、每日限制、交付、宗门贡献 |
| 1.7 | 筑基之路·收集突破材料 | 修为达炼气9层、刷突破任务、接取、魔化BOSS掉魔气结晶、收集副材+灵草+灵石、交付 | 修为/境界监听、任务自动刷新、BOSS击杀、掉落保底、物品数量、采集、材料齐集、交付 |
| 1.8 | 破境筑基·首次大突破 | 开启突破、进"突破/心魔秘境"、击败心魔、雷劫倒计时、筑基、全屏特效、世界播报 | 突破面板、突破事件、秘境实例、镜像分身、击杀、雷劫、成功率、境界变更、播报、幂等、章节结束 |

**动作类型汇总**：NPC对话/交付(1.1–1.8) · 移动/到达(1.1/1.3/1.4/1.6/1.7/1.8) · 击杀(1.2/1.4/1.6/1.7/1.8) · 拾取/收集(1.2/1.3/1.6/1.7) · 使用物品(1.2/1.3/1.4/1.5) · 生产炼丹(1.3) · 打坐/计时/离线(1.3/1.5) · 任务系统自身(1.6/1.7) · 境界/突破(1.7/1.8)。

**原文未定/前后不一致**（抽取层不擅改）：怪名"XXXX"；多处"奖励种类需要确认"；1.3"需要有配方"；1.6"完成一轮(10个一轮?)"；1.7"孙执事/孙管事"；**1.8 目标行"突破秘境"、正文"心魔秘境"口径冲突**。

---

## 二、通用 MMORPG 任务系统与 WAR3 可实现功能

### 2.1 任务系统应有的功能层

任务定义 · 触发与展示 · 接取 · 目标(击杀/收集/交付/到达/对话/使用/装备/生产/计时/事件结果) · 条件组合(all/any/not/RuleTree) · 运行时状态机 · 进度(cur/target/done/step) · **事件监听(EventBus/Anchor/DepKey)** · 对话演出 · 导航 · 奖励 · 领奖幂等 · 重复与周期 · 持久化(Snapshot/Delta) · UI · 工具与测试。

### 2.2 WAR3 原生可直接利用的事件

单位死亡/击杀单位/进入区域 · 玩家进入/离开游戏/选单位/选物品/资源变化 · 英雄升级/属性变化/技能物品使用/施法 · 物品获得/丢失/叠加/装备/卸下 · 定时器/游戏时间/日夜 · 移动到达/场景切换/传送完成(自定义)。

### 2.3 WAR3 需自己补齐（原生任务对象只是薄显示层）

NPC对话节点/交付 · 背包解锁/炼丹/采集/功法/修炼/丹毒/境界突破等领域事件 · 多步骤/阶段/教学演出编排 · 服务器存档/重连/任务实例ID/多人隔离 · 自绘任务面板/导航/标记/世界播报。

### 2.4 WAR3 硬约束（写进设计红线）

避免每任务单独轮询→领域系统发事件、按 DepKey 增量刷新 · UI 区分本地显示与服务器权威 · 打坐/倒计时/离线不逐秒发事件→按开始/结束/区间结算 · 监听器单例注册可销毁，防重进重复订阅 · 用稳定配置ID 不用显示名做主键 · 控制任务实例/进度字段/日志规模（存档与同屏预算有限）。

---

## 三、上一项目 `legendary-map` 已实现的任务框架（代码级，已核）

上一项目为 **TypeScript→TSTL→Lua**，任务系统在 `src/map/QuestSystem/`（约45文件），是**成熟的反应式配置驱动引擎**。

### 3.1 总体链路

```
任务配置表.xlsx → ConfigQuestDef/Bra/PredDef.ts → ImportQuestData.ts → QuestDefRepo
  → (每玩家) TaskServiceImpl → RuleTree + AnchorManager + EventBus(se)
  → 状态/进度/快照/奖励/UI/服务器任务API(/task/create|setprogress|finish)
```

### 3.2 已实现核心（可复用）

- **配置与定义**：主线/支线/日常/周常四入口；接取/交付NPC、四态对白、显示/接取/完成条件+参数、奖励(经验/金币/灵符/≤5物品)、`TargetRectID`寻路、`ONCE/REPEATABLE/PERIODIC(DAILY|WEEKLY)`重复策略。
- **双层状态**：生命周期(权威存档)`NOT_ACCEPTED/ACCEPTED/COMPLETED` + `claimed/completedTotal/completedInPeriod/periodKeySec/InstanceID/rev/baseline/progressData`；派生视图态`HIDDEN/VISIBLE/ACCEPTABLE/ACTIVE/COMPLETABLE/COMPLETED`。**两层分离是正确方向**。
- **RuleTree 三态条件树**：任务引用 showCondId/acceptCondId/completeCondId；支持 `pred/all/any/not`；`PredRegistry` 注册谓词(parseArgs/resolveDeps/eval→TRUE/FALSE/UNKNOWN)；`depKey` 建"事实变化→受影响任务"索引，**只在相关事实变化时增量刷新**。
- **Anchor 事实层**：谓词 `se.on(领域事件)` → 写 `AnchorManager`(Persistent存档/Runtime登录重算) → `submitDepChanges + flush`。
- **BaseLineQuery**：接取时记基线，进度＝当前−基线，**接取前的击杀不回溯计入**。
- **进度/UI**：谓词自带 ProgressSpec+渲染器，进度统一 cur/target/done，写快照 progressData 支增量比较；面板最多5槽；主线优先显示进行中/可完成；支持NPC导航（找不到→传送到出生点/NPC区域→靠近自动开对话）。
- **奖励/存档/网络**：领取发经验/金币/灵符/物品(带概率)，发 `玩家-获得任务奖励`；生命周期事件接取/完成/结束领奖/状态变化/视图更新；`rev/baseRev/changedTasks` 增量同步；服务器任务实例权威。

### 3.3 谓词/监听目录（代码实读）

| PredKey | 监听(se.on) / 锚点 | 状态 |
|---|---|---|
| `kill_count_ge` | `单位-击杀单位` → `kill.monster.{id}`(Persistent) | ✅ 完整 |
| `player_level_ge/_lt` | `单位-升级成功`、`玩家-进入游戏` → `player.level`(Runtime) | ✅ 完整 |
| `collect_items` | `单位-获得/失去/叠加物品` → `collect_items.{id}`；onClaim扣物 | ✅（进度条见坑③） |
| `completed_quest` | `玩家-结束任务` → `completed_quest.{id}`(Persistent) | ✅ 完整 |
| `enhance_equipment_count` | 强化事件 | ✅ |
| `equip_target_grade_equipment` | 装备/卸下→重算档次 | ✅ 部分 |
| `find_target_npc` | **无监听，eval 恒 TRUE** | ⚠️ 桩 |
| `recycle_equipment_count` | **CreateTrigger 空 `{}`** | ⚠️ 桩 |
| 组合子 `all/any/not` | RuleTree 层 | ✅ |

### 3.4 已验证的 bug / 待修点（含文件锚点，迁移前必处理）

| # | 问题 | 位置 | 影响 |
|---|---|---|---|
| ① | `find_target_npc` 恒返回 TRUE、无监听 | `CustomDefinition/FindNPC.ts`（CreateTrigger 空、eval 返回"TRUE"、进度key误写`enhance_equipment_count`） | "找NPC/到达"实为未实现——**新手线1.1/1.4/1.5/1.6/1.8全靠它** |
| ② | `recycle_equipment_count` 触发器为空 | `CustomDefinition/RecycleEquipment.ts`（`function CreateTrigger(){}`） | 回收类任务永远无法推进 |
| ③ | `collect_items` 进度条无分比 | `CustomDefinition/CollectItems.ts`（`percent: item.done ? 1 : 0`，对比 KillCount 的 `cur/target`） | UI只显示0%/100%，无"2/5"进度条观感 |
| ④ | 周常任务分类写成 DAILY | `Import/ImportQuestData.ts`（CreateWeeklyQuest `category:"DAILY"`，仅 period 为 WEEKLY） | 周常被当日常分类，UI/筛选错乱 |
| ⑤ | 快照键读写不一致 | `Impl/QuestServiceImpl.ts`（loadFromSnapshot 读 `string.format("task_%d")`，getFullSnapshot 写数字键 `tasksObj[tid]`） | **存档回读键名不匹配→任务回落默认态**，动存档格式，必须在V0前统一 |
| ⑥ | 击杀监听耦合+每杀同步全刷 | `CustomDefinition/KillCount.ts`（trigger 里混入 VIP计数/杀怪抽奖；每次击杀 `submitDepChanges+flush`） | 高刷怪频率下性能与耦合风险 |
| ⑦ | 残留调试输出 | `Impl/QuestServiceImpl.ts`（fullRecomputeAllTasks 里 `print/print_r`） | WC3 大量 print 掉帧 |
| ⑧ | 多步骤缺失 | 框架"一任务=一条件树"，无显式步骤机 | 新手教学顺序无法强制（见 4.4） |
| ⑨ | 交付可被绕过 | `NPCID2` 主要给UI导航；完成条件须显式配对话/交付谓词 | 否则玩家可不回NPC就完成 |
| ⑩ | 测试非自动化 | `test/TestQuest.ts` 关键事实变更/日志多注释 | 不能当验收 |

> ①②③④⑤ 是硬 bug；其中 **⑤ 触存档格式**、④ 触分类与刷新——这两个若带进 V0 会固化进存档与配置，**必须在 V0 移植时一并修**。①②⑧⑨ 因 V0 无对应内容，可按 V1 内容排期修。

---

## 四、修仙新项目任务框架建议

### 4.1 总原则：任务系统只做"编排层"

任务系统不实现战斗/背包/炼丹/修炼/突破，只做四件事：① 监听其他系统的稳定事件；② 转成玩家任务事实与进度；③ 按定义推进阶段、判定条件、开放下一任务；④ 调奖励/对话/导航/教学/演出/存档接口。→ 复用旧项目 `QuestDefRepo + RuleTree + TaskServiceImpl + ProgressView`，补上修仙事件与多步骤能力。

### 4.2 ★/＋ 监听类型速查表（合并自小C，核心交付）

**★ = 旧项目已实现可直搬；◐ = 旧项目有但需修/改语义；＋ = 修仙新增，需对应系统提供广播钩子。** 优先级列指该监听在哪个版本必需。

| 监听/谓词 | 事件源(se.emit) | 锚点 depKey | 复用度 | 优先级 | 新手任务 |
|---|---|---|---|---|---|
| `kill_count_ge` | `单位-击杀单位` | `kill.monster.{id}` | ★直搬 | **V0/V1** | 1.2/1.6/1.7/1.8 |
| `completed_quest` | `玩家-结束任务` | `completed_quest.{id}` | ★直搬 | **V0** | 全链前置 |
| `player_level_ge/_lt` | `单位-升级成功` | `player.level` | ★直搬 | **V0/V1** | 1.5 |
| `collect_items`/`item_count_ge` | `单位-获得/失去/叠加物品` | `collect_items.{id}` | ◐修进度条 | **V1** | 1.2/1.7 |
| `dialogue_node_completed` | 对话系统 | `dialogue.{npc}.{node}` | ＋新增 | **V1** | 1.1–1.8 |
| `arrived_at_region`/`find_npc` | 区域/NPC交互 | `region.{id}`/`npc.{id}` | ◐重写(①桩) | **V1** | 1.1/1.4/1.5/1.6/1.8 |
| `item_used_ge` | 物品使用 | `used.{id}` | ＋新增 | **V1** | 1.2/1.3 |
| `equipment_equipped` | 装备变化 | `equip.*` | ◐改语义 | **V1** | 1.2/1.5 |
| `gather_count_ge` | 采集点 | `gather.{type}` | ＋新增 | **V2** | 1.3/1.7 |
| `recipe_crafted_ge` | 炼丹炉 | `craft.{recipe}` | ＋新增 | **V2** | 1.3 |
| `manual_learned`/`proficiency_ge` | 功法系统 | `manual.*` | ＋新增 | **V2** | 1.4 |
| `meditation_duration_ge` | 打坐(区间结算) | `meditate.sec` | ＋新增 | **V2** | 1.5 |
| `cultivation_ge` | 修为(批量结算) | `cult.value` | ＋新增 | **V2** | 1.5/1.7 |
| `realm_ge`/`realm_layer_ge` | 境界系统 | `realm.*` | ＋新增 | **V2** | 1.7 |
| `breakthrough_result` | 渡劫结算 | `breakthrough.{id}` | ＋新增 | **V2** | 1.8 |
| `bounty_completed`/`turned_in` | 委托系统 | `bounty.*` | ＋新增 | **V2** | 1.6 |
| `sect_contribution_ge`/`reputation_ge` | 宗门系统 | `sect.*` | ＋新增 | **V5** | 宗门线 |
| 组合子 `all/any/not` | RuleTree 层 | — | ★直搬 | **V0** | 复合条件 |

> 事件只带稳定ID（monsterId/itemId/recipeId/npcId/dialogueNodeId/sceneId/realmId），**不用中文显示名做逻辑条件**。＋类落地成本低：系统本来要做，只需完成点多 `se.emit` 一个事件 + 照 `KillCount.ts` 范式写一个 PredSpec（resolveDeps/eval/progress/renderer 四件套）。

### 4.3 运行时模型：定义层 / 步骤层 / 实例层分开（小G核心洞察）

旧框架"一任务=一条件树"，无显式步骤——但 1.1–1.8 本质是**有序教学**，不能把所有目标平铺进一棵 `all` 树（否则玩家可跳过教学顺序）。建议：

```
QuestDef（配置，不随玩家变）
  └─ StepDef[]（阶段：stepId/enterTrigger/showCond/objectives/onEnter/onProgress/onComplete/nextStep/fail-timeout）
QuestInstance（玩家运行时）
  ├─ status / currentStep / progressData / claimed / instanceId / startedAt·updatedAt / baseline
```

例：1.3 不是单个"炼丹完成"，而是 到灵植园→与药童对话→采集→得材料→找周丹师→炼3颗→服1颗→调息 的步骤链。

### 4.4 任务配置字段（在旧字段上扩充）

`triggerType`(自动/NPC/区域/前置/境界/世界事件/任务栏) · `scope`(个人/房间/全服唯一) · `steps[]` · `objectiveMode`(全部/任一/顺序/并行) · `deliveryRule`(交付NPC+对话节点) · `scene/instanceRule`(计数作用域) · `progressMode`(累计/持有量/事件次数/当前状态/持续时间) · `resetRule`(不重置/日/周/活动/境界阶段) · `rewardPolicy`(入包/邮件补发/失败重试/唯一) · `unlockFlags`(背包格/技能/配方/任务栏/区域/突破入口) · `sequenceId/chapterId` · `version`(迁移兼容)。

### 4.5 与修仙项目资料结合

- **作用域分层**：主线/突破材料/独有BOSS/首次筑基走个人任务实例；普通刷怪/掉落/部分悬赏可用房间事件；世界播报是表现层，"播报成功"不算任务事实。
- **接修仙真实事实**：修为监听 `cultivation.value_changed`/批量结算（非传奇经验）；境界只读 `realm/realm_sub`（境界系统权威变更，任务不自改境界）；丹药监听"使用/炼制/效果结算"非仅背包数量；打坐按区间/离线按时间结算，不逐秒发；突破是"修为满+材料齐+突破事件"组合；灵植/妖丹/魔核/突破主药按物品ID+来源标签区分，防同名误计。
- **世界观口径冲突（需策划裁决，勿由代码擅自统一）**：世界观锚点"上线即炼气一层外门弟子、跳过入门任务链" vs 小C流程从"加入宗门"起；世界观"长老不排他/五堂开放" vs 截图单条长老主线；1.8"突破秘境/心魔秘境"；炼气九层/圆满、孙执事/孙管事、灵植园/灵植圃 需入命名字典定稿。

---

## 五、版本路线与《工作任务拆分表》缺口（合并自小C）

### 5.1 任务系统按版本落地节奏

| 版本 | 任务系统交付 | 依据 |
|---|---|---|
| **V0** | 引擎骨架移植（RuleTree三态+双层状态机+Anchor+rev快照+配置加载）+ 最小谓词集 + GM测试任务闭环 | 底座 A6/A8；见第六部分 |
| V1 | 新手30秒引导 + 击杀/拾取/对话/到达/使用监听 + StepRuntime + 任务追踪UI | H6.1、AE-001/002、1.1–1.2 |
| V2 | 打坐/修为/境界/炼丹/突破监听 + 首次突破任务链(1.3–1.8全线) + 委托雏形 | H1、AE-003、1.3–1.8 |
| V5 | 师门/宗门/日常/周常/悬赏刷新 + 贡献声望监听 + 长老任务链 | H2–H4、I4/I5、AE-004/005/006 |

### 5.2 《工作任务拆分表》缺口（重要，需补排期）

250 条工作项里任务相关**只有 6 条且全挂 AE 引导名下**：AE-001/002(V1新手引导+箭头)、AE-003(V2首次突破引导)、AE-004/005/006(V5师门/日常/周常)。全表检索 `RuleTree/条件树/状态机/事件总线/任务面板/任务栏/任务追踪` **均无**——**任务引擎内核没有任何工作项**，而它恰是旧项目已实现、设计文档1.1–1.8与底座A8/H1.2都要用的地基。建议补：

- `QUEST-CORE-01`（V0，核心层）移植 QuestSystem 内核：RuleTree三态引擎 + Anchor + 双层状态机 + rev增量快照。
- `QUEST-CORE-02`（V0，核心层）谓词最小集(kill/completed_quest/player_level[+collect])+`_init`注册，并**修 bug⑤④**。
- `QUEST-UI-01`（V1，UI层）任务追踪HUD + 任务面板 + NPC头顶气泡(接G3)。
- `QUEST-FLOW-01`（V1–V2，策划+核心）StepRuntime + 新手1.1–1.8全链配置 + 委托接取交付闭环。
- 口径对齐：AE-005"每天5个日常" vs 1.6"悬赏每日刷新" vs 底座"悬赏低/中/高阶"——日常与悬赏是否同一套需定。

---

## 六、V0 任务系统切片定义（本次核心结论）

> 你的目标是"整体规划 + 明确 V0 做什么，既顾当下也顾全盘"。以下是我从实现角度的判定。

### 6.1 V0 做什么（做减法：只搭地基，不做内容）

底座里 V0=内部技术验收版（进房/建角/打怪/掉物/存档），任务的新手内容其实从 V1(AE) 才开始。所以**任务系统的 V0 不是做新手线，而是把旧项目的引擎骨架移植通、跑通一条 GM 测试任务的全闭环**。具体交付：

1. **移植引擎骨架**（QUEST-CORE-01）：`RuleTreeEngine`(三态 compile/dep/flush) + `TaskServiceImpl`(双层状态机+dep增量刷新+rev快照) + `AnchorManager`(事实层) + `QuestDefRepo`+`ImportQuestData`(配置加载) + `Guard` + `QuestRewardHandler` 骨架 + 事件总线 `se` 接线。
2. **最小谓词集**（QUEST-CORE-02）：只上**旧代码已完整、可直搬**的三个——`kill_count_ge`、`completed_quest`、`player_level_ge`（可选加 `collect_items`）。这四个足以证明"事件→锚点→条件树→状态机→奖励→存档→重连"整条管线打通。
3. **一条 GM 测试任务链**（验收）：GM 注入 2 条任务：任务A『杀N只测试怪』(kill_count_ge)→完成→领奖(经验/灵石)→触发 `completed_quest` 解锁任务B→任务B『等级达标』(player_level_ge)→完成。**中途存档→断线→重连→状态与进度正确恢复**。对齐底座 AP-001 冒烟测试。

### 6.2 V0 不做什么（明确排除，防蔓延）

不做新手线1.1–1.8内容 · 不做 StepRuntime（V1再上）· 不做任务面板自绘UI（V0用最简文本/multiboard或复用旧渲染）· 不做炼丹/打坐/境界/突破/委托/宗门谓词 · 不修 FindNPC/Recycle 桩（V0无对应内容）· 不做每日/周常刷新内容（但周期时钟接口保留）。

### 6.3 V0 前必须修的坑（因为它们会固化进存档/配置）

- **bug⑤ 快照键统一**（`task_%d` vs 数字键）：动存档格式，V0 一旦落盘就难改，**必修**。
- **bug④ 周常分类**（category=DAILY）：动配置与筛选口径，**必修**。
- bug⑦ 清 `print_r` 调试输出（顺手）。
- bug⑥ 击杀监听拆耦合 + flush 合批：V0 就把"监听器单一职责 + flush 每 tick 合批"定成范式，别把 VIP/抽奖那种耦合带进来。

### 6.4 为不返工，V0 必须冻结的 5 个全盘约定（顾全盘的关键）

即便 V0 内容极少，这 5 项要在 V0 就定死，否则 V1–V2 会被迫改存档/改接口/返工：

1. **存档 schema 预留**：`steps/currentStep`、`version`、`scope`、`instanceId` 字段现在就写进快照结构（V0 可空置），V1 上 StepRuntime 时不用迁移旧档。
2. **事件命名枚举冻结**：现在就定一套稳定的领域事件枚举（点分命名 `combat.unit_killed`/`cultivation.value_changed`…），V0 只 emit 3–4 个，但后续系统都往同一总线 emit，命名不再变。
3. **锚点键约定冻结**：`domain.key.{id}` 格式 + Persistent/Runtime 生命周期 + baseline 基线约定，V0 定死。
4. **双层状态模型保留**：生命周期(存档) + 视图态(派生) 从 V0 就是两层，别为省事合成一层。
5. **配置表契约冻结**：QuestDef/PredDef 表结构按"含 steps 的超集"设计，V0 只填少数列，但列定义不再变（对齐底座 U3 任务表 + 融合版P17）。

### 6.5 V0 验收标准（可勾选）

- [ ] 引擎骨架编译通过，`se` 事件总线可注册/注销，无重复订阅。
- [ ] GM 可注入任务；kill_count_ge / completed_quest / player_level_ge 三谓词事实累计正确。
- [ ] 状态机迁移正确：NOT_ACCEPTED→ACCEPTED→COMPLETABLE→COMPLETED；视图态派生正确。
- [ ] 领奖幂等：重复领取不重复发奖；rev 增量快照上报正确。
- [ ] 存档→断线→重连：status/进度/completed_quest 解锁链正确恢复（重点验 bug⑤ 已修）。
- [ ] 5 个冻结约定落到代码/表结构（存档字段、事件枚举、锚点格式、双层状态、配置契约）。
- [ ] KillCount 监听单一职责、flush 合批，无 print_r。

---

## 附：本基线之后可深入的方向（供选）

A. **StepRuntime 多步骤模型详设**（把 1.1–1.8 拆成显式步骤机 + 步骤存档/恢复）——V1 落地关键。
B. **监听事件与谓词目录定稿**（事件枚举 + 谓词参数 + depKey + 优先级，一张可直接给程序的配置契约表）。
C. **旧项目→修仙 逐文件移植工单**（每文件标 直搬/改语义/重写 + bug①–⑩ 修复方案）。
D. **世界观口径裁决**（上线即炼气一层 vs 加入宗门、突破/心魔秘境等，先裁决再配置）。

> 本文已确立"以旧 QuestSystem 为底座 + V0 只搭骨架 + 冻结5约定"的整体规划。建议先按第六部分锁定 V0，再从 A/B 深入。
