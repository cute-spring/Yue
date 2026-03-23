import os
from pathlib import Path
from typing import List, Optional

from app.services.skills.models import SkillDirectorySpec


SKILL_LAYER_PRIORITY = {
    "builtin": 0,
    "workspace": 1,
    "user": 2,
}


class SkillDirectoryResolver:
    def __init__(
        self,
        builtin_dir: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        user_dir: Optional[str] = None,
    ):
        backend_root = Path(__file__).resolve().parents[3]
        workspace_root = Path(__file__).resolve().parents[4]
        resolved_user_dir = user_dir or os.getenv("YUE_USER_SKILLS_DIR") or str(Path.home() / ".yue" / "skills")
        self.builtin_dir = str(Path(builtin_dir or (backend_root / "data" / "skills")).resolve())
        self.workspace_dir = str(Path(workspace_dir or (workspace_root / "data" / "skills")).resolve())
        self.user_dir = str(Path(resolved_user_dir).expanduser().resolve())

    def resolve(self) -> List[SkillDirectorySpec]:
        return [
            SkillDirectorySpec(layer="builtin", path=self.builtin_dir),
            SkillDirectorySpec(layer="workspace", path=self.workspace_dir),
            SkillDirectorySpec(layer="user", path=self.user_dir),
        ]
