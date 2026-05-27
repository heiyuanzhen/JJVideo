# -*- coding: utf-8 -*-
"""
初始化测试数据脚本
为数据库添加示例项目和素材
"""

import os
import sys
import sqlite3
from datetime import datetime
from backend.database.db_manager import DatabaseManager


def init_database():
    """初始化数据库（使用统一的 AIJian 数据库结构）"""
    print("\n[初始化] 正在创建数据库并同步表结构...")

    # 使用 DatabaseManager 统一管理数据库路径与表结构
    db_manager = DatabaseManager()
    db_path = db_manager.db_path

    print(f"   [信息] 使用数据库文件: {db_path}")
    print("   [完成] 基本表结构已由 DatabaseManager 初始化")

    return db_manager


def insert_sample_projects(db_manager):
    """插入示例项目（基于新的 projects 表结构）"""
    print("\n[插入] 示例项目数据...")

    # 使用服务层接口检查是否已有项目
    existing_projects = db_manager.get_all_projects()
    if existing_projects:
        print(f"   [跳过] 已存在 {len(existing_projects)} 个项目，跳过插入")
        return existing_projects

    # 示例项目数据（适配 commentaty/audio/mixed 三种类型）
    sample_projects = [
        {
            'name': '示例原创解说项目',
            'type': 'commentary',
            'description': '用于展示 AIJian 原创解说流程的示例项目',
            'template': 'commentary',
        },
        {
            'name': '示例AI配音项目',
            'type': 'audio',
            'description': '用于展示 AI 配音与音频导出的示例项目',
            'template': 'voiceover',
        },
        {
            'name': '示例混剪项目',
            'type': 'mixed',
            'description': '用于展示混剪与 BGM 叠加流程的示例项目',
            'template': 'remix',
        },
    ]

    created_projects = []
    for spec in sample_projects:
        project = db_manager.create_project(
            name=spec['name'],
            project_type=spec['type'],
            description=spec['description'],
            template=spec['template'],
        )
        created_projects.append(project)

    print(f"   [完成] 插入了 {len(created_projects)} 个示例项目")
    return created_projects


def insert_sample_materials(db_manager, projects):
    """插入示例素材（基于新的 materials 表结构）"""
    print("\n[插入] 示例素材数据...")

    # 检查是否已有素材
    existing_materials = db_manager.get_materials()
    if existing_materials:
        print(f"   [跳过] 已存在 {len(existing_materials)} 个素材，跳过插入")
        return

    if not projects:
        print("   [提示] 当前没有可用项目，跳过素材初始化")
        return

    # 简单起见，将示例素材全部挂在第一个示例项目下
    target_project_id = projects[0]['id']

    # 示例素材数据
    materials = [
        {
            'name': '示例视频素材1.mp4',
            'type': 'video',
            'path': '/uploads/materials/video1.mp4',
            'size': 10485760,
            'duration': 60,
            'metadata': {
                'thumbnail': '/static/img/mat_thumb1.jpg',
                'tags': '风景,自然',
            },
        },
        {
            'name': '示例音频素材1.mp3',
            'type': 'audio',
            'path': '/uploads/materials/audio1.mp3',
            'size': 2097152,
            'duration': 180,
            'metadata': {
                'thumbnail': None,
                'tags': '背景音乐,轻音乐',
            },
        },
        {
            'name': '示例图片素材1.jpg',
            'type': 'image',
            'path': '/uploads/materials/image1.jpg',
            'size': 524288,
            'duration': None,
            'metadata': {
                'thumbnail': '/uploads/materials/image1.jpg',
                'tags': '背景,纹理',
            },
        },
        {
            'name': '示例视频素材2.mp4',
            'type': 'video',
            'path': '/uploads/materials/video2.mp4',
            'size': 15728640,
            'duration': 90,
            'metadata': {
                'thumbnail': '/static/img/mat_thumb2.jpg',
                'tags': '人物,运动',
            },
        },
    ]

    for mat in materials:
        db_manager.create_material(
            project_id=target_project_id,
            material_type=mat['type'],
            name=mat['name'],
            path=mat['path'],
            size=mat['size'],
            duration=mat['duration'] or 0,
            metadata=mat['metadata'],
        )

    print(f"   [完成] 插入了 {len(materials)} 个示例素材")

def main():
    """主函数"""
    print("=" * 60)
    print("  AIJian - 初始化测试数据")
    print("=" * 60)
    
    try:
        # 初始化数据库（使用统一的 DatabaseManager + jjyb_ai.db）
        db_manager = init_database()

        # 插入示例数据
        projects = insert_sample_projects(db_manager)
        insert_sample_materials(db_manager, projects)
        
        print("\n" + "=" * 60)
        print("  [成功] 测试数据初始化完成！")
        print("=" * 60)
        print("\n  现在可以启动应用:")
        print("  python frontend/app.py")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n[错误] 初始化失败: {str(e)}")
        return 1
        
    finally:
        # DatabaseManager 会在每次操作后管理自身连接，这里无需额外关闭
        pass


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
