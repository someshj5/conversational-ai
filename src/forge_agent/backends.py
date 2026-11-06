
from pathlib import Path

from deepagents.backends import (
    CompositeBackend,
    FilesystemBackend,
    StateBackend,
)

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = ROOT / "forge-agent-code"
SKILLS_ROOT = (
    ROOT.parent.parent
    / "antigravity_test"
    / "skills"
)


def create_backend(repository_root: Path) -> CompositeBackend:
    repository_root = Path(repository_root).resolve()

    if not repository_root.is_dir():
        raise NotADirectoryError(
            f"Repository directory not found: {repository_root}"
        )

    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

    if not SKILLS_ROOT.is_dir():
        raise FileNotFoundError(
            f"Skills directory not found: {SKILLS_ROOT}"
        )

    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/repo/": FilesystemBackend(
                root_dir=repository_root,
                virtual_mode=True,
            ),
            "/workspace/": FilesystemBackend(
                root_dir=WORKSPACE_ROOT,
                virtual_mode=True,
            ),
            "/skills/": FilesystemBackend(
                root_dir=SKILLS_ROOT,
                virtual_mode=True,
            ),
        },
    )
