import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from interview.models import InterviewModule, Question, JumpRule

class Command(BaseCommand):
    help = 'Load interview modules and questions from JSON data files'

    def handle(self, *args, **options):
        # Get the absolute path to the interview app directory
        import os
        interview_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(interview_dir, 'data')
        
        # Load Module A data
        module_a_path = os.path.join(data_dir, 'module_a.json')
        
        if not os.path.exists(module_a_path):
            self.stdout.write(
                self.style.ERROR(f'Module A data file not found at {module_a_path}')
            )
            return
        
        try:
            with open(module_a_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with transaction.atomic():
                # Create or update module
                module_data = data['module']
                module, created = InterviewModule.objects.get_or_create(
                    name=module_data['name'],
                    defaults={
                        'description': module_data['description'],
                        'version': module_data['version'],
                        'is_active': module_data['is_active'],
                        'order': module_data['order']
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created module: {module.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Module already exists: {module.name}')
                    )
                
                # Create questions
                questions_data = data['questions']
                for question_data in questions_data:
                    question, created = Question.objects.get_or_create(
                        id=question_data['id'],
                        module=module,
                        defaults={
                            'text': question_data['text'],
                            'question_type': question_data['question_type'],
                            'is_criteria': question_data.get('is_criteria', False),
                            'criteria_number': question_data.get('criteria_number', ''),
                            'order': question_data['order'],
                            'is_required': question_data.get('is_required', True),
                            'has_jump_logic': question_data.get('has_jump_logic', False)
                        }
                    )
                    
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f'Created question: {question.id}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'Question already exists: {question.id}')
                        )
                
                # Create jump rules
                jump_rules_data = data.get('jump_rules', [])
                for rule_data in jump_rules_data:
                    try:
                        from_question = Question.objects.get(id=rule_data['from_question'])
                        to_question_id = rule_data['to_question']
                        
                        to_question = None
                        if to_question_id:
                            to_question = Question.objects.get(id=to_question_id)
                        
                        jump_rule, created = JumpRule.objects.get_or_create(
                            from_question=from_question,
                            condition=rule_data['condition'],
                            defaults={
                                'to_question': to_question,
                                'condition_type': rule_data['condition_type'],
                                'metadata': rule_data['metadata']
                            }
                        )
                        
                        if created:
                            target_name = to_question_id if to_question_id else "None"
                            self.stdout.write(
                                self.style.SUCCESS(f'Created jump rule: {rule_data["from_question"]} -> {target_name}')
                            )
                        else:
                            target_name = to_question_id if to_question_id else "None"
                            self.stdout.write(
                                self.style.WARNING(f'Jump rule already exists: {rule_data["from_question"]} -> {target_name}')
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Failed to create jump rule {rule_data["from_question"]} -> {rule_data["to_question"]}: {str(e)}')
                        )
                        continue
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully loaded Module A with {len(questions_data)} questions and {len(jump_rules_data)} jump rules')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading Module A data: {str(e)}')
            )
            raise