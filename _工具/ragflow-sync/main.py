#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAGFlow 文档同步 CLI 入口"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 设置控制台编码为 UTF-8（Windows）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加脚本所在目录到路径，以便导入同目录模块
script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

from dotenv import load_dotenv
from ragflow_client import RagflowClient
from file_scanner import scan_directory, compute_file_hashes
from sync_state import SyncState
from sync_engine import (
    sync, sync_multi_dataset, classify_files, init_content_index
)


def _resolve_dataset_id(rule_name: str) -> str:
    """按规则名解析对应的 dataset_id 环境变量：{规则名大写}_DATASET_ID"""
    return (os.getenv(f'{rule_name.upper()}_DATASET_ID', '')
            or os.getenv(f'{rule_name}_DATASET_ID', ''))


def load_config(script_dir: Path) -> dict:
    """加载 .env 配置文件

    知识库列表完全由 DATASET_RULES 驱动：规则里出现什么名字，
    就去找 {名字大写}_DATASET_ID —— 不存在写死的库名，加新库只改配置。
    """
    env_path = script_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f'✓ 加载配置: .env')
    else:
        print(f'⚠ 未找到 .env 文件，使用环境变量')

    config = {
        'api_url': os.getenv('RAGFLOW_API_URL', 'http://192.168.50.242'),
        'api_key': os.getenv('RAGFLOW_API_KEY', ''),
        'project_root': os.getenv('PROJECT_ROOT', '../..'),
        'sync_dirs': [d.strip() for d in os.getenv('SYNC_DIRS', 'docs').split(',') if d.strip()],
    }

    # 解析排除规则（逗号分隔）
    raw_excludes = os.getenv('EXCLUDE_PATTERNS', '')
    config['exclude_patterns'] = [p.strip() for p in raw_excludes.split(',') if p.strip()]

    # 分类规则两种模式都解析（单库模式用它做 SYNC_ONLY_RULES 过滤）
    config['dataset_rules'] = _parse_dataset_rules(os.getenv('DATASET_RULES', ''))
    config['default_rule'] = os.getenv('DEFAULT_RULE', '').strip()

    if config['default_rule'] and config['default_rule'] not in config['dataset_rules']:
        print(f'✗ DEFAULT_RULE={config["default_rule"]} 不在 DATASET_RULES 的规则名中: '
              f'{list(config["dataset_rules"].keys())}')
        sys.exit(1)

    multi_dataset_enabled = os.getenv('MULTI_DATASET_ENABLED', 'false').lower() == 'true'

    if multi_dataset_enabled:
        # ---------- 多知识库模式 ----------
        config['multi_dataset'] = True

        if not config['dataset_rules']:
            print('✗ 多知识库模式必须配置 DATASET_RULES，例如：')
            print('    DATASET_RULES=tech=docs/tech|planning=docs/planning')
            sys.exit(1)

        # 按规则名逐个解析 dataset_id；缺失的只警告（该库文件跳过），
        # 全部缺失才报错退出——不存在“某个库必填”的硬编码
        config['dataset_ids'] = {}
        missing = []
        for rule_name in config['dataset_rules']:
            dataset_id = _resolve_dataset_id(rule_name)
            if dataset_id:
                config['dataset_ids'][rule_name] = dataset_id
            else:
                missing.append(rule_name)

        if not config['dataset_ids']:
            print('✗ 未配置任何知识库 ID。请为 DATASET_RULES 中的规则名配置对应变量，例如：')
            for rule_name in config['dataset_rules']:
                print(f'    {rule_name.upper()}_DATASET_ID=...')
            sys.exit(1)

        for rule_name in missing:
            print(f'⚠ 未配置 {rule_name.upper()}_DATASET_ID，规则 "{rule_name}" 的文件将跳过同步')
    else:
        # ---------- 单知识库模式 ----------
        config['multi_dataset'] = False
        config['dataset_id'] = os.getenv('RAGFLOW_DATASET_ID', '')
        config['dataset_ids'] = {}

        if not config['dataset_id']:
            print('✗ 未配置 RAGFLOW_DATASET_ID，请在 .env 文件中设置')
            sys.exit(1)

        # 可选：单库模式也吃分类规则——只同步指定规则匹配的文件
        # 例：SYNC_ONLY_RULES=planning → 只把策划文档同步进这个库
        only_rules = [r.strip() for r in os.getenv('SYNC_ONLY_RULES', '').split(',') if r.strip()]
        config['sync_only_rules'] = only_rules
        if only_rules:
            if not config['dataset_rules']:
                print('✗ 配置了 SYNC_ONLY_RULES 但缺少 DATASET_RULES，无法按规则过滤')
                sys.exit(1)
            unknown = [r for r in only_rules if r not in config['dataset_rules']]
            if unknown:
                print(f'✗ SYNC_ONLY_RULES 中的规则名不存在于 DATASET_RULES: {unknown}')
                sys.exit(1)

    if not config['api_key']:
        print('✗ 未配置 RAGFLOW_API_KEY，请在 .env 文件中设置')
        sys.exit(1)

    return config


