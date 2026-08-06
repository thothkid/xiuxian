# 修仙 ORPG · 任务系统框架分析与建议

> 编制说明：本文回应四项要求——(1) 拆解新手任务清单与功能点；(2) 整理 ORPG 任务系统一般性框架（WAR3 视角，不绑定本项目）；(3) 分析上一项目 `legendary-map` 任务系统实现；(4) 综合给出修仙新项目的任务框架建议（含监听类型）。
>
> 数据来源：小C《新手任务流程_截图逐字提取》、《新手任务系统设计文档》、《WC3修仙ORPG_开发底座 v4.1》、《世界观_最表层-开发锚点》、上一项目遗留《老表格/任务配置表1.01.xlsx》。
>
> **重要状态**：第三部分"上一项目代码分析"目前只完成了**配置层**分析（依据已随项目留存的老任务配置表）。`E:\works\legendary-map` 源码目录尚未连接到本会话，**代码级实现（事件派发机制、状态机代码、逐字段存档、UI 实现）待该目录连接后补齐**。连接后我会追加第三部分代码分析并据此微调第四部分。

---

## 第一部分：新手任务清单与功能点拆解

新手主线共 **8 个任务（1.1–1.8）**，从加入宗门到首次筑基，构成"通天大道第一章"。每个任务原则上只引入一个主系统。

### 1.1 任务清单总表

| ID | 任务名 | 任务类型 | 关键 NPC | 主要场景 | 核心教学系统 | 结束产出 |
|---|---|---|---|---|---|---|
| 1.1 | 加入宗门 | 主线/新手 | 莫黎长老 | 山门牌坊、大殿广场 | 移动、镜头、NPC 交互、任务追踪 | 找到陆青 |
| 1.2 | 试炼幻境·首次击杀 | 主线/新手 | 陆青 | 山门广场、试炼幻境(副本) | 背包、战斗、拾取、装备、药品 | 得战利品并转往灵植园 |
| 1.3 | 丹道初窥·首次炼丹 | 主线/新手 | 药童、周文扬 | 灵植园、炼丹房 | 采集、炼丹、丹药/丹毒、打坐调息 | 炼并服用引气丹 |
| 1.4 | 长老授业·传授功法 | 主线/新手 | 莫黎长老 | 功法阁、试炼幻境 | 秘籍、功法激活、技能、熟练度 | 学会基础功法 |
| 1.5 | 再遇陆青·修炼基础 | 主线/新手 | 陆青 | 大殿广场水池旁 | 打坐、修为、离线修炼、装扮 | 获入门服饰，开放勤务堂 |
| 1.6 | 历练委托·首次委托 | 主线/新手 | 孙玲 | 勤务堂 | 任务分类、任务面板、悬赏接取交付 | 完成首个悬赏 |
| 1.7 | 筑基之路·收集突破材料 | 主线/世界(突破) | 孙玲 | 全区域、勤务堂 | 突破条件、材料追踪、BOSS 掉落 | 集齐筑基材料 |
| 1.8 | 破境筑基·首次大突破 | 主线/新手 | 莫黎长老、陆青、周文扬 | 渡劫台、心魔秘境 | 心魔战、雷劫、境界突破 | 晋升筑基，第一章终 |

### 1.2 功能点（任务需要驱动/监听的"原子动作"）

把 8 个任务铺开，任务系统真正需要支撑的功能动词如下，按类归并（这是后面设计监听类型的依据）：

**对话/演出类**：多角色对话树、锁定/解锁移动镜头、条件对白（任务前/中/后不同）、轻动作（转身、指向、打量、搭脉）。出现在全部 8 个任务。

**位移/到达类**：移动教学、寻路导航、区域到达判定、场景↔副本传送与返回点、NPC 头顶标记、找到指定 NPC。出现在 1.1、1.4、1.5、1.6、1.8。

**战斗/击杀类**：选敌普攻技能、击杀计数（1.2 杀 4 只教学怪、1.6 悬赏杀怪、1.7 击杀魔化 BOSS）、心魔镜像战（1.8）。

**掉落/拾取类**：自动拾取、品质光柱、首次掉落飘字与音效、掉落归属。1.2、1.7。

**背包/物品类**：背包解锁（储物袋）、穿戴装备、服用药品/丹药、使用秘籍激活功法、关键任务道具保护。1.2、1.3、1.4。

**采集/生产类**：灵植采集（1.3 凝露草、1.7 灵草）、炼丹炉炼丹产出引气丹（1.3）。

**修炼/成长类**：服丹涨修为(+50)、打坐按秒结算(+5/秒×30秒)、离线修炼结算、修为/等级阈值、境界(炼气七重→九层圆满→筑基)、功法熟练度。1.3、1.4、1.5、1.7、1.8。

