#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步引擎：编排增量同步流程（按知识库分仓，见 sync_state.py v3）"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ragflow_client import RagflowClient
from sync_state import DatasetState


def _normalize(path: str) -> str:
    """统一路径分隔符为正斜杠，便于匹配"""
    return path.replace('\\', '/')


def _match_remote_to_local(remote_name: str, local_files: Dict[str, Path]) -> Optional[str]:
    """
    将远程文档名匹配到本地相对路径。
    优先精确匹配（上传时文档名就是相对路径）；
    降级为带分隔符锚定的后缀匹配（兼容历史上只用文件名上传的文档），
    避免 'a.md' 误匹配 'xxa.md' 这类无锚定 endswith 的假阳性。
    """
    remote_norm = _normalize(remote_name)
    for local_path in local_files.keys():
        local_norm = _normalize(local_path)
        if local_norm == remote_norm or local_norm.endswith('/' + remote_norm):
            return local_path
    return None


def init_content_index(
    client: RagflowClient,
    local_files: Dict[str, Path],
    local_hashes: Dict[str, str],
    dataset_state: DatasetState,
    verbose: bool = False
) -> int:
    """
    初始化内容索引（从云端文档建立真实哈希映射）

    设计原因：
    - RAGFlow 远程已有文档，但本地 content_index 为空
    - 必须下载云端文档，计算**云端文档的真实哈希**
    - 这样才能正确检测云端文档是否被修改

    返回: 成功初始化的文档数量
    """
    print('\n→ 初始化内容索引...')
    print('  [INFO] 下载云端文档并计算真实哈希（可能需要几分钟）')

    # 获取远程文档列表
    try:
        remote_docs = client.list_documents()  # {文档名: {'id': ..., 'size': ...}}
        print(f'  远程文档数量: {len(remote_docs)}')
    except Exception as e:
        print(f'  [ERROR] 获取远程文档列表失败: {e}')
        return 0

    # 下载云端文档并计算哈希
    initialized = 0
    failed = 0
    skipped = 0  # 本地不存在，跳过

    for i, (remote_name, remote_info) in enumerate(remote_docs.items(), 1):
        if i % 20 == 0:
            print(f'  进度: {i}/{len(remote_docs)}...')

        # 下载云端文档
        file_content = client.download_document(remote_info['id'])
        if file_content is None:
            failed += 1
            if verbose:
                print(f'  [WARN] 下载失败: {remote_name}')
            continue

        # 计算云端文档的真实哈希
        cloud_hash = calculate_sha256_bytes(file_content)

        # 建立索引：云端哈希 → 云端文档ID
        dataset_state.set_doc_id(cloud_hash, remote_info['id'])
        initialized += 1

        # 检查本地是否有对应文件（精确/锚定匹配，见 _match_remote_to_local）
        matched_local_path = _match_remote_to_local(remote_name, local_files)

        if matched_local_path:
            # 路径索引也一并建立：远程与本地一致的文件下次直接判「跳过」，
            # 不一致的判「更新」，避免 init 后首次同步把全部文件当新增重传
            local_hash = local_hashes.get(matched_local_path, '')
            if cloud_hash == local_hash:
                dataset_state.set_hash(matched_local_path, local_hash)
            else:
                print(f'  [WARN] 云端和本地内容不一致: {remote_name}')
                print(f'    云端哈希: {cloud_hash[:16]}...')
                print(f'    本地哈希: {local_hash[:16]}...')
        else:
            skipped += 1

    print(f'\n  [OK] 内容索引初始化完成:')
    print(f'    ✓ 成功: {initialized} 个文档')
    if failed:
        print(f'    ✗ 失败: {failed} 个文档（下载失败）')
    if skipped:
        print(f'    ⏭ 本地不存在: {skipped} 个文档')

    return initialized


def calculate_sha256_bytes(file_content: bytes) -> str:
    """计算字节内容的 SHA256 哈希"""
    sha256 = hashlib.sha256()
    sha256.update(file_content)
    return sha256.hexdigest()