def _parse_dataset_rules(rules_str: str) -> Dict[str, list]:
    """
    解析数据集分类规则

    格式：tech=docs/tech|planning=docs/thoth,docs/需求拆解
    返回：{'tech': ['docs/tech'], 'planning': ['docs/thoth', '需求拆解']}
    """
    rules = {}
    if not rules_str:
        return rules

    for rule in rules_str.split('|'):
        rule = rule.strip()
        if '=' not in rule:
            continue
        dataset_name, prefixes = rule.split('=', 1)
        rules[dataset_name.strip()] = [p.strip() for p in prefixes.split(',') if p.strip()]

    return rules


def _make_dataset_assigner(config: dict):
    """构造「相对路径 → dataset_id」的归属函数，用于 v1/v2 旧状态迁移"""
    if not config['multi_dataset']:
        dataset_id = config['dataset_id']
        return lambda path: dataset_id

    rules = config['dataset_rules']
    default_rule = config['default_rule']
    dataset_ids = config['dataset_ids']

    def assign(path: str) -> Optional[str]:
        normalized = path.replace('\\', '/')
        for rule_name, prefixes in rules.items():
            for prefix in prefixes:
                p = prefix.replace('\\', '/')
                if normalized == p or normalized.startswith(p + '/'):
                    return dataset_ids.get(rule_name)
        if default_rule:
            return dataset_ids.get(default_rule)
        return None

    return assign