**任务/委托类**：任务面板、三类任务分类教学、悬赏接取—追踪—交付—奖励闭环、每日刷新、宗门贡献结算。1.6、1.7。

**突破/仪式类**：突破面板入口、突破材料条件校验与扣除、心魔秘境副本、雷劫倒计时结算（首次保底 100%）、全屏金光、世界播报、章节结束大字。1.8。

**通用支撑（贯穿）**：任务奖励幂等发放、背包满补发、关键节点实时存档、断线重连状态恢复、防重复触发/防重复领奖、教学埋点。

> 归纳：新手线要求任务系统能"监听"的事件家族＝ **对话完成 / 到达区域·找到NPC / 击杀计数 / 拾取·收集 / 使用道具·穿戴 / 采集 / 炼制 / 打坐时长 / 修为·等级·境界阈值 / 突破成功 / 委托轮次完成**。这份清单直接决定第四部分的监听类型设计。

---

## 第二部分：ORPG 任务系统一般性框架（WAR3 视角，通用）

抛开本项目，一个成熟 ORPG 的任务系统通常由以下分层组成。每层后面标注"WAR3 一般怎么实现 / 引擎能不能做"。

### 2.1 分层框架

**① 数据/配置层**——任务不写死在代码里，而是读表。通用做法是拆几张表：任务定义表（quest def）、条件/谓词表（predicate）、对话表（dialogue）、目标步骤表（objective/step）、奖励表（reward）。WAR3 侧：可用地图内 gameplay constants、自定义物编字段承载，但主流 ORPG 是把 CSV/表结构导入成初始化脚本，或（本项目情形）由服务器下发配置。

**② 定义/结构层**——单条任务的字段：ID/名称、类型（主线/支线/日常/周常/世界/宗门/悬赏）、前置、触发方式、接取/交付 NPC、地点、可见目标、子目标、玩家操作、对白集、奖励、可重复次数（每日/总）、异常规则。

**③ 状态机层**——每个玩家 × 每个任务持有一个状态：`锁定 → 可接取 → 进行中 → 可交付 → 已完成`（旁支：`已放弃`、`冷却中`、`失败`）。状态迁移必须幂等、可存档、可断线恢复。WAR3 侧：per-player 用 hashtable / 数组 / 结构体存状态。

**④ 事件监听层（核心）**——任务进度靠"游戏里发生的事"推进。ORPG 通用做法是建一个**事件总线/派发器（EventBus）**：各系统（战斗、掉落、背包、修炼…）发出事件，任务管理器订阅并路由到"当前进行中且关心该事件"的任务。常见监听事件族：击杀、拾取/收集、到达区域、与 NPC 对话、升级/属性达标、使用/装备物品、制造/采集、交易/购买、时间到达、任务完成（链式前置）。
  - WAR3 原生 ECA 事件可直接用的：单位死亡 `EVENT_PLAYER_UNIT_DEATH`（击杀）、拾取物品 `PICKUP_ITEM`、进入区域 `EnterRectRegion`、英雄升级 `HERO_LEVEL`、对话按钮点击 `DialogButtonClick`、单位被下达命令等。
  - WAR3 原生事件**覆盖不全**（如"炼丹成功""打坐满 30 秒""修为达标"没有原生事件），因此 ORPG 普遍**自建事件层**：这些系统在自己逻辑里手动 `触发/广播` 一个自定义事件，任务系统订阅之。这是 WAR3 做任务的关键工程点。

**⑤ 条件判定层（RuleTree）**——接取条件、完成条件、显示条件都不是单一判断，而是可组合的布尔树：叶子是"谓词（predicate）"（如击杀数≥N、等级≥L），中间节点是 `AND/OR/NOT` 组合子。这样"等级 5–10 且已完成前置且未穿戴 X"这类复合条件可配置化。WAR3 侧完全可做：谓词就是返回 bool 的函数，组合子递归求值。

**⑥ 目标/进度层**——把完成条件里的可计数项（杀怪 3/5、收集 2/4）实时累加并驱动 UI。需要防回溯或支持回溯（玩家提前持有/提前击杀是否计入）。

**⑦ 触发/接取层**——任务如何开始：出生自动、NPC 对话、进入区域、系统事件（如"修为达炼气圆满自动刷新突破任务"）。

**⑧ 表现层**——任务追踪 HUD、NPC 头顶问号/感叹号标记、寻路导航/目标距离、对话演出、飘字/奖励弹窗、世界播报。WAR3 侧：原生有 F9 任务日志（`CreateQuest` 系列）和 multiboard、text tag、浮动文字、对话框（dialog）；但现代 ORPG 多用自定义 UI 框架（Frame/FDF）自绘任务面板与 NPC 标记。