class SyncReport:
    """同步报告"""

    def __init__(self):
        self.added = 0
        self.updated = 0
        self.deleted = 0
        self.moved = 0       # 路径变更但内容不变（复用已有文档）
        self.skipped = 0
        self.failed = 0
        self.errors: list = []
        self.aborted = False          # 冷启动保护触发，本库未执行任何操作
        self.deletion_blocked = 0     # 批量删除保护拦下的删除数量

    def add_error(self, filename: str, error: str) -> None:
        self.failed += 1
        self.errors.append(f'{filename}: {error}')

    def print_report(self) -> None:
        print('\n' + '=' * 60)
        print('同步报告')
        print('=' * 60)
        if self.aborted:
            print('⛔ 已中止：冷启动保护（详见上方提示，先运行 --init-index）')
            print('=' * 60)
            return
        print(f'✓ 新增: {self.added}')
        print(f'🔄 更新: {self.updated}')
        print(f'✗ 删除: {self.deleted}')
        print(f'♻️  移动: {self.moved}')
        print(f'⏭ 跳过: {self.skipped}')
        print(f'✗ 失败: {self.failed}')
        if self.deletion_blocked:
            print(f'🛑 拦截删除: {self.deletion_blocked}（批量删除保护，用 --force-delete 放行）')

        if self.errors:
            print('\n### 错误列表')
            for error in self.errors:
                print(f'  - {error}')

        print('=' * 60)


