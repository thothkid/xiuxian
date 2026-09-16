# 配置表 ID 首位分配总览

## 全项目 ID 首位分配
| 首位 | 指向 | 表 |
|:--:|---|---|
| 1 | 物品 | `W物品表 / item_config` |
| 3 | 丹方丹效 | `D丹方丹效表 / alchemy_recipe_config` |
| 3 | 灵植 | `L灵植表 / spirit_plant_config` |
| 4 | 技能 | `J技能BUFF表 / skill_config` |
| 5 | 装备 | `Z装备 / equip_config` |
| 6 | BUFF | `J技能BUFF表 / buff_config` |
| 7 | 奇珍 | `Q奇珍录 / 收录` |
| 8 | 词条 | `Z装备 / ConfigCitiao` |

装备形态的奇珍由 `unlock_id` 指向 `equip_config.id`。`equip_config` 现有的 `illustrated_id` 列（现存每行实配 `99`）保持原样，奇珍录不使用该列。

装备词条表 `ConfigCitiao` 的主键 `hidden_affix` 现为 1—96 的整数，迁移到 8 开头的 8 位段。
