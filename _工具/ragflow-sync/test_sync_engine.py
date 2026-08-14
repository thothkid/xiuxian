# -*- coding: utf-8 -*-
"""sync_engine / sync_state 回归测试（无需网络，使用 MockClient）

覆盖：
- 删除保护（僵尸清理 / 纯移动保护 / 冷启动 size 保护 / 重复副本去重）
- 冷启动保护闸（状态空 + 远程非空 → 拒绝同步，防全量重复上传）
- 批量删除保护闸（待删超阈值 → 拦截，--force-delete 放行）
- 更新后旧哈希僵尸清理（内容回滚不再指向已删文档）
- 新增时远程同名旧文档先删再传（防重复堆积）
- 解析失败仍落状态（下次不重传出重复文档）
- 跨库哈希隔离（别的库的哈希不参与本库删除保护）
- classify_files（空规则不崩 / default_rule 兜底 / 未匹配返回）
- v2 → v3 状态迁移

运行：python test_sync_engine.py
"""
import json
import sys
import tempfile
from pathlib import Path

# 设置控制台编码为 UTF-8（Windows）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))
from sync_state import SyncState
import sync_engine


class MockClient:
    """模拟 RagflowClient，不联网，记录删除/上传调用。"""

    def __init__(self, remote, parse_fails=False):
        self._remote = remote
        self.deleted = []
        self.uploaded = []
        self.parse_fails = parse_fails

    def list_documents(self):
        return dict(self._remote)

    def delete_documents(self, ids):
        self.deleted.extend(ids)
        return len(ids)

    def upload_document(self, fpath, relpath):
        self.uploaded.append(relpath)
        return 'NEW_' + relpath

    def parse_document(self, did):
        if self.parse_fails:
            raise RuntimeError('mock parse failure')

    def download_document(self, did):
        return b''


def _new_ds(tmp, path_index=None, content_index=None, dataset_id='DS1'):
    st = SyncState(tmp / 'state.json')
    ds = st.for_dataset(dataset_id)
    ds.path_index.update(path_index or {})
    ds.content_index.update(content_index or {})
    return st, ds


