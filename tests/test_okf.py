import pytest
import os
import tempfile
import shutil

from app.core.okf_validator import OKFValidator


class TestOKFValidator:
    def setup_method(self):
        self.validator = OKFValidator()
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_valid_concept_file(self):
        path = os.path.join(self.tmpdir, "test-concept.md")
        content = """---
type: policy
title: Test Policy
tags: ["test"]
---

# Test Policy

This is a test policy.
"""
        with open(path, "w") as f:
            f.write(content)

        result = self.validator.validate_file(path, "test-concept.md")
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_missing_frontmatter(self):
        path = os.path.join(self.tmpdir, "bad.md")
        content = "# No Frontmatter\n\nJust text."
        with open(path, "w") as f:
            f.write(content)

        result = self.validator.validate_file(path, "bad.md")
        assert not result.is_valid
        assert any("missing YAML frontmatter" in e for e in result.errors)

    def test_missing_type_field(self):
        path = os.path.join(self.tmpdir, "no-type.md")
        content = """---
title: No Type
tags: ["test"]
---

Body text.
"""
        with open(path, "w") as f:
            f.write(content)

        result = self.validator.validate_file(path, "no-type.md")
        assert not result.is_valid
        assert any("missing required frontmatter field 'type'" in e for e in result.errors)

    def test_rejects_wiki_links(self):
        path = os.path.join(self.tmpdir, "wiki-links.md")
        content = """---
type: policy
title: Wiki Links
---

# Bad

This uses [[forbidden wiki syntax]] instead of [proper links](./proper.md).
"""
        with open(path, "w") as f:
            f.write(content)

        result = self.validator.validate_file(path, "wiki-links.md")
        assert not result.is_valid
        assert any("wiki-style" in e for e in result.errors)

    def test_accepts_standard_md_links(self):
        path = os.path.join(self.tmpdir, "good-links.md")
        content = """---
type: reference
title: Good Links
---

# Links

See [Policy](../hr/policy.md) and [External](https://example.com).
"""
        with open(path, "w") as f:
            f.write(content)

        result = self.validator.validate_file(path, "good-links.md")
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_validate_bundle_missing_reserved(self):
        result = self.validator.validate_bundle(self.tmpdir)
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any("missing index.md" in w for w in result.warnings)
        assert any("missing log.md" in w for w in result.warnings)

    def test_validate_bundle_full(self):
        for fn in ("index.md", "log.md"):
            content = f"---\ntype: reserved\n---\n# {fn}"
            with open(os.path.join(self.tmpdir, fn), "w") as f:
                f.write(content)

        result = self.validator.validate_bundle(self.tmpdir)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"