def sync(
    client: RagflowClient,
    local_files: Dict[str, Path],
    local_hashes: Dict[str, str],
    dataset_state: DatasetState,
    dry_run: bool = False,
    verbose: bool = False,
    force_delete: bool = False,
    allow_cold_start: bool = False,
    dataset_name: str = ''
) -> SyncReport:
    """
    对单个知识库执行增量同步（基于内容哈希去重）

    流程：
    1. 获取远程文档列表
    2. 基于内容哈希判断（doc_id 一律与远程列表交叉校验，见 _doc_alive）：
       - 哈希已存在且远程文档仍在 → 复用（即使路径变更）
       - 哈希已存在但远程文档已消失 → 补传（状态自愈，不再永久跳过）
       - 哈希不存在 → 上传新增
    3. 清理远程有但本地无的文档

    安全闸：
    - 冷启动保护：本库状态为空但远程已有文档 → 拒绝执行（防全量重复上传），
      需先 --init-index 建立索引；--force-cold-start 可强行放行（退化为 size 保护）
    - 批量删除保护：待删数量超过 max(10, 远程文档数的 30%) → 拦截删除
      （多为配置漂移/扫描范围缩小所致），--force-delete 放行

    设计原因：RAG 知识库关注内容而非路径，路径变更不应触发重新上传
    """
    report = SyncReport()
    tag = f'[{dataset_name}] ' if dataset_name else ''

    # 防御：只保留本库文件子集的哈希（多库模式下防止别的库的哈希
    # 混入删除保护/复用判断，造成跨库误保护）
    local_hashes = {p: h for p, h in local_hashes.items() if p in local_files}

    # ========================================
    # 步骤1: 获取远程文档列表
    # ========================================
    print(f'\n→ {tag}获取远程文档列表...')
    try:
        remote_docs = client.list_documents()  # {文档名: {'id': ..., 'size': ...}}
        print(f'  远程文档数量: {len(remote_docs)}')
    except Exception as e:
        report.add_error('REMOTE', str(e))
        return report

    # ========================================
    # 安全闸1: 冷启动保护
    # 本库状态为空 + 远程已有文档 = 本机没有任何索引可对照，
    # 直接同步会把所有本地文件当新增重传（远程同名文档不会被清理 → 文档翻倍）
    # ========================================
    if dataset_state.is_empty() and remote_docs and not allow_cold_start:
        msg = (f'{tag}本地状态为空，但远程知识库已有 {len(remote_docs)} 个文档。\n'
               f'  直接同步会导致全量重复上传。请先运行:\n'
               f'    python main.py --init-index\n'
               f'  建立内容索引后再同步；确要跳过请加 --force-cold-start（退化为 size 近似保护）。')
        if dry_run:
            print(f'\n⚠ [冷启动警告] {msg}')
        else:
            print(f'\n⛔ [冷启动保护] {msg}')
            report.aborted = True
            return report

    # ========================================
    # 步骤2: 基于内容哈希 + size 保护分类文件
    # ========================================
    local_paths = set(local_files.keys())

    # 远程实际存在的文档 ID 集合。
    # 本地状态只增不减：文档若在 RAGFlow 侧消失（控制台手动删除、解析失败被清理、
    # 知识库被重建），本地 content_index 仍记着那个 doc_id，该文件就会被永久判为
    # 「跳过」而再也传不上去。必须拿远程真实列表交叉校验，让状态能自愈。
    remote_ids = {info['id'] for info in remote_docs.values()}

    def _doc_alive(hash_value: str) -> bool:
        """该内容哈希是否对应一个远程仍然存在的文档"""
        doc_id = dataset_state.get_doc_id_by_hash(hash_value)
        return bool(doc_id) and doc_id in remote_ids

    # 本次扫描的所有本地文件内容哈希（判断远程文档内容是否仍存活于本地）
    current_local_hashes = set(local_hashes.values())

    # 内容哈希 → 本地文件路径列表（判断该内容的本地归属是否已在远程有副本）
    paths_by_hash: Dict[str, list] = {}
    for _p, _h in local_hashes.items():
        paths_by_hash.setdefault(_h, []).append(_p)

    # 构建以下辅助索引用于删除保护：
    # 1. content_index 反向索引：doc_id → hash（精确匹配）
    hash_by_doc_id: Dict[str, str] = {}
    for hash_val, doc_id_val in dataset_state.content_index.items():
        if doc_id_val:
            hash_by_doc_id[doc_id_val] = hash_val

    # 2. 本地文件 size 映射（冷启动保护，无 content_index 时降级使用）
    local_size_map: Dict[int, list] = {}
    for local_path, local_file in local_files.items():
        try:
            sz = local_file.stat().st_size
            local_size_map.setdefault(sz, []).append(local_path)
        except OSError:
            pass

    # 删除判断：依次检查 content_index 保护 → size 保护 → 确认删除
    to_delete_ids: List[str] = []
    to_delete_names: set = set()
    to_protect_names: set = set()  # 被保护的远程文档（移动/重命名）
    for remote_name, remote_info in remote_docs.items():
        if remote_name in local_paths:
            continue
        remote_doc_id = remote_info['id']
        remote_size = remote_info.get('size', 0)

        # 保护 1：该远程文档的内容哈希仍对应某个当前本地文件 → 内容存活（移动/改路径），不删。
        # 注意：不能只判断 doc_id 是否在 content_index 中——content_index 只增不减，
        # 文件被重命名+改内容或删除后，旧哈希→doc_id 会残留成僵尸，导致旧远程文档被误保护而永不删除。
        mapped_hash = hash_by_doc_id.get(remote_doc_id)
        if mapped_hash is not None and mapped_hash in current_local_hashes:
            # 仅当承载该内容的本地文件尚未在远程拥有副本时才保护（真正的“移动/改路径”，
            # 由后续 to_reuse 重新指向）；若内容的本地归属路径已在远程有副本，
            # 则本远程文档是重复的旧路径副本，应删除去重，而非保护。
            holders = paths_by_hash.get(mapped_hash, [])
            if not any(h in remote_docs for h in holders):
                to_protect_names.add(remote_name)
                continue

        # 保护 2：仅冷启动（content_index 为空）时，用 size 近似匹配防误删；
        # 非冷启动时内容存活性已由保护1精确判断，不再用 size（避免 size 碰撞误保护）
        if not dataset_state.content_index and remote_size > 0 and remote_size in local_size_map:
            to_protect_names.add(remote_name)
            if verbose:
                suspect_paths = local_size_map[remote_size]
                print(f'  [SUSPECT] {remote_name} (size={remote_size}) '
                      f'protected — size matches: {suspect_paths}')
            continue

        # 确认删除
        to_delete_ids.append(remote_doc_id)
        to_delete_names.add(remote_name)

    # ========================================
    # 安全闸2: 批量删除保护
    # 待删数量异常大，通常是 SYNC_DIRS/分类规则变化或多机配置漂移，
    # 而不是真的删了这么多本地文档——拦下来让人确认
    # ========================================
    delete_threshold = max(10, int(len(remote_docs) * 0.3))
    deletion_blocked = False
    if to_delete_ids and not force_delete and len(to_delete_ids) > delete_threshold:
        deletion_blocked = True
        report.deletion_blocked = len(to_delete_ids)
        print(f'\n🛑 {tag}[批量删除保护] 本次将删除 {len(to_delete_ids)} 个远程文档'
              f'（超过阈值 {delete_threshold}），已拦截。')
        print('  常见原因：SYNC_DIRS/DATASET_RULES 改动、多台机器配置不一致。')
        print('  确认无误后用 --force-delete 放行。被拦截的文档:')
        for name in sorted(to_delete_names):
            print(f'    - {name}')

    # 本地文件分类
    to_skip = set()       # 内容未变更，跳过
    to_add = set()        # 新文件（哈希不存在）
    to_update = set()     # 内容变更（哈希变化）
    to_reuse = set()      # 内容已存在（路径变更，复用已有文档）
    to_revive = set()     # 状态记为已同步，但远程文档已不存在 → 补传（仅用于日志区分）

    for path in local_paths:
        local_hash = local_hashes.get(path, '')
        alive = _doc_alive(local_hash)

        if dataset_state.has_file(path):
            # 路径在 path_index 中 → 对比缓存哈希
            cached_hash = dataset_state.get_hash(path)
            if cached_hash != local_hash:
                to_update.add(path)         # 路径未变，哈希已变
            elif not alive:
                # 哈希未变，但该内容没有可用的远程文档：
                # 要么内容索引是 set_hash 的 None 占位（从未真正上传），
                # 要么记录的 doc_id 在远程已不存在（被删/被清理）→ 补传
                to_add.add(path)
                to_revive.add(path)
            else:
                to_skip.add(path)           # 路径 + 哈希未变且远程文档仍在
        elif alive:
            to_reuse.add(path)              # 新路径，内容已有存活的远程文档 → 复用
        else:
            to_add.add(path)                # 全新文件（或旧 doc_id 已失效）

    report.skipped = len(to_skip)

    if verbose:
        print(f'  跳过: {len(to_skip)}, 新增: {len(to_add)}, '
              f'更新: {len(to_update)}, 复用: {len(to_reuse)}, '
              f'删除: {len(to_delete_names)}, 保护(移动): {len(to_protect_names)}')
        if to_revive:
            print(f'  ⚠ 其中 {len(to_revive)} 个是「本地状态记为已同步、但远程已无此文档」的补传')

    if dry_run:
        print(f'\n[DRY RUN] {tag}预览变更（不实际执行）')
        print('=' * 60)
        if to_add:
            print(f'\n📤 将新增 {len(to_add)} 个文件:')
            for path in sorted(to_add):
                if path in remote_docs:
                    note = '（远程已有同名旧文档，将先删再传）'
                elif path in to_revive:
                    note = '（本地状态记为已同步，但远程已无此文档 → 补传）'
                else:
                    note = ''
                print(f'  + {path}{note}')
        if to_update:
            print(f'\n🔄 将更新 {len(to_update)} 个文件:')
            for path in sorted(to_update):
                print(f'  ~ {path}')
        if to_reuse:
            print(f'\n♻️  将复用 {len(to_reuse)} 个文件（内容已存在，路径变更）:')
            for path in sorted(to_reuse):
                print(f'  • {path}')
        if to_protect_names:
            print(f'\n🔒 将保护 {len(to_protect_names)} 个远程文档（疑似移动）:')
            for name in sorted(to_protect_names):
                print(f'  🛡 {name}')
        if to_delete_names:
            blocked = '（将被批量删除保护拦截，需 --force-delete）' if deletion_blocked else ''
            print(f'\n✗ 将删除 {len(to_delete_names)} 个远程文件{blocked}:')
            for name in sorted(to_delete_names):
                print(f'  - {name}')
        print('=' * 60)
        return report

    # ========================================
    # 步骤3: 执行删除
    # ========================================
    print(f'\n→ {tag}开始同步...')
    if to_delete_ids and not deletion_blocked:
        print(f'\n✗ 删除 {len(to_delete_ids)} 个远程文档...')
        if verbose:
            for name in sorted(to_delete_names):
                print(f'  - {name}')
        try:
            deleted_count = client.delete_documents(to_delete_ids)
            report.deleted = deleted_count
            if verbose:
                print(f'  ✓ 已删除 {deleted_count} 个文件')
            for name in to_delete_names:
                dataset_state.remove_by_path(name)
            # 清理 content_index 中指向已删除文档的僵尸哈希（remove_by_hash 确认无路径引用才删）
            for did in to_delete_ids:
                dead_hash = hash_by_doc_id.get(did)
                if dead_hash:
                    dataset_state.remove_by_hash(dead_hash)
        except Exception as e:
            report.add_error('批量删除', str(e))

    if to_protect_names:
        print(f'\n🔒 保护 {len(to_protect_names)} 个远程文档（内容存活着，路径变更）:')
        for name in sorted(to_protect_names):
            if verbose:
                print(f'  🛡 {name}')

    # ========================================
    # 步骤4: 执行新增
    # ========================================
    if to_add:
        print(f'\n📤 新增 {len(to_add)} 个文件...')
        for path in sorted(to_add):
            file_path = local_files[path]
            file_hash = local_hashes[path]
            try:
                # 远程已有同名文档但本地状态没记录（状态丢失/部分重置）→
                # 先删旧的再传，避免同名文档在知识库里越积越多
                if path in remote_docs:
                    stale_id = remote_docs[path]['id']
                    client.delete_documents([stale_id])
                    if verbose:
                        print(f'  ✗ 清理远程同名旧文档: {path} ({stale_id[:8]}...)')

                doc_id = client.upload_document(str(file_path), path)
                if not doc_id:
                    report.add_error(path, '上传返回空 ID')
                    continue

                # 上传成功立即记录状态——即使随后触发解析失败，下次也不会重传出重复文档
                dataset_state.set_hash(path, file_hash)
                dataset_state.set_doc_id(file_hash, doc_id)
                try:
                    client.parse_document(doc_id)
                except Exception as pe:
                    report.add_error(path, f'已上传但触发解析失败（请在 RAGFlow 控制台手动解析）: {pe}')
                    continue
                report.added += 1
                print(f'  ✓ {path}')
            except Exception as e:
                report.add_error(path, str(e))

    # ========================================
    # 步骤5: 处理内容复用（路径变更场景）
    # ========================================
    if to_reuse:
        print(f'\n♻️  复用 {len(to_reuse)} 个文件（内容已存在，仅路径变更）:')
        for path in sorted(to_reuse):
            file_hash = local_hashes[path]
            # 从内容索引获取已有文档 ID
            existing_doc_id = dataset_state.get_doc_id_by_hash(file_hash)
            if existing_doc_id:
                # 清理同一 hash 的旧路径索引（确保 path_index 不残留）
                old_paths = [p for p, h in dataset_state.path_index.items()
                             if h == file_hash and p != path]
                for old_path in old_paths:
                    dataset_state.remove_by_path(old_path)
                    if verbose:
                        print(f'  • 清除旧路径映射: {old_path}')
                # 更新新路径索引，但不重新上传
                dataset_state.set_hash(path, file_hash)
                report.moved += 1
                print(f'  • {path} (复用文档 {existing_doc_id[:8]}...)')
            else:
                # 理论上不应该发生，降级为更新
                to_update.add(path)

    # ========================================
    # 步骤6: 检查并更新
    # ========================================
    if to_update:
        print(f'\n🔄 更新 {len(to_update)} 个文件...')
        for path in sorted(to_update):
            file_path = local_files[path]
            file_hash = local_hashes[path]
            old_hash = dataset_state.get_hash(path)
            try:
                # 如果旧文档在远程列表中，删除它（先删后传）
                if path in remote_docs:
                    old_doc_id = remote_docs[path]['id']
                    client.delete_documents([old_doc_id])

                # 上传新文档
                doc_id = client.upload_document(str(file_path), path)
                if not doc_id:
                    report.add_error(path, '上传返回空 ID')
                    continue

                dataset_state.set_hash(path, file_hash)
                dataset_state.set_doc_id(file_hash, doc_id)
                # 清理旧哈希的僵尸映射：旧文档已删，若无其他路径仍持有旧内容，
                # 必须移除 旧哈希→旧doc_id，否则日后内容回滚会被判「复用」而指向已删文档
                if old_hash and old_hash != file_hash:
                    dataset_state.remove_by_hash(old_hash)

                try:
                    client.parse_document(doc_id)
                except Exception as pe:
                    report.add_error(path, f'已上传但触发解析失败（请在 RAGFlow 控制台手动解析）: {pe}')
                    continue
                report.updated += 1
                print(f'  ✓ {path}')
            except Exception as e:
                report.add_error(path, str(e))

    # ========================================
    # 步骤7: 输出报告（状态保存由调用方统一处理）
    # ========================================
    report.print_report()

    return report


