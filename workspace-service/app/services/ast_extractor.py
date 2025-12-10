"""
AST Extraction using Tree-sitter.

Extracts code metadata without LLM calls for:
- Function/method names
- Class definitions
- Import/export statements
- Type definitions

This runs on file upsert to provide semantic search metadata.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

try:
    import tree_sitter_languages
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


@dataclass
class ASTMetadata:
    """Extracted metadata from source code."""
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "functions": self.functions,
            "classes": self.classes,
            "imports": self.imports,
            "exports": self.exports,
            "types": self.types
        }


class ASTExtractor:
    """Extract code metadata using tree-sitter."""

    # Map file extensions to tree-sitter language names
    LANGUAGE_MAP = {
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "javascript",
        ".py": "python",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
    }

    def extract(self, file_path: str, content: str) -> Optional[ASTMetadata]:
        """Extract AST metadata from source code."""
        if not TREE_SITTER_AVAILABLE:
            # Return empty metadata if tree-sitter not available
            return ASTMetadata()

        ext = Path(file_path).suffix.lower()
        language_name = self.LANGUAGE_MAP.get(ext)

        if not language_name:
            return None  # Unsupported language

        try:
            parser = tree_sitter_languages.get_parser(language_name)
            tree = parser.parse(content.encode())

            if language_name in ("typescript", "tsx", "javascript"):
                return self._extract_typescript(tree, content)
            elif language_name == "python":
                return self._extract_python(tree, content)
            elif language_name == "go":
                return self._extract_go(tree, content)
            elif language_name == "rust":
                return self._extract_rust(tree, content)
            elif language_name == "java":
                return self._extract_java(tree, content)
            else:
                return self._extract_generic(tree, content)

        except Exception as e:
            print(f"AST extraction failed for {file_path}: {e}")
            return ASTMetadata()

    def _get_text(self, node, content: str) -> str:
        """Get the text content of a node."""
        return content[node.start_byte:node.end_byte]

    def _extract_typescript(self, tree, content: str) -> ASTMetadata:
        """Extract metadata from TypeScript/JavaScript."""
        metadata = ASTMetadata()
        root = tree.root_node

        def visit(node):
            # Functions
            if node.type in ("function_declaration", "method_definition"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.functions.append(self._get_text(name_node, content))

            # Arrow functions assigned to variables
            elif node.type == "variable_declarator":
                name_node = node.child_by_field_name("name")
                value_node = node.child_by_field_name("value")
                if name_node and value_node and value_node.type == "arrow_function":
                    metadata.functions.append(self._get_text(name_node, content))

            # Classes
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.classes.append(self._get_text(name_node, content))

            # Imports
            elif node.type == "import_statement":
                source = node.child_by_field_name("source")
                if source:
                    import_path = self._get_text(source, content).strip("'\"")
                    metadata.imports.append(import_path)

            # Exports
            elif node.type == "export_statement":
                declaration = node.child_by_field_name("declaration")
                if declaration:
                    name_node = declaration.child_by_field_name("name")
                    if name_node:
                        metadata.exports.append(self._get_text(name_node, content))

            # Type definitions
            elif node.type in ("type_alias_declaration", "interface_declaration"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.types.append(self._get_text(name_node, content))

            # Recurse
            for child in node.children:
                visit(child)

        visit(root)
        return metadata

    def _extract_python(self, tree, content: str) -> ASTMetadata:
        """Extract metadata from Python."""
        metadata = ASTMetadata()
        root = tree.root_node

        def visit(node):
            # Functions
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.functions.append(self._get_text(name_node, content))

            # Classes
            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.classes.append(self._get_text(name_node, content))

            # Imports
            elif node.type == "import_statement":
                for child in node.children:
                    if child.type == "dotted_name":
                        metadata.imports.append(self._get_text(child, content))

            elif node.type == "import_from_statement":
                module = node.child_by_field_name("module_name")
                if module:
                    metadata.imports.append(self._get_text(module, content))

            # Recurse
            for child in node.children:
                visit(child)

        visit(root)
        return metadata

    def _extract_go(self, tree, content: str) -> ASTMetadata:
        """Extract metadata from Go."""
        metadata = ASTMetadata()
        root = tree.root_node

        def visit(node):
            # Functions
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.functions.append(self._get_text(name_node, content))

            # Methods
            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.functions.append(self._get_text(name_node, content))

            # Types (struct, interface)
            elif node.type == "type_declaration":
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            metadata.types.append(self._get_text(name_node, content))

            # Imports
            elif node.type == "import_declaration":
                for child in node.children:
                    if child.type == "import_spec":
                        path_node = child.child_by_field_name("path")
                        if path_node:
                            metadata.imports.append(self._get_text(path_node, content).strip('"'))

            # Recurse
            for child in node.children:
                visit(child)

        visit(root)
        return metadata

    def _extract_rust(self, tree, content: str) -> ASTMetadata:
        """Extract metadata from Rust."""
        metadata = ASTMetadata()
        root = tree.root_node

        def visit(node):
            # Functions
            if node.type == "function_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.functions.append(self._get_text(name_node, content))

            # Structs
            elif node.type == "struct_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.classes.append(self._get_text(name_node, content))

            # Enums
            elif node.type == "enum_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.types.append(self._get_text(name_node, content))

            # Traits
            elif node.type == "trait_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.types.append(self._get_text(name_node, content))

            # Use statements (imports)
            elif node.type == "use_declaration":
                metadata.imports.append(self._get_text(node, content))

            # Recurse
            for child in node.children:
                visit(child)

        visit(root)
        return metadata

    def _extract_java(self, tree, content: str) -> ASTMetadata:
        """Extract metadata from Java."""
        metadata = ASTMetadata()
        root = tree.root_node

        def visit(node):
            # Methods
            if node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.functions.append(self._get_text(name_node, content))

            # Classes
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.classes.append(self._get_text(name_node, content))

            # Interfaces
            elif node.type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    metadata.types.append(self._get_text(name_node, content))

            # Imports
            elif node.type == "import_declaration":
                for child in node.children:
                    if child.type == "scoped_identifier":
                        metadata.imports.append(self._get_text(child, content))

            # Recurse
            for child in node.children:
                visit(child)

        visit(root)
        return metadata

    def _extract_generic(self, tree, content: str) -> ASTMetadata:
        """Basic extraction for unsupported languages."""
        return ASTMetadata()


# Language detection utility
def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".py": "python",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sql": "sql",
    }
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, "unknown")