def run_tests():
    tmp = Path(tempfile.mkdtemp())
    results = []

    # 场景1: 重命名+改内容 → 旧远程文档应被删除 + content_index 僵尸被清理（核心 bug）
    f1 = tmp / 'n1.md'; f1.write_text('new', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/old.md': 'H_old'}, content_index={'H_old': 'D_old'})
    cli = MockClient({'docs/x/old.md': {'id': 'D_old', 'size': 999}})
    sync_engine.sync(cli, {'docs/x/new.md': f1}, {'docs/x/new.md': 'H_new'}, ds, dry_run=False)
    results.append(('场景1 重命名+改内容 → 删旧+清僵尸',
                    ('D_old' in cli.deleted) and ('H_old' not in ds.content_index),
                    f'deleted={cli.deleted}, ci={ds.content_index}'))

    # 场景2: 纯移动（改路径不改内容）→ 旧远程文档应被保护（防回归）
    f2 = tmp / 'n2.md'; f2.write_text('same', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/old.md': 'H_same'}, content_index={'H_same': 'D_keep'})
    cli = MockClient({'docs/x/old.md': {'id': 'D_keep', 'size': 5}})
    r2 = sync_engine.sync(cli, {'docs/x/new.md': f2}, {'docs/x/new.md': 'H_same'}, ds, dry_run=False)
    results.append(('场景2 纯移动 → 保护不删(复用)',
                    (cli.deleted == []) and (r2.moved == 1),
                    f'deleted={cli.deleted}, moved={r2.moved}'))

    # 场景3: 冷启动强行放行（--force-cold-start）时 size 匹配 → 保护
    f3 = tmp / 'n3.md'; f3.write_bytes(b'x' * 100)
    _, ds = _new_ds(tmp)
    cli = MockClient({'docs/x/old.md': {'id': 'D_cold', 'size': 100}})
    sync_engine.sync(cli, {'docs/x/new.md': f3}, {'docs/x/new.md': 'H_cold'}, ds,
                     dry_run=False, allow_cold_start=True)
    results.append(('场景3 冷启动放行 + size 匹配 → 保护',
                    cli.deleted == [],
                    f'deleted={cli.deleted}'))

    # 场景4: 非冷启动 + size 碰撞但内容已不在本地 → 应删除（size 保护不再误触发）
    f4 = tmp / 'n4.md'; f4.write_bytes(b'y' * 100)
    _, ds = _new_ds(tmp, path_index={'docs/x/gone.md': 'H_gone'}, content_index={'H_gone': 'D_zombie'})
    cli = MockClient({'docs/x/gone.md': {'id': 'D_zombie', 'size': 100}})
    sync_engine.sync(cli, {'docs/x/new.md': f4}, {'docs/x/new.md': 'H_n'}, ds, dry_run=False)
    results.append(('场景4 非冷启动 size 碰撞 → 删僵尸(不误保护)',
                    ('D_zombie' in cli.deleted) and ('H_gone' not in ds.content_index),
                    f'deleted={cli.deleted}, ci={ds.content_index}'))

    # 场景5: 重复旧路径副本（内容==本地他处已同步文件）→ 删除去重，不再误当“移动”保护
    f5 = tmp / 'n5.md'; f5.write_text('dup', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/long/P.md': 'H_dup'}, content_index={'H_dup': 'D_old_dup'})
    cli = MockClient({'docs/long/P.md': {'id': 'D_long', 'size': 3},
                      'docs/old/P.md': {'id': 'D_old_dup', 'size': 3}})
    sync_engine.sync(cli, {'docs/long/P.md': f5}, {'docs/long/P.md': 'H_dup'}, ds, dry_run=False)
    results.append(('场景5 重复旧路径副本 → 删除去重(不误保护)',
                    ('D_old_dup' in cli.deleted) and ('D_long' not in cli.deleted),
                    f'deleted={cli.deleted}'))

    # 场景6: 有 path_index 记录但 content_index 为 None 占位（从未真正上传）→ 补传而非跳过
    f6 = tmp / 'n6.md'; f6.write_text('c6', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/wt.md': 'H_wt'}, content_index={'H_wt': None})
    cli = MockClient({})
    sync_engine.sync(cli, {'docs/x/wt.md': f6}, {'docs/x/wt.md': 'H_wt'}, ds, dry_run=False)
    results.append(('场景6 None占位残留 → 补传(不跳过)',
                    'docs/x/wt.md' in cli.uploaded,
                    f'uploaded={cli.uploaded}'))

    # 场景7: 冷启动保护 → 状态空 + 远程非空 → 中止，不上传不删除
    f7 = tmp / 'n7.md'; f7.write_text('c7', encoding='utf-8')
    _, ds = _new_ds(tmp)
    cli = MockClient({'docs/x/exist.md': {'id': 'D_e', 'size': 9}})
    r7 = sync_engine.sync(cli, {'docs/x/n7.md': f7}, {'docs/x/n7.md': 'H_7'}, ds, dry_run=False)
    results.append(('场景7 冷启动保护 → 中止(防全量重传)',
                    r7.aborted and cli.uploaded == [] and cli.deleted == [],
                    f'aborted={r7.aborted}, uploaded={cli.uploaded}, deleted={cli.deleted}'))

    # 场景8: 批量删除保护 → 待删 15 个(>阈值 max(10,30%)) → 拦截；--force-delete 放行
    f8 = tmp / 'n8.md'; f8.write_text('c8', encoding='utf-8')
    remote8 = {f'docs/x/d{i}.md': {'id': f'D_{i}', 'size': 1} for i in range(15)}
    remote8['docs/x/keep.md'] = {'id': 'D_keep8', 'size': 2}
    _, ds = _new_ds(tmp, path_index={'docs/x/keep.md': 'H_k8'}, content_index={'H_k8': 'D_keep8'})
    cli = MockClient(remote8)
    r8a = sync_engine.sync(cli, {'docs/x/keep.md': f8}, {'docs/x/keep.md': 'H_k8'}, ds, dry_run=False)
    blocked_ok = (cli.deleted == []) and (r8a.deletion_blocked == 15)
    _, ds = _new_ds(tmp, path_index={'docs/x/keep.md': 'H_k8'}, content_index={'H_k8': 'D_keep8'})
    cli = MockClient(remote8)
    r8b = sync_engine.sync(cli, {'docs/x/keep.md': f8}, {'docs/x/keep.md': 'H_k8'}, ds,
                           dry_run=False, force_delete=True)
    results.append(('场景8 批量删除保护 → 默认拦截 / force 放行',
                    blocked_ok and (len(cli.deleted) == 15) and (r8b.deletion_blocked == 0),
                    f'blocked={r8a.deletion_blocked}, forced_deleted={len(cli.deleted)}'))

    # 场景9: 更新后旧哈希僵尸清理 → 内容回滚不再「复用」已删文档
    f9 = tmp / 'n9.md'; f9.write_text('v2', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/u.md': 'H_v1'}, content_index={'H_v1': 'D_v1'})
    cli = MockClient({'docs/x/u.md': {'id': 'D_v1', 'size': 2}})
    sync_engine.sync(cli, {'docs/x/u.md': f9}, {'docs/x/u.md': 'H_v2'}, ds, dry_run=False)
    results.append(('场景9 更新 → 删旧文档 + 清旧哈希僵尸',
                    ('D_v1' in cli.deleted) and ('H_v1' not in ds.content_index)
                    and (ds.content_index.get('H_v2') == 'NEW_docs/x/u.md'),
                    f'deleted={cli.deleted}, ci={ds.content_index}'))

    # 场景10: 新增时远程已有同名旧文档（状态丢失）→ 先删旧再传，不堆重复
    f10 = tmp / 'n10.md'; f10.write_text('c10', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/other.md': 'H_o'}, content_index={'H_o': 'D_o'})
    cli = MockClient({'docs/x/other.md': {'id': 'D_o', 'size': 1},
                      'docs/x/a.md': {'id': 'D_stale', 'size': 3}})
    f10b = tmp / 'n10b.md'; f10b.write_text('other', encoding='utf-8')
    sync_engine.sync(cli, {'docs/x/other.md': f10b, 'docs/x/a.md': f10},
                     {'docs/x/other.md': 'H_o', 'docs/x/a.md': 'H_a'}, ds, dry_run=False)
    results.append(('场景10 新增遇远程同名旧文档 → 先删再传',
                    ('D_stale' in cli.deleted) and ('docs/x/a.md' in cli.uploaded),
                    f'deleted={cli.deleted}, uploaded={cli.uploaded}'))

    # 场景11: 解析失败仍落状态 → 第二次同步不重传（不堆重复文档）
    f11 = tmp / 'n11.md'; f11.write_text('c11', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/other.md': 'H_o'}, content_index={'H_o': 'D_o'})
    cli = MockClient({'docs/x/other.md': {'id': 'D_o', 'size': 1}}, parse_fails=True)
    f11b = tmp / 'n11b.md'; f11b.write_text('other', encoding='utf-8')
    files11 = {'docs/x/other.md': f11b, 'docs/x/p.md': f11}
    hashes11 = {'docs/x/other.md': 'H_o', 'docs/x/p.md': 'H_p'}
    r11a = sync_engine.sync(cli, files11, hashes11, ds, dry_run=False)
    first_upload = list(cli.uploaded)
    cli2 = MockClient({'docs/x/other.md': {'id': 'D_o', 'size': 1},
                       'docs/x/p.md': {'id': 'NEW_docs/x/p.md', 'size': 3}}, parse_fails=True)
    sync_engine.sync(cli2, files11, hashes11, ds, dry_run=False)
    results.append(('场景11 解析失败 → 状态已落，二次同步不重传',
                    (first_upload == ['docs/x/p.md']) and (r11a.failed == 1)
                    and (cli2.uploaded == []),
                    f'first={first_upload}, failed={r11a.failed}, second={cli2.uploaded}'))

    # 场景12: 跨库哈希隔离 → 别的库文件的哈希（不在本库子集）不参与本库删除保护
    f12 = tmp / 'n12.md'; f12.write_text('c12', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/mine.md': 'H_m'},
                    content_index={'H_m': 'D_m', 'H_alien': 'D_alien'})
    cli = MockClient({'docs/x/mine.md': {'id': 'D_m', 'size': 3},
                      'docs/x/alien.md': {'id': 'D_alien', 'size': 7}})
    # local_hashes 混入了不属于本库 local_files 的 'docs/other_lib/alien.md'（模拟旧代码全量传参）
    sync_engine.sync(cli, {'docs/x/mine.md': f12},
                     {'docs/x/mine.md': 'H_m', 'docs/other_lib/alien.md': 'H_alien'},
                     ds, dry_run=False)
    results.append(('场景12 跨库哈希隔离 → 不误保护他库内容',
                    'D_alien' in cli.deleted,
                    f'deleted={cli.deleted}'))

    # 场景13: classify_files → 空规则不崩；default_rule 兜底；无兜底进 unmatched
    c13a, u13a = sync_engine.classify_files({'docs/a.md': Path('a')}, {})
    c13b, u13b = sync_engine.classify_files(
        {'docs/tech/t.md': Path('t'), 'docs/misc/m.md': Path('m')},
        {'tech': ['docs/tech'], 'planning': ['docs/planning']},
        default_rule='planning')
    c13c, u13c = sync_engine.classify_files(
        {'docs/misc/m.md': Path('m')},
        {'tech': ['docs/tech']})
    results.append(('场景13 classify_files 空规则/兜底/未匹配',
                    (u13a == {'docs/a.md': Path('a')})
                    and ('docs/misc/m.md' in c13b['planning']) and ('docs/tech/t.md' in c13b['tech'])
                    and (not u13b)
                    and ('docs/misc/m.md' in u13c),
                    f'u13a={list(u13a)}, c13b_planning={list(c13b["planning"])}, u13c={list(u13c)}'))

    # 场景14: v2 → v3 迁移 → 按归属函数分仓；孤儿哈希丢弃；roundtrip 保存/加载
    state_file = tmp / 'mig.json'
    v2 = {'version': 2,
          'path_index': {'docs/tech/a.md': 'H_a', 'docs/misc/b.md': 'H_b', 'docs/skip/c.md': 'H_c'},
          'content_index': {'H_a': 'D_a', 'H_b': 'D_b', 'H_orphan': 'D_orphan', 'H_c': None}}
    state_file.write_text(json.dumps(v2), encoding='utf-8')
    st = SyncState(state_file)
    st.load()

    def assign(path):
        p = path.replace('\\', '/')
        if p.startswith('docs/tech/'):
            return 'DS_TECH'
        if p.startswith('docs/misc/'):
            return 'DS_PLAN'
        return None  # docs/skip 无法归属 → 丢弃

    needs = st.needs_migration()
    migrated, dropped = st.migrate_legacy(assign)
    st.save()
    st2 = SyncState(state_file)
    st2.load()
    tech = st2.for_dataset('DS_TECH')
    plan = st2.for_dataset('DS_PLAN')
    results.append(('场景14 v2→v3 迁移分仓 + 孤儿丢弃 + roundtrip',
                    needs and (migrated, dropped) == (2, 1)
                    and tech.get_hash('docs/tech/a.md') == 'H_a'
                    and tech.get_doc_id_by_hash('H_a') == 'D_a'
                    and plan.get_hash('docs/misc/b.md') == 'H_b'
                    and plan.get_doc_id_by_hash('H_b') == 'D_b'
                    and tech.get_doc_id_by_hash('H_orphan') is None
                    and plan.get_doc_id_by_hash('H_orphan') is None,
                    f'migrated={migrated}, dropped={dropped}, '
                    f'tech={st2.datasets.get("DS_TECH")}, plan={st2.datasets.get("DS_PLAN")}'))

    # 场景15: 状态记为已同步，但远程文档已被删除（控制台手动删/解析失败被清理）→ 补传而非跳过
    f15 = tmp / 'n15.md'; f15.write_text('c15', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/lost.md': 'H_lost'}, content_index={'H_lost': 'D_lost'})
    cli = MockClient({})  # 远程空：D_lost 已经不在了
    r15 = sync_engine.sync(cli, {'docs/x/lost.md': f15}, {'docs/x/lost.md': 'H_lost'}, ds,
                           dry_run=False, allow_cold_start=True)
    results.append(('场景15 远程文档已消失 → 补传(不跳过)',
                    ('docs/x/lost.md' in cli.uploaded) and (r15.skipped == 0)
                    and (ds.content_index.get('H_lost') == 'NEW_docs/x/lost.md'),
                    f'uploaded={cli.uploaded}, skipped={r15.skipped}, ci={ds.content_index}'))

    # 场景16: 路径变更 + 原 doc_id 已失效 → 不能「复用」死文档，必须重新上传
    f16 = tmp / 'n16.md'; f16.write_text('c16', encoding='utf-8')
    _, ds = _new_ds(tmp, path_index={'docs/x/old16.md': 'H_16'}, content_index={'H_16': 'D_dead'})
    cli = MockClient({'docs/x/keep16.md': {'id': 'D_other', 'size': 4}})  # D_dead 不在远程
    r16 = sync_engine.sync(cli, {'docs/x/new16.md': f16}, {'docs/x/new16.md': 'H_16'}, ds,
                           dry_run=False, force_delete=True)
    results.append(('场景16 复用目标已失效 → 重传(不复用死文档)',
                    ('docs/x/new16.md' in cli.uploaded) and (r16.moved == 0)
                    and (ds.content_index.get('H_16') == 'NEW_docs/x/new16.md'),
                    f'uploaded={cli.uploaded}, moved={r16.moved}, ci={ds.content_index}'))

    print('\n===== 测试结果 =====')
    all_ok = True
    for name, ok, detail in results:
        print(f'[{"PASS" if ok else "FAIL"}] {name}')
        if not ok:
            print(f'       {detail}')
            all_ok = False
    print('\n' + ('>>> ALL PASS' if all_ok else '>>> SOME FAILED'))
    return all_ok


if __name__ == '__main__':
    sys.exit(0 if run_tests() else 1)
