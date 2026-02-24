"""
Skill 热加载模块 - 监听 skill 目录变化并清除缓存。
"""
import os
import time
from typing import Dict, Optional
from watchfiles import awatch

from app.core.config import settings
from app.core.terminal_ui import ui


class SkillWatcher:
    """Skill 目录文件变化监听器"""

    def __init__(self):
        self._last_modified: Dict[str, float] = {}
        self._watching = False
        self._watch_tasks: Dict[str, any] = {}

    def get_skill_dirs(self, project_path: Optional[str] = None) -> list:
        """获取所有 skill 目录"""
        add_dirs = []

        # Global skills directory
        global_skills_dir = os.path.join(settings.project_root, "extensions", "skills")
        if os.path.exists(global_skills_dir):
            add_dirs.append(global_skills_dir)

        # Project-level skills directory
        if project_path:
            project_skills_dir = os.path.join(project_path, ".claude", "skills")
            if os.path.exists(project_skills_dir):
                add_dirs.append(project_skills_dir)

        return add_dirs

    async def check_changes(self, project_path: Optional[str] = None) -> bool:
        """检查 skill 目录是否有变化

        Returns:
            True if changes detected, False otherwise
        """
        skill_dirs = self.get_skill_dirs(project_path)
        has_changes = False

        for skill_dir in skill_dirs:
            if not os.path.exists(skill_dir):
                continue

            try:
                for file_path in os.listdir(skill_dir):
                    full_path = os.path.join(skill_dir, file_path)
                    if os.path.isfile(full_path):
                        mtime = os.path.getmtime(full_path)
                        key = f"{skill_dir}:{file_path}"

                        if key not in self._last_modified:
                            # 新文件
                            ui.info(f"New skill file detected: {file_path}", "SkillWatcher")
                            self._last_modified[key] = mtime
                            has_changes = True
                        elif self._last_modified[key] < mtime:
                            # 文件被修改
                            ui.info(f"Skill file modified: {file_path}", "SkillWatcher")
                            self._last_modified[key] = mtime
                            has_changes = True
            except Exception as e:
                ui.debug(f"Error checking skill dir {skill_dir}: {e}", "SkillWatcher")

        return has_changes

    def reset(self):
        """重置监听状态"""
        self._last_modified.clear()
        ui.info("Skill cache reset", "SkillWatcher")


# 全局实例
_skill_watcher: Optional[SkillWatcher] = None


def get_skill_watcher() -> SkillWatcher:
    """获取全局 SkillWatcher 实例"""
    global _skill_watcher
    if _skill_watcher is None:
        _skill_watcher = SkillWatcher()
    return _skill_watcher
