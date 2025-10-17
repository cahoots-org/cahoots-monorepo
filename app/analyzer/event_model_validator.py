"""Event Model Validator

Validates event models for completeness and consistency following Event Modeling principles.
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    severity: str  # 'error', 'warning', 'info'
    category: str
    message: str
    details: Dict[str, Any]


class EventModelValidator:
    """Validates event models for quality and completeness"""

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate(self, analysis: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate an event model analysis.

        Returns:
            Tuple of (is_valid, issues)
        """
        self.issues = []

        events = analysis.get('events', [])
        commands = analysis.get('commands', [])
        read_models = analysis.get('read_models', [])
        user_interactions = analysis.get('user_interactions', [])
        automations = analysis.get('automations', [])

        # Run all validation checks
        self._validate_basic_completeness(events, commands, read_models)
        self._validate_command_event_mapping(commands, events)
        self._validate_event_naming(events)
        self._validate_command_naming(commands)
        self._validate_read_model_coverage(commands, read_models)
        self._validate_user_interactions(user_interactions, commands, read_models)
        self._validate_automations(automations, events)
        self._validate_slice_balance(commands, read_models, automations)
        self._validate_orphaned_events(events, commands, automations)

        # Validate swimlanes if present
        swimlanes = analysis.get('swimlanes', [])
        if swimlanes:
            self._validate_swimlanes(swimlanes, events, commands, read_models, automations)

        # Check if there are any errors
        has_errors = any(issue.severity == 'error' for issue in self.issues)
        return (not has_errors, self.issues)

    def _validate_basic_completeness(self, events, commands, read_models):
        """Validate basic presence of components"""

        if len(events) == 0:
            self.issues.append(ValidationIssue(
                severity='error',
                category='completeness',
                message='No events found in event model',
                details={'expected': 'At least 1 event', 'actual': 0}
            ))

        if len(commands) == 0:
            self.issues.append(ValidationIssue(
                severity='error',
                category='completeness',
                message='No commands found in event model',
                details={'expected': 'At least 1 command', 'actual': 0}
            ))

        # Read models are optional, but warn if none exist
        if len(read_models) == 0:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='completeness',
                message='No read models found - system has no queries/displays',
                details={'note': 'Read models are only needed when displaying or querying data'}
            ))

    def _validate_command_event_mapping(self, commands, events):
        """Validate that commands have corresponding events"""

        event_names = {e.name if hasattr(e, 'name') else e.get('name') for e in events}

        for cmd in commands:
            cmd_name = cmd.get('name', 'Unknown')
            triggered_events = cmd.get('triggers_events', [])

            if not triggered_events:
                self.issues.append(ValidationIssue(
                    severity='error',
                    category='mapping',
                    message=f'Command "{cmd_name}" does not trigger any events',
                    details={
                        'command': cmd_name,
                        'issue': 'Every command must produce at least one event'
                    }
                ))
            else:
                # Check if triggered events exist
                for event_name in triggered_events:
                    if event_name not in event_names:
                        self.issues.append(ValidationIssue(
                            severity='error',
                            category='mapping',
                            message=f'Command "{cmd_name}" triggers non-existent event "{event_name}"',
                            details={
                                'command': cmd_name,
                                'missing_event': event_name,
                                'available_events': list(event_names)
                            }
                        ))

    def _validate_event_naming(self, events):
        """Validate event naming conventions (past tense)"""

        past_tense_patterns = [
            'ed', 'en', 'Created', 'Updated', 'Deleted', 'Started', 'Stopped',
            'Completed', 'Failed', 'Sent', 'Received', 'Added', 'Removed',
            'Changed', 'Moved', 'Rotated', 'Dropped', 'Cleared', 'Submitted'
        ]

        for event in events:
            event_name = event.name if hasattr(event, 'name') else event.get('name', '')

            # Check if event name is past tense
            is_past_tense = any(event_name.endswith(pattern) for pattern in past_tense_patterns)

            if not is_past_tense:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='naming',
                    message=f'Event "{event_name}" may not be in past tense',
                    details={
                        'event': event_name,
                        'convention': 'Events should be past tense (e.g., ItemAdded, UserRegistered)',
                        'examples': ['ItemAdded', 'OrderPlaced', 'PaymentCompleted']
                    }
                ))

    def _validate_command_naming(self, commands):
        """Validate command naming conventions (imperative)"""

        imperative_patterns = [
            'Add', 'Remove', 'Create', 'Delete', 'Update', 'Move', 'Rotate',
            'Drop', 'Clear', 'Submit', 'Start', 'Stop', 'Pause', 'Resume',
            'Send', 'Receive', 'Change', 'Adjust', 'Set', 'Get'
        ]

        for cmd in commands:
            cmd_name = cmd.get('name', '')

            # Check if command name starts with imperative verb
            is_imperative = any(cmd_name.startswith(pattern) for pattern in imperative_patterns)

            if not is_imperative:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='naming',
                    message=f'Command "{cmd_name}" may not be in imperative form',
                    details={
                        'command': cmd_name,
                        'convention': 'Commands should be imperative (e.g., AddItem, RegisterUser)',
                        'examples': ['AddItem', 'PlaceOrder', 'CompletePayment']
                    }
                ))

    def _validate_read_model_coverage(self, commands, read_models):
        """Validate that there are enough read models for the system"""

        # Heuristic: For every 3-5 commands, there should be at least 1 read model
        # This is because commands often share read models

        if len(commands) >= 5 and len(read_models) == 0:
            self.issues.append(ValidationIssue(
                severity='error',
                category='coverage',
                message=f'System has {len(commands)} commands but no read models',
                details={
                    'commands': len(commands),
                    'read_models': 0,
                    'issue': 'With multiple commands, users need to see system state via read models'
                }
            ))
        elif len(commands) >= 3 and len(read_models) < 1:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='coverage',
                message=f'System may need more read models ({len(commands)} commands, {len(read_models)} read models)',
                details={
                    'commands': len(commands),
                    'read_models': len(read_models),
                    'suggestion': 'Consider if users need to view system state'
                }
            ))

    def _validate_user_interactions(self, user_interactions, commands, read_models):
        """Validate user interactions map correctly"""

        command_names = {cmd.get('name') for cmd in commands}
        read_model_names = {rm.get('name') for rm in read_models}

        for interaction in user_interactions:
            action = interaction.get('action', '')
            triggers_command = interaction.get('triggers_command')
            viewed_read_model = interaction.get('viewed_read_model')

            # Check if command exists
            if triggers_command and triggers_command not in command_names:
                self.issues.append(ValidationIssue(
                    severity='error',
                    category='mapping',
                    message=f'User interaction "{action}" triggers non-existent command "{triggers_command}"',
                    details={
                        'interaction': action,
                        'missing_command': triggers_command,
                        'available_commands': list(command_names)
                    }
                ))

            # Check if read model exists (only if specified)
            if viewed_read_model and viewed_read_model not in read_model_names:
                self.issues.append(ValidationIssue(
                    severity='error',
                    category='mapping',
                    message=f'User interaction "{action}" views non-existent read model "{viewed_read_model}"',
                    details={
                        'interaction': action,
                        'missing_read_model': viewed_read_model,
                        'available_read_models': list(read_model_names)
                    }
                ))

    def _validate_automations(self, automations, events):
        """Validate automations are properly configured"""

        event_names = {e.name if hasattr(e, 'name') else e.get('name') for e in events}

        for automation in automations:
            name = automation.get('name', 'Unknown')
            trigger_event = automation.get('trigger_event')
            result_events = automation.get('result_events', [])

            # Check trigger event exists
            if trigger_event and trigger_event not in event_names:
                self.issues.append(ValidationIssue(
                    severity='error',
                    category='mapping',
                    message=f'Automation "{name}" triggered by non-existent event "{trigger_event}"',
                    details={
                        'automation': name,
                        'missing_event': trigger_event,
                        'available_events': list(event_names)
                    }
                ))

            # Check result events exist
            for result_event in result_events:
                if result_event not in event_names:
                    self.issues.append(ValidationIssue(
                        severity='error',
                        category='mapping',
                        message=f'Automation "{name}" produces non-existent event "{result_event}"',
                        details={
                            'automation': name,
                            'missing_event': result_event,
                            'note': 'This event must be added to the events list or the automation should be corrected'
                        }
                    ))

    def _validate_slice_balance(self, commands, read_models, automations):
        """Validate that slices are reasonably balanced"""

        total_slices = len(commands) + len(read_models) + len(automations)

        # Check for imbalanced models
        if len(commands) == 1 and total_slices > 1:
            self.issues.append(ValidationIssue(
                severity='error',
                category='balance',
                message='Event model has only 1 command but multiple other components',
                details={
                    'commands': len(commands),
                    'read_models': len(read_models),
                    'automations': len(automations),
                    'issue': 'A system with read models/automations should have multiple commands'
                }
            ))

        # Warn if ratio seems off
        if len(commands) > 0 and len(read_models) > len(commands) * 2:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='balance',
                message='More read models than expected for number of commands',
                details={
                    'commands': len(commands),
                    'read_models': len(read_models),
                    'note': 'Typically commands outnumber or equal read models'
                }
            ))

    def _validate_orphaned_events(self, events, commands, automations):
        """Check for events that are never triggered"""

        # Get all events that should be triggered
        triggered_event_names = set()

        # From commands
        for cmd in commands:
            triggered_event_names.update(cmd.get('triggers_events', []))

        # From automations
        for auto in automations:
            triggered_event_names.update(auto.get('result_events', []))

        # Find orphaned events
        for event in events:
            event_name = event.name if hasattr(event, 'name') else event.get('name')

            if event_name not in triggered_event_names:
                # Check if it might be an external event (integration pattern)
                event_type = event.event_type.value if hasattr(event, 'event_type') else event.get('event_type', '')

                if event_type == 'integration':
                    # External events are okay to not be triggered internally
                    continue

                self.issues.append(ValidationIssue(
                    severity='error',
                    category='orphaned',
                    message=f'Event "{event_name}" is never triggered by any command or automation',
                    details={
                        'event': event_name,
                        'note': 'Every event must be triggered by at least one command or automation, or marked as integration type'
                    }
                ))

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of validation results"""

        errors = [i for i in self.issues if i.severity == 'error']
        warnings = [i for i in self.issues if i.severity == 'warning']
        info = [i for i in self.issues if i.severity == 'info']

        return {
            'valid': len(errors) == 0,
            'total_issues': len(self.issues),
            'errors': len(errors),
            'warnings': len(warnings),
            'info': len(info),
            'issues_by_category': self._group_by_category(),
            'critical_issues': [
                {'message': i.message, 'details': i.details}
                for i in errors[:5]  # Top 5 critical issues
            ]
        }

    def _group_by_category(self) -> Dict[str, int]:
        """Group issues by category"""
        categories = {}
        for issue in self.issues:
            categories[issue.category] = categories.get(issue.category, 0) + 1
        return categories

    def _validate_swimlanes(self, swimlanes, events, commands, read_models, automations):
        """Validate swimlanes for narrative coherence and completeness"""

        # Create name lookups
        event_names = {e.name if hasattr(e, 'name') else e.get('name') for e in events}
        command_names = {cmd.get('name') for cmd in commands}
        read_model_names = {rm.get('name') for rm in read_models}
        automation_names = {auto.get('name') for auto in automations}

        # Track which components are assigned to swimlanes
        assigned_events = set()
        assigned_commands = set()
        assigned_read_models = set()
        assigned_automations = set()

        for swimlane in swimlanes:
            name = swimlane.get('name', 'Unknown')
            swimlane_events = swimlane.get('events', [])
            swimlane_commands = swimlane.get('commands', [])
            swimlane_read_models = swimlane.get('read_models', [])
            swimlane_automations = swimlane.get('automations', [])

            # Validate that swimlane components exist in the global model
            for event_name in swimlane_events:
                if event_name not in event_names:
                    self.issues.append(ValidationIssue(
                        severity='error',
                        category='swimlane',
                        message=f'Swimlane "{name}" references non-existent event "{event_name}"',
                        details={
                            'swimlane': name,
                            'missing_event': event_name,
                            'available_events': list(event_names)
                        }
                    ))
                else:
                    assigned_events.add(event_name)

            for command_name in swimlane_commands:
                if command_name not in command_names:
                    self.issues.append(ValidationIssue(
                        severity='error',
                        category='swimlane',
                        message=f'Swimlane "{name}" references non-existent command "{command_name}"',
                        details={
                            'swimlane': name,
                            'missing_command': command_name,
                            'available_commands': list(command_names)
                        }
                    ))
                else:
                    assigned_commands.add(command_name)

            for rm_name in swimlane_read_models:
                if rm_name not in read_model_names:
                    self.issues.append(ValidationIssue(
                        severity='error',
                        category='swimlane',
                        message=f'Swimlane "{name}" references non-existent read model "{rm_name}"',
                        details={
                            'swimlane': name,
                            'missing_read_model': rm_name,
                            'available_read_models': list(read_model_names)
                        }
                    ))
                else:
                    assigned_read_models.add(rm_name)

            for auto_name in swimlane_automations:
                if auto_name not in automation_names:
                    self.issues.append(ValidationIssue(
                        severity='error',
                        category='swimlane',
                        message=f'Swimlane "{name}" references non-existent automation "{auto_name}"',
                        details={
                            'swimlane': name,
                            'missing_automation': auto_name,
                            'available_automations': list(automation_names)
                        }
                    ))
                else:
                    assigned_automations.add(auto_name)

            # Validate minimum components per swimlane (narrative coherence check)
            if len(swimlane_events) < 1:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='swimlane',
                    message=f'Swimlane "{name}" has no events',
                    details={
                        'swimlane': name,
                        'note': 'A swimlane should have events to tell a story'
                    }
                ))

            if len(swimlane_commands) < 1 and len(swimlane_automations) < 1:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='swimlane',
                    message=f'Swimlane "{name}" has no commands or automations',
                    details={
                        'swimlane': name,
                        'note': 'A swimlane should have commands or automations that trigger events'
                    }
                ))

        # Check for unassigned components (info level - some systems may not use swimlanes fully)
        unassigned_events = event_names - assigned_events
        if unassigned_events and len(unassigned_events) > len(event_names) * 0.2:  # More than 20% unassigned
            self.issues.append(ValidationIssue(
                severity='info',
                category='swimlane',
                message=f'{len(unassigned_events)} events not assigned to any swimlane',
                details={
                    'unassigned_count': len(unassigned_events),
                    'examples': list(unassigned_events)[:5],
                    'note': 'Events should be assigned to swimlanes for narrative coherence'
                }
            ))

        unassigned_commands = command_names - assigned_commands
        if unassigned_commands and len(unassigned_commands) > len(command_names) * 0.2:
            self.issues.append(ValidationIssue(
                severity='info',
                category='swimlane',
                message=f'{len(unassigned_commands)} commands not assigned to any swimlane',
                details={
                    'unassigned_count': len(unassigned_commands),
                    'examples': list(unassigned_commands)[:5],
                    'note': 'Commands should be assigned to swimlanes for narrative coherence'
                }
            ))

        # Check for reasonable number of swimlanes (3-8 is typical)
        if len(swimlanes) < 2:
            self.issues.append(ValidationIssue(
                severity='info',
                category='swimlane',
                message=f'Only {len(swimlanes)} swimlane(s) detected',
                details={
                    'swimlanes': len(swimlanes),
                    'note': 'Typical systems have 3-8 swimlanes representing different business capabilities'
                }
            ))
        elif len(swimlanes) > 10:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='swimlane',
                message=f'{len(swimlanes)} swimlanes may be too many',
                details={
                    'swimlanes': len(swimlanes),
                    'note': 'Consider consolidating related capabilities. Typical systems have 3-8 swimlanes.'
                }
            ))
