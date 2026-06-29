import pytest
import os
import tempfile
import shutil

from app.storage.bundle import BundleManager, BundleError
from app.models.okf import OKFConcept, OKFFrontmatter


class TestBundleManager:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace_id = "test-ws"
        self.bundle = BundleManager(self.tmpdir, self.workspace_id)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_reserved_files(self):
        assert self.bundle.workspace_path.exists()
        index_path = self.bundle.workspace_path / "index.md"
        log_path = self.bundle.workspace_path / "log.md"
        assert index_path.exists()
        assert log_path.exists()

    def test_write_and_read_concept(self):
        concept = OKFConcept(
            filepath="hr/test-policy.md",
            frontmatter=OKFFrontmatter(
                type="policy",
                title="Test Policy",
                tags=["test", "policy"],
            ),
            body="# Test Policy\n\nThis is a test."
        )
        written = self.bundle.write_concept(concept)
        assert written.exists()

        read_back = self.bundle.read_concept("hr/test-policy.md")
        assert read_back.frontmatter.title == "Test Policy"
        assert read_back.frontmatter.type == "policy"
        assert read_back.body == "# Test Policy\n\nThis is a test."

    def test_read_nonexistent_concept(self):
        with pytest.raises(BundleError):
            self.bundle.read_concept("nonexistent.md")

    def test_delete_concept(self):
        concept = OKFConcept(
            filepath="delete-me.md",
            frontmatter=OKFFrontmatter(type="test"),
            body="# Delete test"
        )
        self.bundle.write_concept(concept)
        self.bundle.delete_concept("delete-me.md")
        assert not (self.bundle.workspace_path / "delete-me.md").exists()

    def test_list_concepts(self):
        for i in range(3):
            concept = OKFConcept(
                filepath=f"section/file-{i}.md",
                frontmatter=OKFFrontmatter(type="test", title=f"File {i}"),
                body=f"# File {i}"
            )
            self.bundle.write_concept(concept)

        concepts = self.bundle.list_concepts()
        assert len(concepts) == 3

    def test_path_traversal_blocked(self):
        with pytest.raises(BundleError):
            self.bundle.resolve_path("../../../etc/passwd")

    def test_validate_bundle(self):
        concept = OKFConcept(
            filepath="valid-concept.md",
            frontmatter=OKFFrontmatter(type="policy", title="Valid"),
            body="# Valid\n\nOKF compliant."
        )
        self.bundle.write_concept(concept)
        is_valid, errors, warnings = self.bundle.validate()
        assert is_valid, f"Expected valid, got errors: {errors}"

    def test_resolve_links(self):
        concept = OKFConcept(
            filepath="base/doc.md",
            frontmatter=OKFFrontmatter(type="test"),
            body="See [Policy](../hr/policy.md) and [External](https://example.com)."
        )
        self.bundle.write_concept(concept)
        links = self.bundle.resolve_links("base/doc.md")
        assert "hr/policy.md" in links
        assert "https://example.com" in links

    def test_concept_source_hash(self):
        concept = OKFConcept(
            filepath="hash-test.md",
            frontmatter=OKFFrontmatter(type="test", title="Hash Test"),
            body="# Hashed"
        )
        self.bundle.write_concept(concept)

        read_concept = self.bundle.read_concept("hash-test.md")
        assert read_concept.frontmatter.source_hash is not None
        assert len(read_concept.frontmatter.source_hash) == 12

    def test_export_bundle(self):
        concept = OKFConcept(
            filepath="export-test.md",
            frontmatter=OKFFrontmatter(type="test"),
            body="# Export"
        )
        self.bundle.write_concept(concept)

        export_dir = tempfile.mkdtemp()
        exported_path = self.bundle.export_bundle(export_dir)
        assert os.path.isdir(exported_path)
        assert os.path.exists(os.path.join(exported_path, "export-test.md"))
        shutil.rmtree(export_dir)