def classify_files(
    local_files: Dict[str, Path],
    dataset_rules: Dict[str, List[str]],
    default_rule: str = ''
) -> Tuple[Dict[str, Dict[str, Path]], Dict[str, Path]]:
    """
    根据分类规则将文件分配到不同知识库

    规则匹配逻辑：按路径前缀匹配，第一个匹配的规则生效。
    未匹配的文件归入 default_rule 指定的规则；未配置 default_rule 时
    进入 unmatched（由调用方警告并跳过，不再静默塞进某个库）。

    参数：
        local_files: {相对路径: 绝对路径}
        dataset_rules: {'tech': ['docs/tech'], 'planning': ['docs/planning']}
        default_rule: 未匹配文件的兜底规则名（须存在于 dataset_rules，可为空）

    返回：
        (classified, unmatched)
        classified: {'tech': {path: Path}, 'planning': {path: Path}}
        unmatched:  {path: Path}  # 无兜底规则时未能归类的文件
    """
    classified: Dict[str, Dict[str, Path]] = {name: {} for name in dataset_rules}
    unmatched: Dict[str, Path] = {}

    for rel_path, file_path in local_files.items():
        normalized_path = _normalize(rel_path)

        matched = False
        for dataset_name, prefixes in dataset_rules.items():
            for prefix in prefixes:
                normalized_prefix = _normalize(prefix)
                # 匹配路径前缀或子目录
                if normalized_path == normalized_prefix or normalized_path.startswith(normalized_prefix + '/'):
                    classified[dataset_name][rel_path] = file_path
                    matched = True
                    break
            if matched:
                break

        if not matched:
            if default_rule and default_rule in classified:
                classified[default_rule][rel_path] = file_path
            else:
                unmatched[rel_path] = file_path

    return classified, unmatched