**⑨ 奖励/解锁层**——发奖（经验/货币/道具/称号/功能解锁/后续任务解锁），必须幂等、背包满可补发（邮件/临时背包）。

**⑩ 存档层**——任务状态、进度计数、每日已完成次数、冷却时间戳都要落盘。WAR3 侧：原生存档码有大小上限，字段要压缩；本项目走服务器存档更宽松。

**⑪ 异常层**——断线重连、场景切换后状态恢复、重复触发保护、放弃/重接、关键道具误消耗补救、失败重试不重复扣材料。

### 2.2 WAR3 引擎能力与约束速查（针对任务系统）

| 能力 | WAR3 一般实现 | 约束/坑 |
|---|---|---|
| 事件监听 | 原生 ECA 事件 + 自建 EventBus 广播自定义事件 | 原生事件族有限，非战斗类事件几乎都要系统自己发；高频 timer 要控数量（性能） |
| 条件树 | 谓词函数 + AND/OR/NOT 递归求值（对应本项目 A8 RuleTree） | 深树/高频求值注意开销，建议只在相关事件到来时求值，别轮询 |
| 状态存储 | hashtable / 结构体 / 数组，按玩家 slot | 单位/句柄泄漏、hashtable 清理 |
| 接取触发 | 区域进入触发器、NPC 单位点击/对话、出生初始化 | NPC "点击"常用选中或范围触发模拟 |
| 目标计数 | 全局/按玩家计数器，事件里自增 | 组队/多人时归属判定 |
| 任务 UI | 原生 Quest 日志(F9)、multiboard、text tag；或自绘 Frame UI | 原生 UI 朴素，自绘 UI 工作量大但体验好 |
| 导航寻路 | 原生自动寻路 + 目标点箭头/闪烁、区域高亮 | 折返、卡死点需地编配合 |
| 对话演出 | dialog 框 / 自绘对话框 + timer 分句 + 镜头锁定 | 需处理跳过、连点、重复交互 |
| 存档 | 原生存档码（有上限）或服务器存档 | 字段压缩、version 迁移、离线可信度校验 |

> 一句话：WAR3 做任务系统，**难点不在"能不能"，而在"原生事件不够，得自己搭一个事件总线 + 条件树 + 状态机 + 自绘 UI"**。这几件恰恰是可以跨项目复用的基础设施。

---

## 第三部分：上一项目 `legendary-map` 任务系统实现分析（代码级）

> 源码已连接。上一项目用 **TypeScript 编写、经 TSTL 编译为 Lua** 运行在 WC3 上，任务系统位于 `src/map/QuestSystem/`（约 45 个文件，分 Base/CustomDefinition/Guards/Impl/Import/Query/Rendenerer/View 八个子目录），配置位于 `src/xlsx/ConfigQuestDef|Bra|PredDef.ts`，服务器接口在 `src/map/v2/logic/network/api/QuestAPI.ts`。这是一套**成熟的、反应式（reactive）配置驱动任务引擎**，远超一般 WC3 任务系统。以下为实读代码后的架构还原。

### 3.1 目录与模块地图

| 模块 | 关键文件 | 职责 |
|---|---|---|
| 数据契约 | `Base/QuestDefinition.ts`、`QuestTypes.ts`、`QuestSnapshot.ts`、`QuestReward.ts`、`Period.ts` | 任务定义、状态枚举、快照、奖励、周期时钟的类型 |
| 服务核心 | `Impl/QuestServiceImpl.ts`（约 840 行，全系统心脏） | 状态机、增量刷新、快照/上报、玩家动作(接取/交付) |
| 条件树桥 | `Base/RuleTreeBridge.ts` + `Impl/RuleTreeBridgeImpl.ts` + `map/RuleTree/RuleTreeUtil` | 编译/求值三态条件树（compile/submitDepChanges/flush） |
| 谓词库 | `CustomDefinition/*`（KillCount/CollectItems/CompletedQuest/PlayerLevel/FindNPC/EnhanceEquipment/RecycleEquipment/EquipTargetGradeEquipment）+ `_init.ts` | 每个谓词＝监听器＋判定＋进度＋渲染 四合一 |
| 守卫 | `Guards/QuestGuardImpl.ts` | canView/canAccept/canClaim 权限判定 |
| 基线查询 | `Query/BaseLineQuery.ts` | 进度从"接取时刻"起算（解决回溯计数） |
| 进度/渲染 | `Rendenerer/*`、`View/*` | 进度视图构建、diff、快照写回、UI 行渲染 |
| 导入 | `Import/ImportQuestData.ts` | 把 xlsx 配置 → 运行时 QuestDef |
| 服务器 | `QuestAPI.ts` | `/task/create`、`/task/setprogress`、`/task/finish` |

