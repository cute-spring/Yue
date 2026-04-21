import os
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional


def _realpath(path: str) -> str:
    return os.path.realpath(os.path.abspath(path))


def _is_under(root: str, path: str) -> bool:
    root_real = _realpath(root)
    path_real = _realpath(path)
    try:
        return os.path.commonpath([root_real, path_real]) == root_real
    except ValueError:
        return False


def _dedupe_roots(roots: Iterable[str]) -> List[str]:
    unique = sorted(set(roots), key=lambda item: (len(item), item))
    out: List[str] = []
    for root in unique:
        if any(_is_under(existing, root) for existing in out):
            continue
        out.append(root)
    return out


@dataclass(frozen=True)
class DocAccessPolicy:
    allow_roots: List[str]
    deny_roots: List[str]


class DocAccessPolicyResolver:
    @staticmethod
    def normalize_path(path: str, *, project_root: Optional[str] = None) -> str:
        if not os.path.isabs(path):
            base = project_root or os.getcwd()
            path = os.path.join(base, path)
        return _realpath(path)

    @classmethod
    def normalize_roots(
        cls,
        roots: Optional[Iterable[str]],
        *,
        project_root: Optional[str] = None,
    ) -> List[str]:
        normalized: List[str] = []
        if not roots:
            return normalized
        for root in roots:
            if not isinstance(root, str) or not root.strip():
                continue
            normalized.append(cls.normalize_path(root, project_root=project_root))
        return _dedupe_roots(normalized)

    @classmethod
    def intersect_allow_roots(
        cls,
        upper_allow_roots: Optional[Iterable[str]],
        lower_allow_roots: Optional[Iterable[str]],
        *,
        project_root: Optional[str] = None,
    ) -> List[str]:
        upper = cls.normalize_roots(upper_allow_roots, project_root=project_root)
        lower = cls.normalize_roots(lower_allow_roots, project_root=project_root)
        if not upper or not lower:
            return []

        intersections: List[str] = []
        for upper_root in upper:
            for lower_root in lower:
                if _is_under(upper_root, lower_root):
                    intersections.append(lower_root)
                elif _is_under(lower_root, upper_root):
                    intersections.append(upper_root)
        return _dedupe_roots(intersections)

    @classmethod
    def merge_deny_roots(
        cls,
        *deny_root_groups: Optional[Iterable[str]],
        project_root: Optional[str] = None,
    ) -> List[str]:
        merged: List[str] = []
        for group in deny_root_groups:
            merged.extend(cls.normalize_roots(group, project_root=project_root))
        return _dedupe_roots(merged)

    @classmethod
    def build_policy(
        cls,
        *,
        base_allow_roots: Optional[Iterable[str]],
        base_deny_roots: Optional[Iterable[str]] = None,
        restrict_allow_roots: Optional[Iterable[str]] = None,
        restrict_deny_roots: Optional[Iterable[str]] = None,
        project_root: Optional[str] = None,
    ) -> DocAccessPolicy:
        base_allow = cls.normalize_roots(base_allow_roots, project_root=project_root)
        restrict_allow = cls.normalize_roots(restrict_allow_roots, project_root=project_root)

        if restrict_allow:
            allow_roots = cls.intersect_allow_roots(base_allow, restrict_allow, project_root=project_root)
        else:
            allow_roots = base_allow

        deny_roots = cls.merge_deny_roots(
            base_deny_roots,
            restrict_deny_roots,
            project_root=project_root,
        )
        return DocAccessPolicy(allow_roots=allow_roots, deny_roots=deny_roots)

    @classmethod
    def explain(
        cls,
        path: str,
        *,
        policy: DocAccessPolicy,
        project_root: Optional[str] = None,
    ) -> dict[str, Any]:
        candidate = cls.normalize_path(path, project_root=project_root)
        matched_allow = [root for root in policy.allow_roots if _is_under(root, candidate)]
        matched_deny = [root for root in policy.deny_roots if _is_under(root, candidate)]

        if not matched_allow:
            allowed = False
            reason = "outside_allow"
        elif matched_deny:
            allowed = False
            reason = "hit_deny"
        else:
            allowed = True
            reason = "allowed"

        return {
            "requested_path": path,
            "normalized_path": candidate,
            "allow_roots": list(policy.allow_roots),
            "deny_roots": list(policy.deny_roots),
            "matched_allow_roots": matched_allow,
            "matched_deny_roots": matched_deny,
            "allowed": allowed,
            "reason": reason,
        }

    @classmethod
    def is_allowed(
        cls,
        path: str,
        *,
        policy: DocAccessPolicy,
        project_root: Optional[str] = None,
    ) -> bool:
        return bool(cls.explain(path, policy=policy, project_root=project_root)["allowed"])