class MultiDatasetReport:
    """多知识库同步报告"""

    def __init__(self):
        self.reports: Dict[str, SyncReport] = {}
        self.unmatched_count = 0   # 未匹配任何规则、被跳过的文件数
        self.skipped_datasets: List[str] = []  # 未配置 dataset_id 而跳过的规则名

    def add_report(self, dataset_name: str, report: SyncReport) -> None:
        self.reports[dataset_name] = report

    def has_failure(self) -> bool:
        """是否存在需要人工关注的结果（失败/中止/删除被拦截）"""
        return any(r.failed > 0 or r.aborted or r.deletion_blocked > 0
                   for r in self.reports.values())

    def print_report(self) -> None:
        print('\n' + '=' * 60)
        print('多知识库同步报告')
        print('=' * 60)

        total = SyncReport()

        for dataset_name, report in self.reports.items():
            print(f'\n📚 {dataset_name}:')
            if report.aborted:
                print('  ⛔ 已中止（冷启动保护，先运行 --init-index）')
                continue
            print(f'  ✓ 新增: {report.added}')
            print(f'  🔄 更新: {report.updated}')
            print(f'  ✗ 删除: {report.deleted}')
            print(f'  ♻️  移动: {report.moved}')
            print(f'  ⏭ 跳过: {report.skipped}')
            print(f'  ✗ 失败: {report.failed}')
            if report.deletion_blocked:
                print(f'  🛑 拦截删除: {report.deletion_blocked}（需 --force-delete）')

            if report.errors:
                print(f'  错误:')
                for error in report.errors:
                    print(f'    - {error}')

            total.added += report.added
            total.updated += report.updated
            total.deleted += report.deleted
            total.moved += report.moved
            total.skipped += report.skipped
            total.failed += report.failed

        if self.skipped_datasets:
            print(f'\n⏭ 未配置 dataset_id 而跳过的知识库: {", ".join(self.skipped_datasets)}')
        if self.unmatched_count:
            print(f'⚠ 未匹配任何分类规则而跳过的文件: {self.unmatched_count} 个'
                  f'（配置 DEFAULT_RULE 或补充 DATASET_RULES）')

        print(f'\n📊 总计:')
        print(f'  ✓ 新增: {total.added}')
        print(f'  🔄 更新: {total.updated}')
        print(f'  ✗ 删除: {total.deleted}')
        print(f'  ♻️  移动: {total.moved}')
        print(f'  ⏭ 跳过: {total.skipped}')
        print(f'  ✗ 失败: {total.failed}')
        print('=' * 60)