### 3.2 核心架构：Anchor（事实锚点）+ RuleTree（三态条件树）+ 增量刷新

老项目的精髓是一条**"事件 → 锚点 → 依赖 → 只重算受影响任务"**的反应式链路，而不是每帧轮询：

```
业务事件(se.emit)  ──▶  谓词的 CreateTrigger 订阅(se.on)
    例:"单位-击杀单位"          │  更新 AnchorManager（per-player 事实库）
                               │    anchor.NumberChanged("kill.monster.X", +1, "Persistent")
                               ▼
              service.submitDepChanges(["kill.monster.X"]) → service.flush()
                               │  QuestService 用 depToTasks 索引：depKey → 关心它的任务集合
                               ▼
              只对受影响任务 flush 其 show/accept/complete 三棵条件树（三态求值）
                               ▼
              viewState 重算 → 变化则 se.emit("玩家-任务视图更新"/"完成任务"...)
```

关键点：

**① 全局事件总线 `se`**（signal emitter）。业务系统 `se.emit("单位-击杀单位"/"单位-升级成功"/"玩家-进入游戏"...)`；任务系统既是消费者（谓词 `se.on` 订阅），也是生产者（`se.emit("玩家-接取任务/完成任务/结束任务/任务视图更新/任务状态变化/获得任务奖励")`，契约见 `QuestEvents.d.ts`）。这就是第二部分说的"自建 EventBus"，老项目已经有了。

**② AnchorManager = per-player 事实库**。谓词不直接读游戏状态，而读"锚点"：击杀累加 `NumberChanged(key,+1,"Persistent")`、等级用 `NumberCover(key,value,"Runtime")`（覆盖式）。锚点分 **Persistent（存档）/ Runtime（登录重算）** 两种生命周期——这是把"进度事实"与"业务系统"解耦的中间层。

**③ RuleTree 是三态（Tri-state）**：`TRUE / FALSE / UNKNOWN`。事实缺失时返回 UNKNOWN 而非 FALSE（`unknownIfMissingNumber`），避免"数据没到位就误判未完成"。比老配置表的二值条件更稳健。每棵树带 `depIndex`，`submitDepChanges` 打脏、`flush` 只重算脏节点——**增量求值**。

**④ 谓词 PredSpec 四合一**（以 `KillCount.ts` 为范本）：`resolveDeps`(声明监听哪些 depKey) + `eval`(query,args)→三态 + `onClaim`(交付副作用，如 `CollectItems` 扣道具) + 配套的 `QuestProgressReg`(进度条 cur/target) 与 `QuestRenderer`(UI 文案"击杀X 3/5")。加一种新监听＝加一个这样的文件并在 `_init.ts` 注册。

**⑤ BaseLineQuery（回溯计数解法）**：接取任务时 `RecordBaseLine` 把当前锚点值记为基线，之后进度＝当前值−基线。所以"接取前已击杀的怪不计入本任务"。这正好回答了我上一版报告里提的开放问题（提前击杀是否计入）——老项目选择**不计入**，从接取时刻起算。

### 3.3 状态机：双层状态（生命周期 + 视图态）

- **生命周期状态（权威、存档）** `TaskLifecycleStatus`：`NOT_ACCEPTED / ACCEPTED / COMPLETED`。
- **视图态（派生、不存档）** `TaskViewState`：`HIDDEN / VISIBLE / ACCEPTABLE / ACTIVE / COMPLETABLE / COMPLETED`，由 `computeViewState(status, showTri, acceptTri, completeTri)` 推导（见 `QuestServiceImpl` 780 行起）：show≠TRUE→HIDDEN；未接且 accept=TRUE→ACCEPTABLE 否则 VISIBLE；已接且 complete=TRUE→COMPLETABLE 否则 ACTIVE。
- **任务分类** `TaskCategory`：`MAIN / SIDE / DAILY / EVENT`。**主线单活约束**已实现：接主线时遍历其他主线，若有 ACCEPTED 则拒绝（"当前已有主线任务进行中"）。
- **重复策略** `RepeatPolicy`：`ONCE`（主线）/ `REPEATABLE{maxTotal}`（支线可重复带上限）/ `PERIODIC{DAILY|WEEKLY, maxCompletePerPeriod}`（日常/周常）。`applyRolloverIfNeeded` 用 `dailyKeySec/weeklyKeySec` 检测跨周期并重置 `completedInPeriod`/status。

