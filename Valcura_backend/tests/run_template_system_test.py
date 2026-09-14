import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Valcura_backend.settings')
django.setup()

from user_request.template_cache import TemplateCacheService
from user_request.template_retrieval import TemplateRetrievalService
from user_request.workflow_service import WorkflowOrchestrator

# Test 1: Basic template retrieval with caching
print("=== Test 1: Basic Template Retrieval ===")
template = TemplateCacheService.get_template('UTL-L1-01')
if template:
    print(f"✓ Retrieved template: {template['template_id']} - {template['meta_template_name']}")
    print(f"  Library: {template['library']}, Trigger: {template['trigger']}")
else:
    print("✗ Failed to retrieve template")

# Test 2: Template retrieval by library
print("\n=== Test 2: Library Templates ===")
library_templates = TemplateCacheService.get_templates_by_library('Library 1')
print(f"✓ Retrieved {len(library_templates)} templates from Library 1")

# Test 3: Situation-based template finding
print("\n=== Test 3: Situation-Based Retrieval ===")
missed_call_template = TemplateRetrievalService.get_templates_for_missed_call()
if missed_call_template:
    print(f"✓ Found missed call template: {missed_call_template['template_id']}")
else:
    print("✗ Failed to find missed call template")

# Test 4: Cost objection template
print("\n=== Test 4: Objection Handling ===")
cost_template = TemplateRetrievalService.get_templates_for_cost_objection('Root Canal Treatment')
if cost_template:
    print(f"✓ Found cost objection template: {cost_template['template_id']}")
else:
    print("✗ Failed to find cost objection template")

# Test 5: Workflow orchestration
print("\n=== Test 5: Workflow Orchestration ===")
orchestrator = WorkflowOrchestrator()
result = orchestrator.process_event(
    phone_number='+1234567890',
    is_missed_call=True
)
if result['success']:
    print(f"✓ Workflow processed successfully")
    print(f"  Template: {result['template']['template_id']}")
    print(f"  Cause: {result['cause']['trigger']}")
    print(f"  Reason: {result['reason']['library']}")
else:
    print(f"✗ Workflow failed: {result.get('message')}")

# Test 6: User message analysis
print("\n=== Test 6: User Message Analysis ===")
# Reset workflow state first
from user_request.workflow_service import WorkflowService
WorkflowService.reset_workflow('+1234567890')

result = orchestrator.process_event(
    phone_number='+1234567890',
    user_message='This treatment is too expensive',
    treatment='Root Canal Treatment'
)
if result['success']:
    print(f"✓ User message analyzed successfully")
    print(f"  Detected cause: {result['cause']['trigger']}")
    print(f"  Selected template: {result['template']['template_id']}")
else:
    print(f"✗ User message analysis failed: {result.get('message')}")

# Test 7: Workflow sequence
print("\n=== Test 7: Workflow Sequence ===")
sequence = TemplateRetrievalService.get_workflow_sequence('Library 1')
print(f"✓ Retrieved workflow sequence with {len(sequence)} templates for Library 1")
if sequence:
    print(f"  First template: {sequence[0]['template_id']}")
    print(f"  Last template: {sequence[-1]['template_id']}")

print("\n=== All Tests Complete ===")
