"""Event Model Markdown Generator

Converts event modeling analysis into human and AI-readable markdown format
following Event Modeling best practices.
"""

from typing import List, Dict, Any


class EventModelMarkdownGenerator:
    """Generates structured markdown representation of Event Models"""

    def generate(self, analysis: Dict[str, Any], project_description: str = "") -> str:
        """
        Generate complete event model in markdown table format.

        Args:
            analysis: Event modeling analysis with events, commands, read_models, etc.
            project_description: High-level project description

        Returns:
            Markdown string with complete event model
        """
        sections = []

        # Header
        sections.append(self._generate_header(project_description))

        # Overview
        sections.append(self._generate_overview(analysis))

        # Swimlanes (Business Capabilities)
        swimlanes_section = self._generate_swimlanes_section(analysis)
        if swimlanes_section:
            sections.append(swimlanes_section)

        # Chapters (Workflows)
        chapters_section = self._generate_chapters_section(analysis)
        if chapters_section:
            sections.append(chapters_section)

        # State Change Slices (Commands → Events)
        state_changes = self._generate_state_change_slices(analysis)
        if state_changes:
            sections.append("## State Change Slices\n")
            sections.append(state_changes)

        # State View Slices (Events → Read Models)
        state_views = self._generate_state_view_slices(analysis)
        if state_views:
            sections.append("## State View Slices\n")
            sections.append(state_views)

        # Automation Slices (Event → Process → Command → Event)
        automations = self._generate_automation_slices(analysis)
        if automations:
            sections.append("## Automation Slices\n")
            sections.append(automations)

        # Event Catalog
        sections.append(self._generate_event_catalog(analysis))

        # Information Completeness Check
        sections.append(self._generate_completeness_notes(analysis))

        return "\n\n".join(sections)

    def _generate_header(self, project_description: str) -> str:
        """Generate document header"""
        return f"""# Event Model

**Project**: {project_description or "System"}

This document represents the Event Model following Event Modeling best practices. Each slice represents an independent, isolated unit of functionality that can be implemented separately."""

    def _generate_overview(self, analysis: Dict[str, Any]) -> str:
        """Generate high-level overview statistics"""
        events = analysis.get("events", [])
        commands = analysis.get("commands", [])
        read_models = analysis.get("read_models", [])
        automations = analysis.get("automations", [])
        swimlanes = analysis.get("swimlanes", [])
        chapters = analysis.get("chapters", [])

        overview = f"""## Overview

| Component | Count |
|-----------|-------|
| Events | {len(events)} |
| Commands | {len(commands)} |
| Read Models | {len(read_models)} |
| Automations | {len(automations)} |
| Total Slices | {len(commands) + len(read_models) + len(automations)} |"""

        if swimlanes:
            overview += f"\n| Swimlanes | {len(swimlanes)} |"

        if chapters:
            overview += f"\n| Chapters | {len(chapters)} |"

        return overview

    def _generate_swimlanes_section(self, analysis: Dict[str, Any]) -> str:
        """Generate swimlanes (business capabilities) section"""
        swimlanes = analysis.get("swimlanes", [])

        if not swimlanes:
            return ""

        sections = ["## Swimlanes (Business Capabilities)", ""]
        sections.append("Swimlanes organize the system by business capabilities. Each swimlane groups related events, commands, and read models that tell a coherent story.")
        sections.append("")

        for swimlane in swimlanes:
            name = swimlane.get("name", "Unknown")
            description = swimlane.get("description", "")
            events = swimlane.get("events", [])
            commands = swimlane.get("commands", [])
            read_models = swimlane.get("read_models", [])
            automations = swimlane.get("automations", [])

            sections.append(f"### {name}")
            sections.append("")
            if description:
                sections.append(f"**Description**: {description}")
                sections.append("")

            # Build summary table
            table = ["| Component | Count | Items |", "|-----------|-------|-------|"]
            table.append(f"| Events | {len(events)} | {', '.join([f'`{e}`' for e in events[:5]])}{'...' if len(events) > 5 else ''} |")
            table.append(f"| Commands | {len(commands)} | {', '.join([f'`{c}`' for c in commands[:5]])}{'...' if len(commands) > 5 else ''} |")
            table.append(f"| Read Models | {len(read_models)} | {', '.join([f'`{r}`' for r in read_models[:5]])}{'...' if len(read_models) > 5 else ''} |")
            if automations:
                table.append(f"| Automations | {len(automations)} | {', '.join([f'`{a}`' for a in automations[:5]])}{'...' if len(automations) > 5 else ''} |")

            sections.extend(table)
            sections.append("")

        return "\n".join(sections)

    def _generate_chapters_section(self, analysis: Dict[str, Any]) -> str:
        """Generate chapters (workflows) section"""
        chapters = analysis.get("chapters", [])

        if not chapters:
            return ""

        sections = ["## Chapters (Workflows)", ""]
        sections.append("Chapters group slices into logical workflows, representing major business processes.")
        sections.append("")

        for chapter in chapters:
            name = chapter.get("name", "Unknown")
            description = chapter.get("description", "")
            sub_chapters = chapter.get("sub_chapters", [])

            sections.append(f"### {name}")
            sections.append("")
            if description:
                sections.append(f"**Description**: {description}")
                sections.append("")

            if sub_chapters:
                sections.append("**Sub-Chapters**:")
                sections.append("")
                for sub_chapter in sub_chapters:
                    sub_name = sub_chapter.get("name", "Unknown")
                    slices = sub_chapter.get("slices", [])
                    sections.append(f"- **{sub_name}** ({len(slices)} slices)")

                sections.append("")

        return "\n".join(sections)

    def _generate_state_change_slices(self, analysis: Dict[str, Any]) -> str:
        """Generate State Change slices (UI → Command → Event)"""
        commands = analysis.get("commands", [])
        events = analysis.get("events", [])
        user_interactions = analysis.get("user_interactions", [])

        if not commands:
            return ""

        # Create event lookup
        event_map = {e.name if hasattr(e, 'name') else e.get('name'): e for e in events}

        # Create interaction lookup (command → interaction)
        interaction_map = {}
        for interaction in user_interactions:
            cmd_name = interaction.get("triggers_command")
            if cmd_name:
                interaction_map[cmd_name] = interaction

        sections = []

        for cmd in commands:
            cmd_name = cmd.get("name", "Unknown Command")
            sections.append(f"### Slice: {cmd_name}")
            sections.append("")

            # Build table
            table = ["| Element | Details |", "|---------|---------|"]

            # Type
            table.append("| **Type** | State Change |")

            # UI interaction if available
            interaction = interaction_map.get(cmd_name)
            if interaction:
                ui_action = interaction.get("action", "User interaction")
                viewed_model = interaction.get("viewed_read_model")
                ui_desc = ui_action
                if viewed_model:
                    ui_desc += f" (viewing {viewed_model})"
                table.append(f"| **UI** | {ui_desc} |")

            # Command
            table.append(f"| **Command** | `{cmd_name}` |")

            # Description
            desc = cmd.get("description", "")
            if desc:
                table.append(f"| **Description** | {desc} |")

            # Input data
            input_data = cmd.get("input_data", [])
            if input_data:
                input_str = ", ".join(input_data)
                table.append(f"| **Input Data** | {input_str} |")

            # Events triggered
            triggered_events = cmd.get("triggers_events", [])
            if triggered_events:
                event_details = []
                for event_name in triggered_events:
                    event = event_map.get(event_name)
                    if event:
                        # Get event description
                        if hasattr(event, 'description'):
                            desc = event.description
                        else:
                            desc = event.get('description', '')

                        if desc:
                            event_details.append(f"`{event_name}` - {desc}")
                        else:
                            event_details.append(f"`{event_name}`")
                    else:
                        event_details.append(f"`{event_name}`")

                event_str = "<br>".join(event_details)
                table.append(f"| **Events** | {event_str} |")

            sections.append("\n".join(table))

            # Add GWT placeholder with business rules note
            sections.append("")
            sections.append("#### Given/When/Then")
            sections.append("")
            sections.append("| Scenario | Given | When | Then |")
            sections.append("|----------|-------|------|------|")
            sections.append(f"| Happy Path | Prerequisites met | {cmd_name} executed | {', '.join(triggered_events) if triggered_events else 'Event(s) stored'} |")
            sections.append("")
            sections.append("*Note: Additional GWTs should be defined for business rules, validations, and error cases.*")
            sections.append("")
            sections.append("---")
            sections.append("")

        return "\n".join(sections)

    def _generate_state_view_slices(self, analysis: Dict[str, Any]) -> str:
        """Generate State View slices (Events → Read Model → UI)"""
        read_models = analysis.get("read_models", [])
        events = analysis.get("events", [])

        if not read_models:
            return ""

        # Create event lookup
        event_map = {e.name if hasattr(e, 'name') else e.get('name'): e for e in events}

        sections = []

        for rm in read_models:
            rm_name = rm.get("name", "Unknown Read Model")
            sections.append(f"### Slice: {rm_name}")
            sections.append("")

            # Build table
            table = ["| Element | Details |", "|---------|---------|"]

            # Type
            table.append("| **Type** | State View (Query) |")

            # Description
            desc = rm.get("description", "")
            if desc:
                table.append(f"| **Description** | {desc} |")

            # Source events - infer from event types
            # In a complete system, this would be tracked explicitly
            # For now, we'll note that it should be specified
            table.append("| **Source Events** | *To be determined based on Information Completeness Check* |")

            # Read Model name
            table.append(f"| **Read Model** | `{rm_name}` |")

            # Fields
            data_fields = rm.get("data_fields", [])
            if data_fields:
                if isinstance(data_fields, list):
                    fields_str = ", ".join(data_fields)
                else:
                    fields_str = str(data_fields)
                table.append(f"| **Fields** | {fields_str} |")

            # UI display
            table.append("| **UI** | Display/Query interface |")

            sections.append("\n".join(table))

            # Add Given/Then placeholder
            sections.append("")
            sections.append("#### Given/Then")
            sections.append("")
            sections.append("| Scenario | Given | Then |")
            sections.append("|----------|-------|------|")
            sections.append(f"| Display Data | Source events occurred | {rm_name} shows correct data |")
            sections.append("")
            sections.append("*Note: Define specific Given/Then scenarios with example data for each field.*")
            sections.append("")
            sections.append("---")
            sections.append("")

        return "\n".join(sections)

    def _generate_automation_slices(self, analysis: Dict[str, Any]) -> str:
        """Generate Automation slices (Event → Read Model → Processor → Command → Event)"""
        automations = analysis.get("automations", [])
        events = analysis.get("events", [])

        if not automations:
            return ""

        # Create event lookup
        event_map = {e.name if hasattr(e, 'name') else e.get('name'): e for e in events}

        sections = []

        for auto in automations:
            auto_name = auto.get("name", "Unknown Automation")
            sections.append(f"### Slice: {auto_name}")
            sections.append("")

            # Build table
            table = ["| Element | Details |", "|---------|---------|"]

            # Type
            table.append("| **Type** | Automation (Background Process) |")

            # Trigger event
            trigger = auto.get("trigger_event")
            if trigger:
                trigger_event = event_map.get(trigger)
                if trigger_event:
                    if hasattr(trigger_event, 'description'):
                        trigger_desc = f"`{trigger}` - {trigger_event.description}"
                    else:
                        trigger_desc = f"`{trigger}` - {trigger_event.get('description', '')}"
                else:
                    trigger_desc = f"`{trigger}`"
                table.append(f"| **Trigger Event** | {trigger_desc} |")

            # Read Model (if needed for automation)
            table.append("| **Read Model** | *Define if automation needs to query data* |")

            # Processor
            table.append(f"| **Processor** | ⚙️ {auto_name} |")

            # Command issued (if any)
            table.append("| **Command** | *Define command issued by processor* |")

            # Result events
            result_events = auto.get("result_events", [])
            if result_events:
                result_str = ", ".join([f"`{e}`" for e in result_events])
                table.append(f"| **Output Events** | {result_str} |")

            sections.append("\n".join(table))

            # Add Given/Then placeholder
            sections.append("")
            sections.append("#### Given/Then")
            sections.append("")
            sections.append("| Scenario | Given | Then |")
            sections.append("|----------|-------|------|")
            if trigger and result_events:
                sections.append(f"| Automation Flow | {trigger} occurred | {', '.join(result_events)} |")
            else:
                sections.append("| Automation Flow | Trigger event occurred | Result event(s) stored |")
            sections.append("")
            sections.append("*Note: Define specific automation scenarios including error handling.*")
            sections.append("")
            sections.append("---")
            sections.append("")

        return "\n".join(sections)

    def _generate_event_catalog(self, analysis: Dict[str, Any]) -> str:
        """Generate catalog of all events for reference"""
        events = analysis.get("events", [])

        if not events:
            return ""

        sections = ["## Event Catalog", "", "Complete list of all events in the system:", ""]

        # Build table
        table = [
            "| Event | Type | Actor | Affected Entity | Description |",
            "|-------|------|-------|-----------------|-------------|"
        ]

        for event in events:
            if hasattr(event, 'name'):
                name = event.name
                event_type = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
                actor = event.actor or "-"
                entity = event.affected_entity or "-"
                desc = event.description or "-"
            else:
                name = event.get('name', 'Unknown')
                event_type = event.get('event_type', '-')
                actor = event.get('actor', '-')
                entity = event.get('affected_entity', '-')
                desc = event.get('description', '-')

            table.append(f"| `{name}` | {event_type} | {actor} | {entity} | {desc} |")

        sections.extend(table)
        return "\n".join(sections)

    def _generate_completeness_notes(self, analysis: Dict[str, Any]) -> str:
        """Generate information completeness check notes"""
        return """## Information Completeness Check

**Important**: For each slice, verify:

1. **State Change Slices**:
   - Every event attribute has a source (command or previous events)
   - Every command attribute has a source (UI, read model, or external)
   - All data flows are traced to their origin

2. **State View Slices**:
   - Every read model field has a source event
   - If derived data, ensure source data exists for calculation
   - No assumed data without verification

3. **Automation Slices**:
   - Trigger events are clearly defined
   - Read models provide all data needed for automation
   - Output events are stored in the system

**Red Flags**:
- Missing attribute sources
- Undefined event sources for read models
- Commands with data that has no origin
- Read models displaying data not in any event

**Next Steps**:
1. Review each slice for completeness
2. Add missing Given/When/Then scenarios for business rules
3. Define specific example data for all GWTs
4. Trace backward from read models to verify all data sources
5. Add error case scenarios for validations and constraints"""