玩家动作三入口：`tryView / tryAccept / tryClaim`，每个先过 `guard`，再改 snapshot，再 `refreshTaskDerivedState`，最后 `se.emit` + 调服务器 API。交付 `tryClaim` 会：跑谓词 `onClaim` 副作用 → `applyTaskCompletion` → 重置三条 baseline → 发奖 `QuestRewardHandler.grantRewards` → `se.emit("玩家-结束任务")` → 全量 `flush()`（触发后续支线解锁）。

### 3.4 存档与服务器同步

- **快照 + rev 增量**：每任务一个 `TaskProgressSnapshot`（status/claimed/completedTotal/completedInPeriod/periodKeySec/progressData/三条 baseline/rev）。`playerRev` 单调递增，`getDeltaSnapshot` 只回传 `dirty` 任务，`clearDeltaFlags` 推进 baseRev——标准的增量同步。
- **服务器权威**：`tryAccept` 调 `/task/create` 拿到服务器 `InstanceID(tid)`；进度变化（kill/collect）`/task/setprogress` 上报；交付 `/task/finish`。客户端算进度、服务器落权威账。
- **快照恢复**：`loadFromSnapshot` 以 `defRepo` 为准重建运行时（服务器可能不下发全部任务），`completed_quest.*` 这类"绝对状态"强制基线归零。

### 3.5 谓词/监听目录（代码实读，8 个已实现 + 组合子）

| PredKey | 监听事件源(se.on) | 锚点 depKey | 判定 | 状态 |
|---|---|---|---|---|
| `kill_count_ge` | `单位-击杀单位` | `kill.monster.{id}`(Persistent) | 累计击杀≥N | ✅ 完整 |
| `player_level_ge` / `_lt` | `单位-升级成功`、`玩家-进入游戏` | `player.level`(Runtime,覆盖) | 等级≥/< | ✅ 完整 |
| `collect_items` | 背包变化 | `collect_items.{id}` | 持有≥N，`onClaim` 扣除 | ✅ 完整 |
| `completed_quest` | 任务链内部 | `completed_quest.{id}` | 前置任务已完成 | ✅ 完整 |
| `enhance_equipment_count` | 强化事件 | 计数锚点 | 强化次数≥N | ✅ |
| `recycle_equipment_count` | 回收事件 | 计数锚点 | 回收次数≥N | ✅ |
| `equip_target_grade_equipment` | 装备变化 | 装备锚点 | 已穿 x 级 x 件 | ✅ |
| `find_target_npc` | **无**（`CreateTrigger` 空） | `find_target_npc` | **eval 恒 TRUE** | ⚠️ **桩/未完成**（进度 key 还误写成 `enhance_equipment_count`） |
| 组合子 `all/any/not` | — | — | AND/OR/NOT 递归（在 RuleTree 层） | ✅ |

### 3.6 可直接复用 vs 需重写（迁移到修仙）

**可几乎直搬（改语义即用）**：`RuleTree` 三态引擎（compile/dep/flush）、`QuestServiceImpl` 状态机与增量刷新、`QuestSnapshot`+rev 增量同步、`BaseLineQuery` 基线机制、`Guard` 权限层、`PredSpec` 四合一谓词范式、`QuestRewardHandler`、周期 rollover。这些是与"传奇/修仙"题材无关的纯基建。

**需重写/新增**：谓词库要按修仙扩充（见第四部分 4.3）——老的 8 个里 `kill/collect/level/completed_quest` 可直接复用，`enhance/recycle/equip` 换成修仙装备语义，`find_target_npc` **必须重做**（老项目是桩）。另需新增炼丹/打坐/境界/突破/采集/委托/宗门贡献等修仙谓词。UI 渲染层（`QuestRenderer`）要接修仙自绘面板。

### 3.7 值得警惕的几处（老项目的坑，新项目别继承）

1. **`find_target_npc` 是空实现**——"到达/找 NPC"这一新手最高频的监听在老项目根本没落地。修仙新手线 1.1/1.4/1.5/1.6/1.8 全靠它，**必须优先实现**（区域进入/NPC 交互事件 → 锚点）。
2. **每次击杀都同步 `submitDepChanges+flush`**，且 `KillCount` 的 trigger 里还塞了 VIP 计数、杀怪抽奖等**无关业务**——高刷怪频率下有性能与耦合风险。修仙建议：击杀监听只更新锚点，flush 合批（每 tick/每 0.2s 汇总一次），且监听器保持单一职责。
3. **`fullRecomputeAllTasks` 里残留 `print/print_r` 调试输出**——上线前需清理，WC3 大量 print 影响性能。
4. **锚点 Persistent 无上限累加**（如 `kill.monster.X` 永久累加）——长期存档字段膨胀，修仙需考虑封顶或按需清理。

