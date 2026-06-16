# V0 怪物 AI 规则（融合版）

> 版本：vMerge-1.1 ｜ 2026-06-09 ｜ 对应交付清单 P06 ｜ 对应程序 S10
> 融合来源：小马《V0_怪物AI规则》(主体,六态机+完整 C++ 伪代码+combat_config AI 参数) + 小龙《V0 怪物AI》(状态图叙述并入)。
> 定位：V0 怪物 AI 行为规则。程序对着本文档写状态机。**六态机，所有怪物共用一套，参数可配。无巡逻/呼救/逃跑/技能/仇恨列表。**

---

## 一、AI 边界

| 维度 | V0 | 说明 |
|------|-----|------|
| 模型 | 六态有限状态机 | 待机/索敌/追击/攻击/脱战/归位 + 死亡 |
| 共用规则 | ✅ 所有怪物同一套 | 仅参数不同（aggro_range/atk_range/move_speed 等） |
| 巡逻/警戒/呼救/逃跑/技能/仇恨列表/寻路 | ❌ 全不做 | 怪物原地待机，发现即追，独立作战，死战到底，直线移动 |

设计哲学：一个最简单的「看到→追→打」循环，不做任何让程序员纠结的边界。

---

## 二、状态机

```
┌──────┐ 0.5s 检测 aggro 内敌对单位  ┌────────┐ 到 atk_range ┌──────┐
│ 待机 │──────────────────────────→│ 追击   │─────────────→│ 攻击 │
│ IDLE │←──────────── 目标死亡 ─────│ CHASE  │←── 出 atk ───│ATTACK│
└──────┘                           └───┬────┘              └──┬───┘
   ↑ 到出生点(满血)                     │ 出 chase_range×        │ 目标死亡
   │                                    │ 持续3s                 ↓
┌──────┐         0.3s 自动          ┌──────┐                  待机
│ 归位 │←─────────────────────────│ 脱战 │
│RETURN│                           │ FLEE │
└──────┘                           └──────┘
任意状态 hp≤0 → 死亡 DEAD → 死亡动画1s → 尸体5s → 淡出0.5s → 等重刷(S11)
```

### 状态转换速查

| 当前 | 条件 | 目标 | 优先级 |
|------|------|------|--------|
| 任意非DEAD | hp≤0 | DEAD | 🔴 最高(当帧) |
| IDLE | 索敌发现敌对 | CHASE | |
| CHASE | distance≤atk_range | ATTACK | |
| CHASE | 目标死亡 | IDLE | |
| CHASE | distance>chase_range 持续3s | FLEE | |
| ATTACK | distance>atk_range | CHASE | |
| ATTACK | 目标死亡 | IDLE | |
| FLEE | 0.3s 后 | RETURN | |
| RETURN | 到出生点≤30码 | IDLE(满血) | |
| RETURN | 受到攻击 | CHASE(锁攻击者) | |

---

## 三、各状态规则

- **IDLE**：原地待机播 stand 动画，每 0.5s 索敌检测（不每帧，省性能）。
- **索敌（逻辑态，不持久）**：扫 aggro_range 圆形（`dx²+dy²≤aggro²`），筛选 unit_type=PLAYER 且存活且敌对，**最近优先**锁定，立即转 CHASE。无仇恨值、不切目标、不检测隐身/遮挡。
- **CHASE**：以 move_speed 向目标当前坐标移动（每帧更新目标点）。退出：到 atk_range→攻击 / 目标死→IDLE / 出 chase_range 持续 3s→FLEE。
- **ATTACK**：停止移动，面向目标，调 `combat_attack(monster,target)`（P03 节奏：前摇0.3+命中+后摇0.4+冷却1.5）。退出检查在每次冷却完毕时做一次，不打断前后摇（目标死亡是硬中断）。
- **FLEE（=放弃追击,非逃跑）**：立即停追、清目标，0.3s 动画过渡后转 RETURN。可简化为立即跳 RETURN。
- **RETURN**：直线回出生点，移速 = move_speed×1.2（归位更快）。到出生点（30 码容差）→ IDLE 并**回满血**（硬规则，防玩家逐次磨血）。归位途中**受到攻击**（必须是受伤，非靠近）→ 锁攻击者转 CHASE。
- **DEAD**：见 P03 §3.3。停所有 AI Timer，从主循环移除，后续由 S11 接管。

