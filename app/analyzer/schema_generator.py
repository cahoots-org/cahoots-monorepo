"""Schema Generator

Generates database schemas from domain events, state machines, and CQRS analysis.
Creates entity models, relationships, and migration scripts.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from app.analyzer.event_extractor import DomainEvent
from app.analyzer.state_machine_detector import StateMachine
from app.analyzer.cqrs_detector import CQRSAnalysis
from app.analyzer.llm_client import LLMClient


@dataclass
class Field:
    """Database field/column"""
    name: str
    type: str  # e.g., "string", "integer", "boolean", "datetime", "uuid"
    nullable: bool = False
    unique: bool = False
    default: Optional[str] = None
    foreign_key: Optional[str] = None  # "table.column"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Entity:
    """Database entity/table"""
    name: str
    fields: List[Field] = field(default_factory=list)
    indexes: List[List[str]] = field(default_factory=list)  # Composite indexes
    relationships: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaAnalysis:
    """Complete schema analysis"""
    entities: List[Entity] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    event_store_schema: Optional[Entity] = None  # For event sourcing
    metadata: Dict[str, Any] = field(default_factory=dict)


class SchemaGenerator:
    """Generates database schemas from domain analysis"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def generate_schema(
        self,
        events: List[DomainEvent],
        state_machines: Optional[List[StateMachine]] = None,
        cqrs_analysis: Optional[CQRSAnalysis] = None
    ) -> SchemaAnalysis:
        """
        Generate database schema from domain analysis.

        Args:
            events: List of domain events
            state_machines: Optional state machine analysis
            cqrs_analysis: Optional CQRS analysis

        Returns:
            Schema analysis with entities and relationships
        """
        if not events:
            return SchemaAnalysis()

        # Extract entities from events
        entities_mentioned = set()
        for event in events:
            if event.affected_entity:
                entities_mentioned.add(event.affected_entity)

        # Build context for LLM
        context = {
            "events": [
                {
                    "name": e.name,
                    "type": e.event_type.value,
                    "description": e.description,
                    "affected_entity": e.affected_entity
                }
                for e in events
            ],
            "entities": list(entities_mentioned),
            "state_machines": []
        }

        if state_machines:
            context["state_machines"] = [
                {
                    "entity": sm.entity,
                    "states": list(sm.states),
                    "has_status_field": True
                }
                for sm in state_machines
            ]

        if cqrs_analysis:
            context["commands"] = [
                {
                    "name": cmd.name,
                    "input_data": cmd.input_data,
                    "affects_entities": cmd.affects_entities
                }
                for cmd in cqrs_analysis.commands
            ]

        prompt = f"""Based on this domain analysis, design a database schema.

Context:
{context}

For each entity, provide:
- Entity/table name (singular, PascalCase)
- Fields with:
  - name (snake_case)
  - type (uuid, string, integer, boolean, datetime, decimal, json)
  - nullable (true/false)
  - unique (true/false)
  - default value (if applicable)
  - foreign_key (table.column if applicable)
- Indexes (arrays of field names for composite indexes)
- Relationships (type, target_entity, through_table if many-to-many)

Include standard fields:
- id (uuid, primary key)
- created_at (datetime)
- updated_at (datetime)

For entities with state machines, add:
- status field (enum/string)
- status_changed_at (datetime)

Format as JSON:
{{
  "entities": [
    {{
      "name": "User",
      "fields": [
        {{"name": "id", "type": "uuid", "nullable": false, "unique": true}},
        {{"name": "email", "type": "string", "nullable": false, "unique": true}},
        {{"name": "name", "type": "string", "nullable": false}},
        {{"name": "created_at", "type": "datetime", "nullable": false}},
        {{"name": "updated_at", "type": "datetime", "nullable": false}}
      ],
      "indexes": [["email"], ["created_at"]],
      "relationships": [
        {{"type": "has_many", "target": "Order", "foreign_key": "user_id"}}
      ]
    }}
  ],
  "relationships": [
    {{"type": "one_to_many", "from": "User", "to": "Order", "foreign_key": "user_id"}}
  ],
  "event_store": {{
    "name": "DomainEvent",
    "fields": [
      {{"name": "id", "type": "uuid", "nullable": false, "unique": true}},
      {{"name": "event_type", "type": "string", "nullable": false}},
      {{"name": "aggregate_id", "type": "uuid", "nullable": false}},
      {{"name": "aggregate_type", "type": "string", "nullable": false}},
      {{"name": "payload", "type": "json", "nullable": false}},
      {{"name": "occurred_at", "type": "datetime", "nullable": false}}
    ],
    "indexes": [["aggregate_id"], ["event_type"], ["occurred_at"]]
  }}
}}
"""

        try:
            response = await self.llm.chat_completion([
                {"role": "user", "content": prompt}
            ])

            # Extract content from response
            import json
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                data = self.llm._parse_json(content)
            elif isinstance(response, dict):
                data = response
            else:
                data = json.loads(response.strip())

            # Build Entity objects
            entities = []
            for entity_data in data.get("entities", []):
                fields = []
                for field_data in entity_data.get("fields", []):
                    field = Field(
                        name=field_data["name"],
                        type=field_data["type"],
                        nullable=field_data.get("nullable", False),
                        unique=field_data.get("unique", False),
                        default=field_data.get("default"),
                        foreign_key=field_data.get("foreign_key")
                    )
                    fields.append(field)

                entity = Entity(
                    name=entity_data["name"],
                    fields=fields,
                    indexes=entity_data.get("indexes", []),
                    relationships=entity_data.get("relationships", [])
                )
                entities.append(entity)

            # Build event store schema if present
            event_store = None
            if "event_store" in data:
                es_data = data["event_store"]
                fields = []
                for field_data in es_data.get("fields", []):
                    field = Field(
                        name=field_data["name"],
                        type=field_data["type"],
                        nullable=field_data.get("nullable", False),
                        unique=field_data.get("unique", False)
                    )
                    fields.append(field)

                event_store = Entity(
                    name=es_data["name"],
                    fields=fields,
                    indexes=es_data.get("indexes", [])
                )

            analysis = SchemaAnalysis(
                entities=entities,
                relationships=data.get("relationships", []),
                event_store_schema=event_store,
                metadata={
                    "total_entities": len(entities),
                    "has_event_store": event_store is not None
                }
            )

            return analysis

        except Exception as e:
            import traceback
            print(f"Error generating schema: {e}")
            traceback.print_exc()
            return SchemaAnalysis()

    def generate_sql_ddl(self, schema: SchemaAnalysis, dialect: str = "postgresql") -> str:
        """Generate SQL DDL from schema"""
        lines = [f"-- Generated Schema ({dialect})", ""]

        # Map types to SQL
        type_map = {
            "uuid": "UUID",
            "string": "VARCHAR(255)",
            "integer": "INTEGER",
            "boolean": "BOOLEAN",
            "datetime": "TIMESTAMP",
            "decimal": "DECIMAL(10,2)",
            "json": "JSONB" if dialect == "postgresql" else "JSON"
        }

        # Generate tables
        for entity in schema.entities:
            lines.append(f"CREATE TABLE {entity.name.lower()}s (")

            # Fields
            field_lines = []
            for field in entity.fields:
                sql_type = type_map.get(field.type, "VARCHAR(255)")
                constraints = []

                if not field.nullable:
                    constraints.append("NOT NULL")
                if field.unique:
                    constraints.append("UNIQUE")
                if field.default:
                    constraints.append(f"DEFAULT {field.default}")
                if field.foreign_key:
                    table, column = field.foreign_key.split(".")
                    constraints.append(f"REFERENCES {table}({column})")

                constraint_str = " " + " ".join(constraints) if constraints else ""
                field_lines.append(f"  {field.name} {sql_type}{constraint_str}")

            # Primary key
            field_lines.append("  PRIMARY KEY (id)")

            lines.append(",\n".join(field_lines))
            lines.append(");")
            lines.append("")

            # Indexes
            for idx in entity.indexes:
                idx_name = f"idx_{entity.name.lower()}_{'_'.join(idx)}"
                idx_cols = ", ".join(idx)
                lines.append(f"CREATE INDEX {idx_name} ON {entity.name.lower()}s ({idx_cols});")

            lines.append("")

        # Event store
        if schema.event_store_schema:
            es = schema.event_store_schema
            lines.append(f"-- Event Store")
            lines.append(f"CREATE TABLE {es.name.lower()}s (")

            field_lines = []
            for field in es.fields:
                sql_type = type_map.get(field.type, "VARCHAR(255)")
                constraints = " NOT NULL" if not field.nullable else ""
                field_lines.append(f"  {field.name} {sql_type}{constraints}")

            field_lines.append("  PRIMARY KEY (id)")
            lines.append(",\n".join(field_lines))
            lines.append(");")
            lines.append("")

            for idx in es.indexes:
                idx_name = f"idx_{es.name.lower()}_{'_'.join(idx)}"
                idx_cols = ", ".join(idx)
                lines.append(f"CREATE INDEX {idx_name} ON {es.name.lower()}s ({idx_cols});")

        return "\n".join(lines)

    def generate_prisma_schema(self, schema: SchemaAnalysis) -> str:
        """Generate Prisma schema"""
        lines = ["// Generated Prisma Schema", "", "datasource db {", "  provider = \"postgresql\"", "  url      = env(\"DATABASE_URL\")", "}", "", "generator client {", "  provider = \"prisma-client-js\"", "}", ""]

        # Map types to Prisma
        type_map = {
            "uuid": "String @id @default(uuid())",
            "string": "String",
            "integer": "Int",
            "boolean": "Boolean",
            "datetime": "DateTime",
            "decimal": "Decimal",
            "json": "Json"
        }

        for entity in schema.entities:
            lines.append(f"model {entity.name} {{")

            for field in entity.fields:
                prisma_type = type_map.get(field.type, "String")
                optional = "?" if field.nullable else ""
                unique = " @unique" if field.unique else ""
                default = f" @default({field.default})" if field.default else ""

                if field.name == "id":
                    lines.append(f"  {field.name} String @id @default(uuid())")
                else:
                    lines.append(f"  {field.name} {prisma_type}{optional}{unique}{default}")

            # Relationships
            for rel in entity.relationships:
                if rel["type"] == "has_many":
                    lines.append(f"  {rel['target'].lower()}s {rel['target']}[]")

            lines.append("}")
            lines.append("")

        return "\n".join(lines)