---

## 第四部分：修仙新项目任务框架建议

综合 WAR3 实现现实（第二部分）、新手线暴露的系统需求（第一部分）、老项目已实现资产（第三部分）、以及《开发底座》既有规划（H 任务引导体系、A8 RuleTree、AE 任务引导系统、U3 配置表含"任务表"），给出如下建议。

### 4.1 总原则

1. **直接移植老项目 `QuestSystem/` 的反应式内核**，不重造轮子。经代码确认，老项目的 RuleTree 三态引擎、`QuestServiceImpl` 状态机、Anchor 事实库、BaseLineQuery、Guard、PredSpec 谓词范式都是与题材无关的纯基建（第三部分 3.6），可几乎直搬，只换谓词语义。这也正是《开发底座》`A8 RuleTree条件树`/`H1.2` 的既定方向。
2. **复用老项目已有的事件总线 `se`（EventBus）作为任务系统地基**。它已同时服务任务的订阅与广播；修仙的炼丹/打坐/突破/采集无 WAR3 原生事件，全靠各系统 `se.emit`。这条总线也应服务图鉴(L4)、成就、埋点、世界播报(G11)——公共基建，V0 就要搭。
3. **任务系统只订阅、不侵入**：沿用 Anchor 中间层——业务系统 emit 事件 → 谓词 trigger 更新锚点 → `submitDepChanges`。业务系统不需要知道任务存在。**但要修正老项目的坑**：监听器保持单一职责（别学 KillCount 塞 VIP/抽奖），`flush` 合批而非每次事件同步全刷。
4. **状态/进度/次数走服务器存档**（沿用老项目 rev 增量快照 + `/task/create|setprogress|finish`），关键节点实时保存 + 幂等发奖。

### 4.2 推荐分层架构（修仙版）

```
配置层    QuestDef 表 / PredDef 条件表 / Dialogue 对话表 / Objective 子目标表 / Reward 表
   │        （对齐 U3 配置表清单"任务"表 + 融合版P17；PredDef 直接沿用老项目并扩充）
状态机    锁定→可接→进行中→可交付→已完成 (+放弃/冷却/失败)  · per-player · 落服务器存档
   │
条件树    RuleTree(A8)：pred 叶子 + all/any/not 组合子（沿用老项目结构，递归求值）
   │
事件总线  EventBus：各系统广播 → QuestManager 订阅 → 路由到关心该事件的进行中任务
   ↑
业务系统  战斗/掉落/背包/修炼/炼丹/采集/委托/突破/宗门… 在关键节点 emit 事件
```

### 4.3 建议监听类型（核心交付，用户明确要的"监听类型"）

下表把第一部分的功能原子 + 老项目谓词，落成修仙新项目的监听事件目录。左侧是事件（业务系统广播），右侧是可用它做完成/接取条件的谓词。**★ = 老项目已有可直接复用；＋ = 修仙新增，需对应系统提供广播钩子。**

