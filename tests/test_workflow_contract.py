"""Documentation/routing structure checks; not a live-agent or engineering test."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins/chemical-engineering-skills/skills"
STAGE_SKILLS = {
    "chemical-engineering-expert", "aspen-document-driven-flowsheet",
    "aspen-adaptive-generalization-loop", "aspen-edr-rating-delivery",
    "aspen-flowsheet-error-repair", "aspen-heat-pump-distillation-replacement",
    "aspen-plus-operations", "aspen-pressure-pfd-delivery",
    "aspen-tower-optimization-workflow", "aspen-two-section-flowsheet",
    "chemical-equipment-selection-audit", "chemical-tower-design",
    "equipment-design-app",
}

def introduction(path):
    text = path.read_text(encoding="utf-8")
    return text.split("## 工作过程\n", 1)[1].split("\n## ", 1)[0].strip()

class WorkflowContract(unittest.TestCase):
    def test_all_professional_entries_explain_a_connected_workflow(self):
        entries = sorted(SKILLS.glob("*/SKILL.md"))
        self.assertEqual(len(entries), 19)
        for entry in entries:
            with self.subTest(skill=entry.parent.name):
                body = introduction(entry)
                paragraphs = [p for p in body.split("\n\n") if p.strip()]
                self.assertGreaterEqual(len(paragraphs), 2)
                self.assertGreaterEqual(len(re.findall(r"[\u4e00-\u9fff]", body)), 100)
                self.assertFalse(any(p.startswith(("- ", "1. ", "|")) for p in paragraphs))

    def test_process_consumers_link_one_stage_owner(self):
        owner = SKILLS / "chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md"
        for name in STAGE_SKILLS:
            entry = SKILLS / name / "SKILL.md"
            links = re.findall(r"\]\(([^)]+DESIGN_STAGE_ROUTING\.md)\)", introduction(entry))
            self.assertEqual(len(links), 1, name)
            self.assertEqual((entry.parent / links[0]).resolve(), owner.resolve())
        self.assertNotIn("DESIGN_STAGE_ROUTING", introduction(SKILLS / "aspen-plus-template/SKILL.md"))

    def test_new_introduction_links_and_reader_document_links_exist(self):
        documents = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
        for entry in SKILLS.glob("*/SKILL.md"):
            documents.append(entry)
        for document in documents:
            body = introduction(document) if document.name == "SKILL.md" else document.read_text(encoding="utf-8")
            body = re.sub(r"```.*?```", "", body, flags=re.S)
            for link in re.findall(r"\]\(([^)\n]+)\)", body):
                if link.startswith(("https://", "http://", "#")):
                    continue
                target = unquote(link.strip("<>").split("#", 1)[0])
                with self.subTest(document=document.relative_to(ROOT), link=link):
                    self.assertTrue((document.parent / target).exists())

    def test_stage_table_keeps_six_events_and_separate_engineering_gate(self):
        body = (SKILLS / "chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md").read_text(encoding="utf-8")
        for stage in ("source", "scaffold", "island", "reconnect", "change", "delivery"):
            self.assertIn("| `" + stage + "` |", body)
        self.assertIn("MODULE_CHECKS_EXECUTED", body)
        self.assertIn("ACTION_REQUIRED", body)
        self.assertIn("engineering_accepted", body)
        self.assertIn("aspen-plus-operations", body)

    def test_knowledge_and_equipment_layers_are_not_replaced(self):
        for relative in (
            "knowledge/records.jsonl", "knowledge/vectors/vectors.npy",
            "backends/equipment/data/standard_facts.sqlite.gz",
            "backends/process/feedback.py", "backends/process/pressure.py",
            "tools/equipment_gateway.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

if __name__ == "__main__":
    unittest.main()