def main():
    parser = argparse.ArgumentParser(description='将本地文档同步到 RAGFlow 知识库')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览变更（含删除预览），不实际执行'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='输出详细日志'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='重置同步状态（清除本地缓存；重置后需先 --init-index 重建索引）'
    )
    parser.add_argument(
        '--init-index',
        action='store_true',
        help='初始化内容索引（从远程文档建立哈希映射，首次运行/重置后需要）'
    )
    parser.add_argument(
        '--force-delete',
        action='store_true',
        help='放行批量删除保护（待删数量超过阈值时默认拦截）'
    )
    parser.add_argument(
        '--force-cold-start',
        action='store_true',
        help='跳过冷启动保护（本地状态为空但远程有文档时默认拒绝同步）'
    )
    parser.add_argument(
        '--datasets',
        default='',
        help='只同步指定规则名的知识库（逗号分隔，仅多库模式），例：--datasets planning'
    )

    args = parser.parse_args()

    print('=' * 60)
    print('RAGFlow 文档同步工具')
    print('=' * 60)

    # 加载配置
    config = load_config(script_dir)

    only_datasets: Optional[List[str]] = None
    if args.datasets:
        if not config['multi_dataset']:
            print('✗ --datasets 仅在多知识库模式下可用')
            sys.exit(1)
        only_datasets = [d.strip() for d in args.datasets.split(',') if d.strip()]
        unknown = [d for d in only_datasets if d not in config['dataset_rules']]
        if unknown:
            print(f'✗ --datasets 中的规则名不存在于 DATASET_RULES: {unknown}')
            sys.exit(1)

    # 解析项目根目录
    project_root = (script_dir / config['project_root']).resolve()
    if not project_root.exists():
        print(f'✗ 项目根目录不存在: {project_root}')
        sys.exit(1)

    print(f'✓ 项目根目录: {project_root}')
    print(f'✓ 同步目录: {config["sync_dirs"]}')

    if config['multi_dataset']:
        print(f'✓ 多知识库模式: 已启用')
        for rule_name, dataset_id in config['dataset_ids'].items():
            print(f'  - {rule_name}: {dataset_id}')
        print(f'  - 分类规则: {len(config["dataset_rules"])} 条')
        print(f'  - 未匹配兜底: {config["default_rule"] or "无（未匹配文件跳过并警告）"}')
    else:
        print(f'✓ 单知识库模式')
        print(f'  - 知识库 ID: {config["dataset_id"]}')
        if config.get('sync_only_rules'):
            print(f'  - 仅同步规则: {config["sync_only_rules"]}')
    print()

    # 确定状态文件路径（存放在脚本同级目录）
    state_file = script_dir / 'sync_state.json'

    # 加载同步状态
    sync_state = SyncState(state_file)
    if args.reset:
        print('⚠ 重置同步状态...')
        if args.dry_run:
            print('⚠ --reset 与 --dry-run 同用时不落盘，本次重置不会生效')
    else:
        sync_state.load()

    # v1/v2 旧状态迁移到 v3 分仓格式
    if sync_state.needs_migration():
        print('\n→ 迁移旧格式状态到 v3（按知识库分仓）...')
        migrated, dropped = sync_state.migrate_legacy(_make_dataset_assigner(config))
        print(f'  ✓ 迁移 {migrated} 条路径索引' +
              (f'，丢弃 {dropped} 条（无法归属任何知识库）' if dropped else ''))

    # 扫描本地文件
    print('\n→ 扫描本地文件...')
    if config['exclude_patterns']:
        print(f'  排除规则: {config["exclude_patterns"]}')
    local_files = scan_directory(
        base_dir=project_root,
        scan_dirs=config['sync_dirs'],
        exclude_patterns=config['exclude_patterns']
    )
    print(f'  本地文件数量: {len(local_files)}')

    # 单库模式 + SYNC_ONLY_RULES：先按规则过滤
    if not config['multi_dataset'] and config.get('sync_only_rules'):
        classified, unmatched = classify_files(
            local_files, config['dataset_rules'], config['default_rule'])
        filtered: Dict[str, Path] = {}
        for rule_name in config['sync_only_rules']:
            filtered.update(classified.get(rule_name, {}))
        skipped_count = len(local_files) - len(filtered)
        local_files = filtered
        print(f'  按规则 {config["sync_only_rules"]} 过滤后: {len(local_files)} 个文件'
              f'（跳过 {skipped_count} 个）')

    # 计算哈希
    print('→ 计算文件哈希...')
    local_hashes = compute_file_hashes(local_files)
    print(f'  已计算哈希: {len(local_hashes)}')

    # 初始化内容索引（如果需要）
    if args.init_index:
        print('\n' + '=' * 60)
        print('初始化内容索引模式')
        print('=' * 60)

        if config['multi_dataset']:
            # 多知识库模式：为每个已配置的知识库初始化
            classified, unmatched = classify_files(
                local_files, config['dataset_rules'], config['default_rule'])

            for dataset_name, files in classified.items():
                if only_datasets is not None and dataset_name not in only_datasets:
                    continue

                dataset_id = config['dataset_ids'].get(dataset_name, '')
                if not dataset_id:
                    print(f'\n⏭ {dataset_name}: 未配置 dataset_id，跳过')
                    continue

                client = RagflowClient(
                    base_url=config['api_url'],
                    api_key=config['api_key'],
                    dataset_id=dataset_id
                )

                print(f'\n→ 初始化 {dataset_name} 知识库内容索引...')
                count = init_content_index(
                    client=client,
                    local_files=files,
                    local_hashes=local_hashes,
                    dataset_state=sync_state.for_dataset(dataset_id),
                    verbose=args.verbose
                )

                if count > 0:
                    sync_state.save()
        else:
            # 单知识库模式
            client = RagflowClient(
                base_url=config['api_url'],
                api_key=config['api_key'],
                dataset_id=config['dataset_id']
            )

            count = init_content_index(
                client=client,
                local_files=local_files,
                local_hashes=local_hashes,
                dataset_state=sync_state.for_dataset(config['dataset_id']),
                verbose=args.verbose
            )

            if count > 0:
                sync_state.save()

        print('\n' + '=' * 60)
        print('[OK] 内容索引初始化完成')
        print('现在可以运行普通同步，路径变更将被正确识别')
        print('=' * 60)
        sys.exit(0)

    # 执行同步
    if config['multi_dataset']:
        # 多知识库模式
        report = sync_multi_dataset(
            api_url=config['api_url'],
            api_key=config['api_key'],
            local_files=local_files,
            local_hashes=local_hashes,
            sync_state=sync_state,
            dataset_rules=config['dataset_rules'],
            dataset_ids=config['dataset_ids'],
            default_rule=config['default_rule'],
            only_datasets=only_datasets,
            dry_run=args.dry_run,
            verbose=args.verbose,
            force_delete=args.force_delete,
            allow_cold_start=args.force_cold_start
        )
        if report.has_failure():
            sys.exit(1)
    else:
        # 单知识库模式
        client = RagflowClient(
            base_url=config['api_url'],
            api_key=config['api_key'],
            dataset_id=config['dataset_id']
        )
        report = sync(
            client=client,
            local_files=local_files,
            local_hashes=local_hashes,
            dataset_state=sync_state.for_dataset(config['dataset_id']),
            dry_run=args.dry_run,
            verbose=args.verbose,
            force_delete=args.force_delete,
            allow_cold_start=args.force_cold_start
        )
        if not args.dry_run:
            sync_state.save()
        if report.failed > 0 or report.aborted or report.deletion_blocked > 0:
            sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