---

## 四、AI 参数

每个怪物实例持有，值从 monster_config（P05）读：

| 参数 | 来源 | 小野狼 | 石傀儡 | 练气妖兽 |
|------|------|--------|--------|---------|
| `aggro_range` | P05 | 400 | 350 | 500 |
| `atk_range` | P05 | 128 | 150 | 128 |
| `move_speed` | P05 | 180 | 120 | 200 |
| `chase_range` | P05 | 600 | 525 | 750 |
| `atk_interval` | P05 atk_speed | 1.5 | 1.5 | 1.5 |
| `return_speed_mult` | 全局 | 1.2 | 1.2 | 1.2 |

> 说明：小马原稿用 `chase_max_range = aggro×1.5` 派生；本融合版按 G1/P05 裁决改为**显式读 P05 的 chase_range 字段**（值仍 = aggro×1.5，行为一致）。

### combat_config 中的 AI 全局参数

| 字段 | 建议值 | 说明 |
|------|--------|------|
| ai_search_interval | 0.5 | 索敌检测间隔(秒) |
| ai_flee_duration | 3.0 | 出追击范围持续多久才脱战(秒) |
| ai_return_arrival_radius | 30.0 | 归位到达判定半径(码) |
| ai_default_return_speed_mult | 1.2 | 默认归位移速倍率 |

---

## 五、程序实现（伪代码骨架）

```cpp
enum MonsterAIState { IDLE, CHASE, ATTACK, FLEE, RETURN, DEAD };

void MonsterAI_Update(MonsterAI* ai, float dt) {
    if (ai->state == DEAD) return;
    if (!IsAlive(ai->monster_id)) { EnterDead(ai); return; }
    switch (ai->state) {
        case IDLE:   UpdateIdle(ai, dt);   break;  // 累计0.5s→FindNearestPlayer(aggro)→有则EnterChase
        case CHASE:  UpdateChase(ai, dt);  break;  // 目标死→IDLE; ≤atk→ATTACK; >chase持续3s→FLEE; 否则MoveTo(目标)
        case ATTACK: UpdateAttack(ai, dt); break;  // 目标死→IDLE; >atk→CHASE; 否则委托战斗系统
        case FLEE:   UpdateFlee(ai, dt);   break;  // 0.3s后→RETURN
        case RETURN: UpdateReturn(ai, dt); break;  // 到出生点→IDLE+满血; MoveTo(spawn, speed×1.2)
    }
}

// 外部事件：归位途中被攻击
void OnMonsterDamaged(int mid, int attacker) {
    MonsterAI* ai = GetMonsterAI(mid);
    if (ai && ai->state == RETURN) { ai->target_id = attacker; ai->state = IDLE; ai->search_timer = 999; }
}
```

实现注意：①chase_range 创建时缓存不每帧算；出范围需持续 3s 才脱战，回范围内 flee_timer 立即清零。②距离用平方比较 `dx²+dy²≤range²` 免开方。③归位到达用 30 码容差，不用 `==`。④状态切换清残留（停移动/清计时器/更新目标）。⑤死亡检测在 Update 开头，高于所有状态逻辑。

---

## 六、融合说明

- 主体取小马（六态机 / 完整 C++ 伪代码 / OnMonsterDamaged 事件 / combat_config AI 参数 / 性能优化要点最完整）。
- 小龙版的状态图叙述清晰，并入开篇。小龙的状态名 ALERT 等价小马 SEARCH（逻辑态），统一用小马术语。
- 按 G1/P05 裁决：脱战范围从小马"派生 aggro×1.5"改为"显式读 P05 chase_range"（行为不变，更可配）。

*依据：总分析 G1、小马 P06 + 小龙 P06 全文、P05 参数。下一步：程序实现 S10 怪物 AI。*
