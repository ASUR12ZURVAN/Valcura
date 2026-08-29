# Meta Template System Guide

## Overview

This system provides a complete solution for managing WhatsApp message templates with database storage, intelligent caching, and a cause->reason->response workflow for patient communication.

## Architecture

### Components

1. **MetaTemplate Model** (`models.py`)
   - Database model for storing template metadata
   - Includes all fields from the CSV (library, trigger, treatment, objection, etc.)
   - Automatic cache invalidation on updates

2. **TemplateCacheService** (`template_cache.py`)
   - High-performance caching layer using Django's cache framework
   - 24-hour cache timeout for templates
   - Multiple retrieval strategies (by ID, library, trigger, treatment, objection)
   - Situation-based template finding

3. **WorkflowService** (`workflow_service.py`)
   - Implements cause->reason->response workflow
   - Analyzes patient interactions to determine appropriate responses
   - Manages workflow state per phone number
   - Handles time-based message scheduling

4. **TemplateRetrievalService** (`template_retrieval.py`)
   - High-level API for template retrieval
   - Situation-specific methods (missed call, appointment confirmation, etc.)
   - Search and validation capabilities

5. **TemplateService** (`services.py`)
   - Updated to use cached database model
   - Backward compatible with existing code
   - Variable normalization and message rendering

## Setup Instructions

### 1. Database Migration

Run migrations to create the new models:

```bash
python manage.py makemigrations user_request
python manage.py migrate
```

### 2. Import Templates from CSV

Import the Meta Templates from your CSV file:

```bash
python manage.py import_templates --csv-file "Meta Templates - Sheet1.csv"
```

The command will automatically search for the CSV file in common locations.

### 3. Configure Caching

Ensure your Django settings have caching configured. Example in `settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'valcura-cache',
    }
}
```

For production, use Redis or Memcached:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

## Usage Examples

### Basic Template Retrieval

```python
from user_request.template_cache import TemplateCacheService

# Get a specific template by ID
template = TemplateCacheService.get_template('UTL-L1-01')

# Get all templates for a library
library_templates = TemplateCacheService.get_templates_by_library('Library 1')

# Find template by situation (library + trigger + treatment + objection)
template = TemplateCacheService.find_template_by_situation(
    library='Library 5',
    trigger='Primary Objection = Cost',
    treatment='Root Canal Treatment'
)
```

### Cause -> Reason -> Response Workflow

```python
from user_request.workflow_service import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()

# Process a missed call event
result = orchestrator.process_event(
    phone_number='+1234567890',
    is_missed_call=True
)

if result['success']:
    template = result['template']
    variables_needed = result['variables_needed']
    # Send message using template and variables

# Process a cost objection
result = orchestrator.process_event(
    phone_number='+1234567890',
    user_message='This treatment is too expensive',
    treatment='Root Canal Treatment',
    objection='Cost'
)

# Process appointment booking
result = orchestrator.process_event(
    phone_number='+1234567890',
    appointment_booked=True
)
```

### Situation-Specific Template Retrieval

```python
from user_request.template_retrieval import TemplateRetrievalService

# Get template for missed call
template = TemplateRetrievalService.get_templates_for_missed_call()

# Get template for appointment confirmation
template = TemplateRetrievalService.get_templates_for_appointment_confirmation()

# Get template for cost objection
template = TemplateRetrievalService.get_templates_for_cost_objection(
    treatment='Root Canal Treatment'
)

# Get template for trust objection
template = TemplateRetrievalService.get_templates_for_trust_objection(
    treatment='Root Canal Treatment'
)

# Get complete workflow sequence for a library
sequence = TemplateRetrievalService.get_workflow_sequence('Library 1')
```

### Message Rendering with Variables

