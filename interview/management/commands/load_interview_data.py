import json
import os
import sys
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from interview.models import InterviewModule, Question, JumpRule

# Suppress Django DB logger UnicodeEncodeError on Windows cp1252 consoles
logging.getLogger("django.db.backends").setLevel(logging.WARNING)


class Command(BaseCommand):
    help = "Load interview modules and questions from JSON data files"

    MODULE_FILES = [
        "module_a.json",
        "module_b.json",
        "module_c.json",
        "module_d.json",
    ]

    def handle(self, *args, **options):
        interview_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        data_dir = os.path.join(interview_dir, "data")

        # Phase 1: Load all modules and questions
        for filename in self.MODULE_FILES:
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath):
                self._write(self.style.WARNING(f"Skipping {filename} — file not found"))
                continue
            self._load_questions(filepath, filename)

        # Phase 2: Load all jump rules (now all questions exist across modules)
        for filename in self.MODULE_FILES:
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath):
                continue
            self._load_jump_rules(filepath, filename)

    def _write(self, msg):
        """Write to stdout with safe encoding for Windows consoles."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            self.stdout.write(
                msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
            )

    def _load_questions(self, filepath, filename):
        """Phase 1: Create module and questions."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        with transaction.atomic():
            module_data = data["module"]
            module, created = InterviewModule.objects.get_or_create(
                name=module_data["name"],
                defaults={
                    "description": module_data["description"],
                    "version": module_data["version"],
                    "is_active": module_data["is_active"],
                    "order": module_data["order"],
                },
            )

            if created:
                self._write(self.style.SUCCESS(f"Created module: {module.name}"))
            else:
                self._write(f"  Module exists: {module.name}")

            created_count = 0
            for q_data in data["questions"]:
                _, created = Question.objects.get_or_create(
                    id=q_data["id"],
                    module=module,
                    defaults={
                        "text": q_data["text"],
                        "question_type": q_data["question_type"],
                        "is_criteria": q_data.get("is_criteria", False),
                        "criteria_number": q_data.get("criteria_number", ""),
                        "order": q_data["order"],
                        "is_required": q_data.get("is_required", True),
                        "has_jump_logic": q_data.get("has_jump_logic", False),
                    },
                )
                if created:
                    created_count += 1

            total = len(data["questions"])
            if created_count:
                self._write(
                    self.style.SUCCESS(f"  {created_count}/{total} questions created")
                )
            else:
                self._write(f"  All {total} questions already exist")

    def _load_jump_rules(self, filepath, filename):
        """Phase 2: Create jump rules (all questions across modules now exist)."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        rules_data = data.get("jump_rules", [])
        if not rules_data:
            return

        module = InterviewModule.objects.get(name=data["module"]["name"])
        created_count = 0

        for rule_data in rules_data:
            try:
                from_q = Question.objects.get(
                    id=rule_data["from_question"], module=module
                )
                to_q = None
                if rule_data["to_question"]:
                    to_q = Question.objects.get(id=rule_data["to_question"])

                _, created = JumpRule.objects.get_or_create(
                    from_question=from_q,
                    condition=rule_data["condition"],
                    defaults={
                        "to_question": to_q,
                        "condition_type": rule_data["condition_type"],
                        "metadata": rule_data["metadata"],
                    },
                )
                if created:
                    created_count += 1
                    target = rule_data["to_question"] or "END"
                    self._write(
                        self.style.SUCCESS(
                            f'  Jump rule: {rule_data["from_question"]} -> {target}'
                        )
                    )
            except Question.DoesNotExist as e:
                self._write(
                    self.style.ERROR(
                        f'  Failed: {rule_data["from_question"]} -> {rule_data["to_question"]}: {e}'
                    )
                )

        if created_count:
            self._write(
                self.style.SUCCESS(
                    f"  {created_count}/{len(rules_data)} jump rules created"
                )
            )
        else:
            self._write(f"  All {len(rules_data)} jump rules already exist")
