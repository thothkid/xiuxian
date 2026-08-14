# RAGFlow 文档同步脚本

将本地项目文档增量同步到 RAGFlow 知识库（支持单/多知识库模式，知识库列表完全由配置驱动）。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 并按需修改。

### 基础配置

```env
RAGFLOW_API_URL=http://192.168.50.242
RAGFLOW_API_KEY=your-api-key
PROJECT_ROOT=../..
SYNC_DIRS=docs,xlsx/export_json
EXCLUDE_PATTERNS=*.xlsx
```

### 多知识库模式（推荐）

按路径规则自动分类文档。**规则名可以任意起**，每个规则名对应一个
`{规则名大写}_DATASET_ID` 变量——加新知识库只需加一条规则和一个 ID 变量，无需改代码：

```env
MULTI_DATASET_ENABLED=true

# 规则名=路径前缀1,路径前缀2,...；多个规则用 | 分隔；第一个匹配的规则生效
DATASET_RULES=tech=docs/tech|planning=docs/planning

TECH_DATASET_ID=tech-dataset-id-here
PLANNING_DATASET_ID=planning-dataset-id-here

# 未匹配任何规则的文件兜底归入的规则名（可选；不配则跳过并警告）
DEFAULT_RULE=planning
```

**只同步部分知识库**：不想同步的库不配 ID 即可（会警告并跳过该库文件）。
例如策划同事的机器只配 `PLANNING_DATASET_ID`，技术文档不会被同步。
也可以用命令行临时限定：`python main.py --datasets planning`。

### 单知识库模式

```env
MULTI_DATASET_ENABLED=false
RAGFLOW_DATASET_ID=your-dataset-id

# 可选：仍按 DATASET_RULES 过滤，只同步指定规则匹配的文件
# DATASET_RULES=tech=docs/tech|planning=docs/planning
# SYNC_ONLY_RULES=planning
```

不配 `SYNC_ONLY_RULES` 时，`SYNC_DIRS` 下的所有文件都会同步进这一个库。

## 使用

### 首次运行：初始化内容索引（强制）

如果 RAGFlow 远程已有文档，但本地 `sync_state.json` 是空的（或刚重置），**必须**先初始化内容索引：

```bash
python main.py --init-index --verbose
```

此操作会**下载云端文档并计算真实哈希**，同时建立路径索引——之后的同步才能正确识别
"跳过/更新/移动"，否则会把所有本地文件当新增重传，知识库文档翻倍。

**同步器会强制这一点**：本地状态为空但远程已有文档时，同步会直接中止并提示先跑
`--init-index`（冷启动保护）。确要跳过用 `--force-cold-start`（退化为 size 近似保护，不推荐）。

### 预览变更（不实际执行）

```bash
python main.py --dry-run --verbose
```

多库/单库模式的 dry-run 走同一套逻辑，**包含删除预览**——会列出将从远程删除哪些文档。

### 执行同步

```bash
python main.py
```

### 其他参数

| 参数 | 说明 |
|------|------|
| `--verbose` | 详细日志 |
| `--datasets a,b` | 只同步指定规则名的知识库（多库模式） |
| `--force-delete` | 放行批量删除保护（见下） |
| `--force-cold-start` | 跳过冷启动保护（不推荐） |
| `--reset` | 重置同步状态；重置后需重新 `--init-index` |

## 同步逻辑

### 核心机制：基于内容哈希去重 + 智能删除保护

**设计原则**：RAG 知识库关注的是**内容**而非路径。文档路径变更不应触发重新上传或删除。

### 同步流程

1. 扫描 `SYNC_DIRS`（递归），实时读取项目根目录 `.gitignore` 排除匹配文件
2. **多知识库模式**：根据 `DATASET_RULES` 分类；未匹配的归入 `DEFAULT_RULE`，
   没配兜底则跳过并警告
3. 计算每个文件的 SHA256 哈希
4. **对每个知识库独立**执行（索引也按知识库分仓，互不干扰）：
   - 获取该库远程文档列表
   - 分类本地文件（状态里的 doc_id 一律与远程列表交叉校验，**远程查无此文档就不算已同步**）：
     - **哈希已存在（content_index）且远程文档仍在** → 复用（内容已存在，路径变更）
     - **路径在状态中但哈希变了** → 更新（先删旧传新，并清理旧哈希索引）
     - **其余** → 新增（若远程已有同名旧文档则先删再传，防止重复堆积）
   - 删除保护（由强到弱）：
     - **content_index 精确保护**：远程文档内容仍存活于本地 → 疑似移动，不删
     - **size 近似保护**：仅冷启动放行时使用
     - **两者都不满足** → 确认删除
5. 输出同步报告（按知识库分组）

### 安全闸

| 安全闸 | 触发条件 | 行为 | 放行方式 |
|--------|---------|------|---------|
| 冷启动保护 | 本库状态为空 + 远程已有文档 | 中止该库同步（防全量重复上传） | 先 `--init-index`；或 `--force-cold-start` |
| 批量删除保护 | 待删数量 > max(10, 远程文档数 30%) | 拦截删除（新增/更新照常） | 确认后 `--force-delete` |

批量删除保护主要防两类事故：`SYNC_DIRS`/`DATASET_RULES` 改动导致扫描范围缩小，
以及**多台机器配置不一致**（A 机同步的文档被 B 机当"本地已删除"清掉）。

### 多机使用注意

同步状态 `sync_state.json` 只存在各自本地。多台机器同步**同一个**知识库时：

- 每台机器首次使用都要先 `--init-index`
- 各机器的 `SYNC_DIRS` / `DATASET_RULES` / `EXCLUDE_PATTERNS` 必须一致，
  否则一台机器会把另一台上传的文档判为"本地已删除"而清掉（批量删除保护会拦截大规模误删，
  但少量误删仍可能发生）
- 只维护部分库的机器（如策划同事）应只配置对应库的 `*_DATASET_ID`，
  让其他库整体跳过，而不是缩小 `SYNC_DIRS`

### 状态管理

同步状态保存在 `sync_state.json`（v3 格式，按知识库分仓）：

```json
{
  "version": 3,
  "datasets": {
    "<dataset_id>": {
      "path_index":    { "docs/thoth/世界观.md": "abc123..." },
      "content_index": { "abc123...": "ragflow_doc_id_456" }
    }
  }
}
```

- **path_index**：路径 → 哈希（检测变更）
- **content_index**：哈希 → RAGFlow 文档 ID（同库内去重/复用；跨库不共享，
  避免"复用"到别的知识库里的文档）

**状态自愈**：状态只增不减，若文档在 RAGFlow 侧被删掉（控制台手删、解析失败被清理、
知识库重建），本地仍记着旧 doc_id。同步时每个 doc_id 都会与远程实际列表比对，
查无此文档即改判补传，因此**不需要靠 `--reset` + `--init-index` 来修复这类漂移**。

该文件已加入项目 `.gitignore`，不会被提交到版本控制。

**向后兼容**：旧格式（v1 纯映射 / v2 全局索引）首次加载时按当前分类规则自动迁移到
v3 分仓格式；无法归属任何知识库的条目会被丢弃（下次同步按新文件处理）。

## 测试

```bash
python test_sync_engine.py
```

无需网络（MockClient），覆盖删除保护、安全闸、状态迁移等 14 个回归场景。
