# 知识库脚本

> 依据：《龙马工作流》5.33 知识库·四区纪律。
> 状态：已修改、未执行。首次启用前先 `--dry-run`。

## 作用

`inject_headers.py` 是三区 Markdown 的知识库预处理器，不是同步器或上传器。除作为配置输入的 `项目索引.md` 外，它在每个 `##` / `###` 标题下写入：

```
〔出处：<当前文件名.md> · §<节名> ｜ 定位：<文档定位>——<使用边界>〕
```

出处由脚本使用当前文件名自动生成。文档定位和使用边界直接读取《项目索引》三区目录树中每个文件后的标记：

```
[定位：代码依据｜边界：写代码用]
[定位：非代码依据｜边界：排期用，不作代码依据]
```

定位只允许 `代码依据`、`非代码依据` 两种。代码不保存、不推断项目语义。

## 索引与文件范围

1. 只编辑一区 `E:\thoth\横向\WAR3修仙项目\项目索引.md`。
2. 二区、三区索引由正常 1→2→3 同步生成，不手工维护。
3. 注入前脚本比较三份索引 SHA-256；不一致即停止。
4. 脚本解析索引的“③区·团队共享”目录树。
5. 三区文档只允许：
   - 根目录7个文件；
   - `策划案/` 内索引逐项列出的文件。
6. `项目索引.md` 只作为配置输入，不注入。
7. 索引列出但三区缺失、或三区存在但索引未列出的 Markdown，均停止。

## 停止与日志

每次运行，无论成功、停止还是干跑，都会尝试写：

- `logs/inject_headers_YYYYMMDD_HHMMSS_ffffff.json`
- `logs/latest.json`

日志和 stdout 只记录机器事实，不写处理建议：

- `status`
- `exit_code`
- `reason_code`
- `stage`
- `summary`
- `details`
- `metrics`
- `log_path`

日志写 `ai_report_required=true`。执行脚本的 AI 必须读取 stdout 或 `logs/latest.json`，把事实字段报告给 thoth。

## 安全规则

1. 固定只允许处理 `E:\works\mortal-cultivation-war3\docs\修仙项目`。
2. 全部 Markdown 先完成索引一致性、目录树格式、文件集合、定位边界和 UTF-8 解码检查，通过后才写。
3. 注入使用同目录临时文件原子替换；批量写入中途失败时尝试回滚。
4. 代码围栏内不识别标题，也不剥离同形示例文本。
5. `--strip` 只生成指定目录中的无节头副本，不修改三区。
6. 本脚本不删文件、不做三区同步、不上传 RAGFlow。
7. `--dry-run` 不修改项目文档，但仍写运行日志。

## 用法

```powershell
python inject_headers.py --dry-run
python inject_headers.py
python inject_headers.py --strip --dry-run
python inject_headers.py --strip --output "E:\tmp\修仙项目_剥离版"
```

顺序：完成 1→2→3 同步 → 三份索引一致 → `--dry-run` → 执行 AI 报告事实结果 → 注入 → git检查与提交；合并到 `main` 后才允许运行 ragflow-sync。

## 当前边界

- 只处理标准 ATX 二级、三级标题，即 `## 标题`、`### 标题`。
- 单节被知识库继续切成多片时，只有首片自动带节头。