| 事件（EventBus 广播） | 触发来源系统 | 配套谓词(PredKey) | WAR3 事件源 | 用于新手任务 |
|---|---|---|---|---|
| ★ 击杀怪物 | 战斗/怪物 | `kill_count_ge`(怪ID/数量)、`＋kill_by_tag_ge`(按境界/魔化标签) | 原生 UNIT_DEATH + 归属判定 | 1.2 杀教学怪、1.6 悬赏、1.7 BOSS |
| ★ 拾取/收集道具 | 掉落/背包 | `collect_items`(itemID,数量)、拥有量≥ | 原生 PICKUP_ITEM + 背包变更 | 1.2、1.7 |
| ★ 到达区域/找到NPC | 场景/NPC | `find_target_npc`、`＋reach_region`(RectID) | 原生 EnterRect / 单位选中 | 1.1、1.4、1.5、1.6、1.8 |
| ＋ 对话节点完成 | 对话演出 | `＋dialogue_finished`(对话ID) | 自建（对话系统 emit） | 全部 8 个 |
| ＋ 使用/服用道具 | 背包/丹药 | `＋use_item`(丹ID)、`＋first_use`(首次) | 自建（物品使用 emit） | 1.3 服引气丹 |
| ★ 穿戴装备 | 装备 | `equip_target_grade_equipment`(品级,数量) | 自建（装备变更 emit） | 1.2 穿装、1.5 服饰 |
| ＋ 采集完成 | 灵植/采集 | `＋gather_count_ge`(材料,数量) | 自建（采集点 emit） | 1.3 凝露草、1.7 灵草 |
| ＋ 炼制完成 | 炼丹/炼器 | `＋craft_count_ge`(产物,数量)、`＋first_craft` | 自建（炼丹炉 emit） | 1.3 炼引气丹×3 |
| ＋ 打坐/修炼时长 | 修炼 | `＋meditate_seconds_ge`(秒)、修炼状态达成 | 自建（打坐按秒结算 emit） | 1.5 打坐 30 秒 |
| ★ 等级/修为达标 | 修炼/属性 | `player_level_ge/lt`、`＋cultivation_ge`(修为值) | 自建 + 原生 HERO_LEVEL | 1.5 升 1 级 |
| ＋ 境界达标 | 境界 | `＋realm_ge`(大境界)、`＋realm_layer_ge`(炼气9层/圆满) | 自建（境界系统 emit） | 1.7 炼气圆满触发突破 |
| ＋ 突破结算 | 突破 | `＋breakthrough_success`(目标境界) | 自建（渡劫结算 emit） | 1.8 筑基成功 |
| ＋ 委托轮次完成 | 委托 | `＋bounty_round_done`(轮次)、`＋turn_in`(交付) | 自建（委托系统 emit） | 1.6 首个悬赏 |
| ＋ 宗门贡献/声望达标 | 宗门 | `＋contribution_ge`、`＋reputation_ge` | 自建（宗门系统 emit） | 后续宗门任务线 |
| ★ 系统行为计数 | 各系统 | `enhance/recycle_equipment_count` 等 | 自建（行为 emit） | 支线/日常复用 |
| ★ 前置任务完成 | 任务系统内 | `completed_quest`(任务ID) | 任务链内部 | 全链 1.1→1.8 前置 |
| 组合子 | — | `all`(AND) / `any`(OR) / `not`(NOT) 递归引用 | RuleTree 求值 | 复合条件（如境界+材料+灵石同时满足） |

> 落地要点：★ 类中 `kill_count_ge / collect_items / player_level_ge·lt / completed_quest` 老项目代码可直搬（`CustomDefinition/*` 对应文件），`enhance/recycle/equip` 换修仙装备语义即可；`find_target_npc` 老项目是**桩**、必须重写。＋ 的修仙类（炼丹/打坐/境界/突破/采集/委托）是**新写的广播钩子**——这些系统本来就要做（V1–V2 范围），只需在完成点 `se.emit` 一个事件 + 写一个 PredSpec（照 `KillCount.ts` 范式：resolveDeps/eval/progress/renderer 四件套），边际成本低。

### 4.4 触发/接取方式（对齐新手线）

四类接取，均需支持：**出生自动**（1.1）、**NPC 对话接取**（1.2–1.6、1.8）、**区域进入触发**、**系统事件自动刷新**（1.7：修为达炼气圆满→委托面板自动刷突破任务）。系统事件自动刷新这一类，正好由 4.3 的 `realm_layer_ge` 事件驱动，体现事件总线的统一性。

### 4.5 状态机与存档字段建议

**直接采用老项目的双层状态模型**（已验证优于单层）：生命周期状态（权威、存档）`NOT_ACCEPTED / ACCEPTED / COMPLETED`，加派生视图态（不存档）`HIDDEN / VISIBLE / ACCEPTABLE / ACTIVE / COMPLETABLE / COMPLETED`，视图态由 `computeViewState(status, showTri, acceptTri, completeTri)` 推导。每玩家每任务存：`taskId, status, claimed, completedTotal, completedInPeriod, periodKeySec, 三条 baseline, progressData, rev`。对齐《开发底座》U4 存档字段与 A4/A5 存档系统，沿用 rev 增量快照，走服务器周期保存 + 关键节点强制保存（新手线每个任务完成即存）。

### 4.6 表现层建议

任务追踪 HUD + NPC 头顶问号/感叹号气泡（底座 G3 气泡系统已规划）+ 寻路导航（F6.1 自动寻路 + 目标箭头）+ 自绘对话框（锁镜头、可跳过、防连点）+ 飘字/奖励弹窗 + 世界播报（G11，用于 1.8 筑基播报）。新手线强绑**新手教学系统**（强引导遮罩、按钮高亮、单步放行、完成检测），教学步骤与任务子目标一一对应、不可跳过时锁死出口。

### 4.7 与版本路线对齐（落地节奏）

| 版本 | 任务系统需交付 | 依据 |
|---|---|---|
| V0 | EventBus 地基 + 任务状态机 + RuleTree 解释器（搬老项目）+ 配置表加载 | 底座 A8/A6 |
| V1 | 新手 30 秒引导 + 击杀/拾取/对话/到达监听 + 任务追踪 UI | H6.1、AE、1.1–1.2 |
| V2 | 打坐/修为/境界/炼丹/突破监听 + 首次突破任务链（1.3–1.8 全线）+ 委托雏形 | H1、1.3–1.8 |
| V5 | 师门/宗门/日常/周常/悬赏刷新 + 贡献声望监听 + 长老任务链 | H2–H4、I4/I5 |