def sync_multi_dataset(
    api_url: str,
    api_key: str,
    local_files: Dict[str, Path],
    local_hashes: Dict[str, str],
    sync_state,
    dataset_rules: Dict[str, List[str]],
    dataset_ids: Dict[str, str],
    default_rule: str = '',
    only_datasets: Optional[List[str]] = None,
    dry_run: bool = False,
    verbose: bool = False,
    force_delete: bool = False,
    allow_cold_start: bool = False
) -> MultiDatasetReport:
    """
    多知识库增量同步

    流程：
    1. 根据规则分类文件（未匹配 → default_rule 或跳过警告）
    2. 对每个知识库独立执行同步（dry-run 直接透传给 sync()，
       预览与真实执行走同一套逻辑，包含删除预览）
    3. 汇总报告

    参数：
        dataset_ids: {规则名: dataset_id}，由调用方从配置解析（引擎不读环境变量）
        only_datasets: 只同步这些规则名对应的知识库（None = 全部）
    """
    report = MultiDatasetReport()

    # 分类文件
    classified, unmatched = classify_files(local_files, dataset_rules, default_rule)
    report.unmatched_count = len(unmatched)

    if unmatched:
        print(f'\n⚠ {len(unmatched)} 个文件未匹配任何分类规则，跳过同步'
              f'（配置 DEFAULT_RULE 或补充 DATASET_RULES）:')
        for path in sorted(unmatched)[:10]:
            print(f'  ? {path}')
        if len(unmatched) > 10:
            print(f'  ... 及其余 {len(unmatched) - 10} 个')

    if verbose:
        print('\n→ 文件分类结果:')
        for dataset_name, files in classified.items():
            print(f'  {dataset_name}: {len(files)} 个文件')

    # 对每个知识库执行同步
    for dataset_name, files in classified.items():
        if only_datasets is not None and dataset_name not in only_datasets:
            if verbose:
                print(f'\n⏭ {dataset_name}: 不在 --datasets 指定范围，跳过')
            continue

        if not files:
            if verbose:
                print(f'\n⏭ {dataset_name}: 无文件，跳过')
            continue

        dataset_id = dataset_ids.get(dataset_name, '')
        if not dataset_id:
            print(f'\n⏭ {dataset_name}: 未配置 {dataset_name.upper()}_DATASET_ID，'
                  f'跳过该库 {len(files)} 个文件')
            report.skipped_datasets.append(dataset_name)
            continue

        if verbose:
            print(f'\n→ 同步到 {dataset_name} (dataset_id: {dataset_id})...')

        # 创建客户端
        client = RagflowClient(
            base_url=api_url,
            api_key=api_key,
            dataset_id=dataset_id
        )

        # 该库的文件子集哈希（防止跨库哈希混入删除保护）
        subset_hashes = {p: local_hashes[p] for p in files if p in local_hashes}

        # 执行同步（dry-run 透传，预览与真实执行同一套逻辑）
        dataset_report = sync(
            client=client,
            local_files=files,
            local_hashes=subset_hashes,
            dataset_state=sync_state.for_dataset(dataset_id),
            dry_run=dry_run,
            verbose=verbose,
            force_delete=force_delete,
            allow_cold_start=allow_cold_start,
            dataset_name=dataset_name
        )

        report.add_report(dataset_name, dataset_report)

    # 保存状态 & 输出报告
    if not dry_run:
        sync_state.save()
    report.print_report()

    return report
