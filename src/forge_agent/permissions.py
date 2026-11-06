
from deepagents.middleware.filesystem import FilesystemPermission # type: ignore

# First-match-wins: deny repository writes before allowing repository reads.
REPOSITORY_PERMISSIONS = [
    FilesystemPermission(
        operations=["write"],
        paths=["/repo/**"],
        mode="deny",
    ),
    FilesystemPermission(
        operations=["read"],
        paths=["/repo/**"],
        mode="allow",
    ),
]

WORKSPACE_PERMISSIONS = [
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/workspace/**"],
        mode="allow",
    ),
]

AGENT_PERMISSIONS = [
    *REPOSITORY_PERMISSIONS,
    *WORKSPACE_PERMISSIONS,
]