### 4.8 待策划/程序确认

沿用《新手任务系统设计文档》第 9 节 12 项待确认（怪物 XXXX 命名、奖励数值、材料命名、悬赏轮次、首次筑基是否恒 100%、命名等），此外任务框架层需另确认：(1) ~~提前击杀是否回溯计入~~——老项目已有答案：BaseLineQuery 从接取时刻起算、**不回溯**，建议沿用；如新手线希望"提前击杀也算"需专门覆盖；(2) 突破材料扣除时机（建议点击突破时扣，而非孙玲确认时）；(3) 每日/周常重置的时间基准（服务器时区/节气，接入 `periodClock`）；(4) 事件总线 `se` 是否作为公共基建同时服务图鉴/成就/埋点（建议是）。

### 4.9 与《工作任务拆分表》的对照与缺口（重要）

已核对 250 条工作项的《WC3修仙ORPG_工作任务拆分表》。**任务相关工作项目前只有 6 条，且全部挂在 AE（引导）名下**：

| 编号 | 版本 | 内容 | 落点 |
|---|---|---|---|
| AE-001 | V1 | 新手 30 秒引导流程（靠近→攻击→拾取→吃丹→升级→"你变强了"） | 策划+UI |
| AE-002 | V1 | 引导箭头/高亮 | 美术+UI |
| AE-003 | V2 | 首次突破引导（修为满→打开突破面板→放材料→突破） | 策划+UI |
| AE-004 | V5 | 师门任务（每日杀怪/收集/跑腿→贡献+经验） | 策划+核心+UI |
| AE-005 | V5 | 日常任务（每日刷 5 个→活跃度→累计领奖） | 策划+核心+UI |
| AE-006 | V5 | 周常任务（每周刷 3 个→修为/材料） | 策划+核心+UI |

**缺口（需要补进拆分表）**：拆分表把"任务"理解成了**引导演出 + 日常/周常内容**，但**任务引擎内核没有任何工作项**——全表检索 `RuleTree / 条件树 / 状态机 / 事件总线 / 任务面板 / 任务栏 / 任务追踪` 均无。而这恰恰是：(a) 老项目 `QuestSystem/` 已实现、可移植的部分；(b) 新手设计文档 1.1–1.8 与《开发底座》A8/H1.2 明确要求的部分。等于"要用的地基没排期"。建议在拆分表 **V0/V1 增补引擎层/核心层工作项**：

- `QUEST-CORE-01`（V0，核心层）移植 legendary-map `QuestSystem` 内核：RuleTree 三态引擎 + Anchor 事实库 + 双层状态机 + rev 增量快照。
- `QUEST-CORE-02`（V0，核心层）谓词库最小集（kill/collect/level/completed_quest/reach_region/find_npc）+ `_init` 注册，其中 `find_target_npc` **重写**（老项目为桩）。
- `QUEST-UI-01`（V1，UI 层）任务追踪 HUD + 任务面板（接取/进行中/可交付分页）+ NPC 头顶气泡（接 G3）。
- `QUEST-FLOW-01`（V2，策划+核心）新手主线 1.1–1.8 全链配置 + 委托接取交付闭环。
- 现有 AE-001/002/003/004/005/006 保留，作为"引导演出层"与上面引擎层协作，而非替代。

此外 AE-005"每天刷 5 个日常"与新手 1.6 孙玲口径"悬赏每日刷新"、《开发底座》悬赏分低/中/高阶三档需要对齐口径（日常 vs 悬赏是否同一套）。

---

## 附：本次可交付与后续

- 四部分均完整。第三部分已升级为**代码级分析**（已连接 `E:\works\legendary-map`，实读 `QuestSystem/` 约 20 个核心文件）：还原了 Anchor+RuleTree 三态引擎+双层状态机+rev 增量同步的完整架构，标出了可直搬模块、需重写模块与 4 处需规避的坑。第四部分据此把复用建议落到了具体模块与文件。
- 第 4.9 节新增了与《工作任务拆分表》的对照：指出任务引擎内核在拆分表中**无排期**，并给出建议补充的工作项。
- 建议下一步：若要把复用落到实处，可再让我出一份"legendary-map → 修仙 QuestSystem 移植清单"（逐文件标 直搬/改语义/重写 + 修仙谓词新增列表 + 改动点 diff 级说明）。
