import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.doc_retrieval import resolve_docs_root_for_read


def test_policy_allow_intersection_prefers_effective_overlap():
    from app.services.doc_access_policy import DocAccessPolicyResolver

    with tempfile.TemporaryDirectory() as tmp:
        allow_docs = os.path.join(tmp, "allow", "docs")
        allow_shared = os.path.join(tmp, "allow", "shared")
        restrict_docs_sub = os.path.join(tmp, "allow", "docs", "sub")
        os.makedirs(restrict_docs_sub, exist_ok=True)
        os.makedirs(allow_shared, exist_ok=True)

        policy = DocAccessPolicyResolver.build_policy(
            base_allow_roots=[allow_docs, allow_shared],
            base_deny_roots=[],
            restrict_allow_roots=[restrict_docs_sub, os.path.join(tmp, "other")],
            restrict_deny_roots=[],
            project_root=tmp,
        )

        assert policy.allow_roots == [os.path.realpath(restrict_docs_sub)]


def test_policy_deny_has_priority_over_allow():
    from app.services.doc_access_policy import DocAccessPolicyResolver

    with tempfile.TemporaryDirectory() as tmp:
        docs_root = os.path.join(tmp, "docs")
        private_root = os.path.join(docs_root, "private")
        os.makedirs(private_root, exist_ok=True)
        target = os.path.join(private_root, "note.md")
        with open(target, "w", encoding="utf-8") as f:
            f.write("secret")

        policy = DocAccessPolicyResolver.build_policy(
            base_allow_roots=[docs_root],
            base_deny_roots=[private_root],
            project_root=tmp,
        )
        explain = DocAccessPolicyResolver.explain(target, policy=policy, project_root=tmp)

        assert explain["allowed"] is False
        assert explain["reason"] == "hit_deny"


def test_policy_symlink_escape_is_blocked():
    from app.services.doc_access_policy import DocAccessPolicyResolver

    with tempfile.TemporaryDirectory() as tmp:
        docs_root = os.path.join(tmp, "docs")
        outside_root = os.path.join(tmp, "outside")
        os.makedirs(docs_root, exist_ok=True)
        os.makedirs(outside_root, exist_ok=True)

        link_path = os.path.join(docs_root, "escape")
        try:
            os.symlink(outside_root, link_path)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink not supported in this environment")

        target = os.path.join(link_path, "secrets.md")
        with open(os.path.join(outside_root, "secrets.md"), "w", encoding="utf-8") as f:
            f.write("outside")

        policy = DocAccessPolicyResolver.build_policy(
            base_allow_roots=[docs_root],
            base_deny_roots=[],
            project_root=tmp,
        )
        explain = DocAccessPolicyResolver.explain(target, policy=policy, project_root=tmp)

        assert explain["allowed"] is False
        assert explain["reason"] == "outside_allow"


def test_global_allow_roots_are_authoritative_over_agent_doc_roots():
    with tempfile.TemporaryDirectory() as tmp:
        allowed_root = os.path.join(tmp, "allowed")
        restricted_root = os.path.join(allowed_root, "restricted")
        bypass_root = os.path.join(allowed_root, "bypass")
        os.makedirs(restricted_root, exist_ok=True)
        os.makedirs(bypass_root, exist_ok=True)

        bypass_file = os.path.join(bypass_root, "note.md")
        with open(bypass_file, "w", encoding="utf-8") as f:
            f.write("blocked")

        explicit_root = resolve_docs_root_for_read(
            "note.md",
            requested_root=bypass_root,
            doc_roots=[restricted_root],
            allow_roots=[allowed_root],
        )
        implicit_root = resolve_docs_root_for_read(
            bypass_file,
            requested_root=None,
            doc_roots=[restricted_root],
            allow_roots=[allowed_root],
        )

        assert explicit_root == os.path.realpath(bypass_root)
        assert implicit_root == os.path.realpath(allowed_root)