```python
from user_request.services import TemplateService

service = TemplateService()

# Get required variables for a template
required_vars = service.required_variables('UTL-L1-01')

# Normalize variables using variable mapping
variables = {
    'clinic_name': 'Dental Care Clinic',
    'doctor_name': 'Dr. Smith',
    'reception_number': '+1234567890'
}
normalized = service.normalize_variables('UTL-L1-01', variables)

# Render the message
message = service.get_message('UTL-L1-01', {
    '1': 'Dental Care Clinic',
    '2': 'Dr. Smith',
    '3': '+1234567890'
})
```

### Workflow State Management

```python
from user_request.workflow_service import WorkflowService

# Get next template in sequence based on time
next_template = WorkflowService.get_next_template_in_sequence('+1234567890')

# Check if workflow should exit
should_exit = WorkflowService.should_exit_workflow(
    phone_number='+1234567890',
    template=template_data
)

# Reset workflow for a patient
WorkflowService.reset_workflow('+1234567890')
```

### Scheduled Messages

```python
from user_request.workflow_service import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()

# Get all messages that should be sent based on time
scheduled = orchestrator.get_scheduled_messages()

for item in scheduled:
    phone_number = item['phone_number']
    template = item['template']
    # Send the message
```

## Template Libraries

The system organizes templates into libraries based on patient journey:

- **Library 1**: Missed call recovery and initial engagement
- **Library 2**: Post-call engagement and treatment introduction
- **Library 3**: Appointment confirmation and reminders
- **Library 4**: Visit summary and post-consultation follow-up
- **Library 5**: Objection handling (Cost, Trust, Fear, Urgency)

## Cause Analysis

The system analyzes various causes to trigger appropriate responses:

### System Events
- **Missed Call**: Triggers Library 1 apology and callback request
- **Appointment Booked**: Triggers Library 3 confirmation
- **Call Completed**: Triggers Library 2 engagement if no appointment
- **Consultation Completed**: Triggers Library 4 visit summary

### User Messages
- **Cost Objection**: "expensive", "cost", "price", "afford" → Library 5 Cost handling
- **Trust Objection**: "trust", "sure", "necessary", "really need" → Library 5 Trust handling
- **Fear Objection**: "pain", "hurt", "scared", "afraid" → Library 5 Fear handling
- **Urgency Objection**: "wait", "later", "not urgent" → Library 5 Urgency handling
- **Positive Response**: "yes", "sure", "okay" → Continues workflow

## Caching Strategy

### Cache Keys
- `template_{template_id}`: Individual template cache
- `templates_library_{library}`: All templates in a library
- `templates_trigger_{trigger}`: Templates by trigger
- `templates_treatment_{treatment}`: Templates by treatment
- `templates_objection_{objection}`: Templates by objection
- `situation_{library}_{trigger}_{treatment}_{objection}`: Situation-based lookup
- `all_templates_cache`: Complete template catalog

### Cache Invalidation
- Automatic invalidation when templates are updated via model save
- Manual invalidation available via TemplateCacheService methods
- 24-hour TTL ensures fresh data

## API Reference

### TemplateCacheService

```python
TemplateCacheService.get_template(template_id: str) -> Optional[Dict]
TemplateCacheService.get_all_templates() -> Dict[str, Dict]
TemplateCacheService.get_templates_by_library(library: str) -> List[Dict]
TemplateCacheService.get_templates_by_trigger(trigger: str) -> List[Dict]
TemplateCacheService.get_templates_by_treatment(treatment: str) -> List[Dict]
TemplateCacheService.get_templates_by_objection(objection: str) -> List[Dict]
TemplateCacheService.find_template_by_situation(library, trigger, treatment, objection) -> Optional[Dict]
TemplateCacheService.invalidate_template(template_id: str)
TemplateCacheService.invalidate_library_cache(library: str)
TemplateCacheService.invalidate_all()
```

### WorkflowService

```python
WorkflowService.analyze_cause(user_message, is_missed_call, appointment_booked) -> Dict
WorkflowService.determine_reason(phone_number, cause, treatment, objection) -> Dict
WorkflowService.get_response(phone_number, cause, reason) -> Optional[Dict]
WorkflowService.update_workflow_state(phone_number, template_id, cause, reason, metadata) -> WorkflowState
WorkflowService.should_exit_workflow(phone_number, template) -> bool
WorkflowService.get_next_template_in_sequence(phone_number) -> Optional[Dict]
WorkflowService.reset_workflow(phone_number) -> bool
```

### WorkflowOrchestrator

```python
WorkflowOrchestrator.process_event(phone_number, user_message, is_missed_call, appointment_booked, treatment, objection, metadata) -> Dict
WorkflowOrchestrator.get_scheduled_messages() -> List[Dict]
```

### TemplateRetrievalService

```python
TemplateRetrievalService.get_template_by_id(template_id) -> Optional[Dict]
TemplateRetrievalService.get_templates_for_missed_call() -> Optional[Dict]
TemplateRetrievalService.get_templates_for_appointment_confirmation() -> Optional[Dict]
TemplateRetrievalService.get_templates_for_cost_objection(treatment) -> Optional[Dict]
TemplateRetrievalService.get_templates_for_trust_objection(treatment) -> Optional[Dict]
TemplateRetrievalService.get_templates_for_fear_objection(treatment) -> Optional[Dict]
TemplateRetrievalService.get_templates_for_urgency_objection(treatment) -> Optional[Dict]
TemplateRetrievalService.get_all_library_templates(library) -> List[Dict]
TemplateRetrievalService.get_workflow_sequence(library) -> List[Dict]
TemplateRetrievalService.validate_template_variables(template_id, variables) -> Dict
```

## Database Schema

### MetaTemplate
- `template_id`: Primary key (e.g., "UTL-L1-01")
- `meta_template_name`: Template name
- `library`: Library assignment (Library 1-5)
- `message_name`: Human-readable message name
- `category`: Utility or Marketing
- `treatment`: Treatment type (for Library 5)
- `objection`: Objection type (for Library 5)
- `trigger`: Event trigger
- `day`: Timing specification
- `meta_approved_body`: Message body with placeholders
- `meta_mapping`: Variable order for Meta API
- `variable_mapping`: Variable definitions
- Additional metadata fields (objective, AI rules, etc.)

### WorkflowState
- `phone_number`: Patient phone number (unique)
- `current_library`: Active workflow library
- `current_step`: Current step in sequence
- `last_template_id`: Last sent template
- `treatment`: Associated treatment
- `objection`: Associated objection
- `appointment_booked`: Appointment status
- `last_message_date`: Last message timestamp
- `metadata`: Additional JSON data

## Performance Considerations

1. **Caching**: All template retrievals are cached with 24-hour TTL
2. **Database Indexes**: Key fields (library, trigger, treatment, objection) are indexed
3. **Batch Operations**: Import command processes all templates efficiently
4. **Cache Invalidation**: Selective invalidation minimizes cache misses

## Troubleshooting

### Templates not appearing after import
- Check that the CSV path is correct
- Verify CSV format matches expected structure
- Run import with verbose error checking

### Cache not refreshing
- Manually invalidate cache: `TemplateCacheService.invalidate_all()`
- Check cache backend configuration
- Verify cache timeout settings

### Workflow not progressing
- Check workflow state in database
- Verify day field parsing for time-based triggers
- Ensure trigger conditions match template definitions

## Migration from Old System

The updated `TemplateService` maintains backward compatibility. Existing code using `TemplateService` will automatically use the new cached database model without requiring code changes.

Old code:
```python
from user_request.services import TemplateService
template = TemplateService.get_template('UTL-L1-01')
```

This continues to work but now leverages the database and caching system.

## Future Enhancements

- A/B testing support for template variations
- Analytics and performance tracking per template
- Multi-language template support
- Template versioning and rollback
- Real-time template editing interface
