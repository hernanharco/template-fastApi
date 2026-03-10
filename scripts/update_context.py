#!/usr/bin/env python3
"""
Script para actualizar CONTEXT.md automáticamente analizando el codebase.

Uso:
    python scripts/update_context.py

Este script:
1. Analiza models/ para detectar entidades SQLAlchemy
2. Analiza agents/ para detectar nodos y schemas Pydantic
3. Analiza api/ para detectar endpoints
4. Actualiza las secciones correspondientes en CONTEXT.md
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class ModelInfo:
    name: str
    table_name: str
    fields: List[str]
    relationships: List[str]


@dataclass
class SchemaInfo:
    name: str
    module: str
    fields: List[str]


@dataclass
class NodeInfo:
    name: str
    file_path: str
    description: str = ""


@dataclass
class EndpointInfo:
    path: str
    method: str
    description: str = ""


class ContextAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.models: List[ModelInfo] = []
        self.schemas: List[SchemaInfo] = []
        self.nodes: List[NodeInfo] = []
        self.endpoints: List[EndpointInfo] = []

    def analyze_models(self) -> None:
        """Analiza app/models/ para encontrar modelos SQLAlchemy"""
        models_dir = self.project_root / "app" / "models"

        for py_file in models_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content)
                self._extract_models_from_ast(tree, py_file)
            except SyntaxError as e:
                print(f"⚠️ Error parsing {py_file}: {e}")

    def _extract_models_from_ast(self, tree: ast.AST, file_path: Path) -> None:
        """Extrae información de modelos del AST"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Buscar si hereda de Base
                if self._inherits_from_base(node):
                    model_info = self._analyze_model_class(node, file_path)
                    if model_info:
                        self.models.append(model_info)

    def _inherits_from_base(self, class_node: ast.ClassDef) -> bool:
        """Verifica si la clase hereda de SQLAlchemy Base"""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "Base":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "Base":
                return True
        return False

    def _analyze_model_class(
        self, class_node: ast.ClassDef, file_path: Path
    ) -> ModelInfo:
        """Analiza una clase de modelo SQLAlchemy"""
        name = class_node.name
        table_name = name.lower() + "s"  # Convención por defecto
        fields = []
        relationships = []

        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_name = target.id

                        # Detectar Column de SQLAlchemy
                        if self._is_sqlalchemy_column(item):
                            fields.append(field_name)

                        # Detectar relationships
                        elif self._is_relationship(item):
                            relationships.append(field_name)

            # Detectar __tablename__
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant):
                            table_name = item.value.value

        return ModelInfo(
            name=name, table_name=table_name, fields=fields, relationships=relationships
        )

    def _is_sqlalchemy_column(self, node: ast.Assign) -> bool:
        """Verifica si es una Column de SQLAlchemy"""
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == "Column":
                return True
        return False

    def _is_relationship(self, node: ast.Assign) -> bool:
        """Verifica si es un relationship de SQLAlchemy"""
        if isinstance(node.value, ast.Call):
            if (
                isinstance(node.value.func, ast.Name)
                and node.value.func.id == "relationship"
            ):
                return True
        return False

    def analyze_schemas(self) -> None:
        """Analiza app/schemas/ y app/agents/schemas/ para encontrar modelos Pydantic"""
        schema_dirs = [
            self.project_root / "app" / "schemas",
            self.project_root / "app" / "agents" / "schemas",
        ]

        for schema_dir in schema_dirs:
            if not schema_dir.exists():
                continue

            for py_file in schema_dir.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue

                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                try:
                    tree = ast.parse(content)
                    self._extract_schemas_from_ast(tree, py_file)
                except SyntaxError as e:
                    print(f"⚠️ Error parsing schema {py_file}: {e}")

    def _extract_schemas_from_ast(self, tree: ast.AST, file_path: Path) -> None:
        """Extrae información de schemas Pydantic del AST"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._inherits_from_pydantic(node):
                    schema_info = self._analyze_schema_class(node, file_path)
                    if schema_info:
                        self.schemas.append(schema_info)

    def _inherits_from_pydantic(self, class_node: ast.ClassDef) -> bool:
        """Verifica si la clase hereda de BaseModel de Pydantic"""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
        return False

    def _analyze_schema_class(
        self, class_node: ast.ClassDef, file_path: Path
    ) -> SchemaInfo:
        """Analiza una clase de schema Pydantic"""
        name = class_node.name
        module = file_path.stem
        fields = []

        for item in class_node.body:
            if isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    fields.append(item.target.id)

        return SchemaInfo(name=name, module=module, fields=fields)

    def analyze_nodes(self) -> None:
        """Analiza app/agents/nodes/ para encontrar nodos de LangGraph"""
        nodes_dir = self.project_root / "app" / "agents" / "nodes"

        for py_file in nodes_dir.glob("*_node.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extraer nombre del nodo del nombre del archivo
            node_name = py_file.stem.replace("_node", "")

            # Buscar función principal del nodo
            node_func = self._find_node_function(content)
            if node_func:
                description = self._extract_function_docstring(node_func)
            else:
                description = ""

            self.nodes.append(
                NodeInfo(
                    name=node_name,
                    file_path=str(py_file.relative_to(self.project_root)),
                    description=description,
                )
            )

    def _find_node_function(self, content: str) -> ast.FunctionDef:
        """Busca la función principal del nodo"""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Generalmente la función del nodo tiene el mismo nombre que el archivo
                    if "node" in node.name:
                        return node
        except SyntaxError:
            pass
        return None

    def _extract_function_docstring(self, func_node: ast.FunctionDef) -> str:
        """Extrae el docstring de una función"""
        if (
            func_node.body
            and isinstance(func_node.body[0], ast.Expr)
            and isinstance(func_node.body[0].value, ast.Constant)
        ):
            return func_node.body[0].value.value
        return ""

    def analyze_endpoints(self) -> None:
        """Analiza app/api/ para encontrar endpoints FastAPI"""
        api_dir = self.project_root / "app" / "api"

        for py_file in api_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            self._extract_endpoints_from_content(content, py_file)

    def _extract_endpoints_from_content(self, content: str, file_path: Path) -> None:
        """Extrae endpoints del contenido del archivo"""
        # Buscar decoradores @app.get, @app.post, etc.
        decorator_pattern = (
            r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        )
        matches = re.findall(decorator_pattern, content)

        for method, path in matches:
            self.endpoints.append(
                EndpointInfo(
                    path=path,
                    method=method.upper(),
                    description=f"Endpoint en {file_path.name}",
                )
            )

    def generate_markdown_sections(self) -> Dict[str, str]:
        """Genera las secciones de Markdown para CONTEXT.md"""
        sections = {}

        # Sección de Modelos
        if self.models:
            models_md = "### Entidades Principales\n\n"
            for model in self.models:
                models_md += f"#### {model.name}\n"
                models_md += f"```python\n"
                models_md += f"class {model.name}(Base):\n"
                for field in model.fields:
                    models_md += f"    {field}: ...\n"
                if model.relationships:
                    models_md += "\n    # Relaciones\n"
                    for rel in model.relationships:
                        models_md += f"    {rel}: ...\n"
                models_md += "```\n\n"
            sections["models"] = models_md

        # Sección de Schemas
        if self.schemas:
            schemas_md = "### Schemas de Agentes\n\n"
            for schema in self.schemas:
                schemas_md += f"- **{schema.name}** ({schema.module})\n"
            schemas_md += "\n"
            sections["schemas"] = schemas_md

        # Sección de Nodos
        if self.nodes:
            nodes_md = "### Nodos del Sistema\n\n"
            for i, node in enumerate(self.nodes, 1):
                description = (
                    node.description if node.description else f"Nodo de {node.name}"
                )
                nodes_md += f"{i}. **{node.name}_node**: {description}\n"
            nodes_md += "\n"
            sections["nodes"] = nodes_md

        # Sección de Endpoints
        if self.endpoints:
            endpoints_md = "### Endpoints API Principales\n\n"
            for endpoint in self.endpoints:
                endpoints_md += (
                    f"- `{endpoint.method} {endpoint.path}` - {endpoint.description}\n"
                )
            endpoints_md += "\n"
            sections["endpoints"] = endpoints_md

        return sections

    def update_context_file(self) -> None:
        """Actualiza el archivo CONTEXT.md manteniendo el resto del contenido"""
        context_file = self.project_root / "CONTEXT.md"

        if not context_file.exists():
            print("❌ No se encontró CONTEXT.md")
            return

        # Leer contenido actual
        with open(context_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Generar nuevas secciones
        new_sections = self.generate_markdown_sections()

        # Actualizar secciones específicas con patrones más precisos
        for section_name, section_content in new_sections.items():
            if section_name == "models":
                # Reemplazar todo el contenido desde "### Entidades Principales" hasta el próximo ##
                pattern = r"### Entidades Principales.*?(?=\n## |\Z)"
                replacement = f"### Entidades Principales\n\n{section_content}"
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)

            elif section_name == "schemas":
                # Buscar y reemplazar sección de schemas
                pattern = r"### Schemas de Agentes.*?(?=\n## |\Z)"
                replacement = f"### Schemas de Agentes\n\n{section_content}"
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)

            elif section_name == "nodes":
                # Buscar y reemplazar sección de nodos
                pattern = r"### Nodos del Sistema.*?(?=\n## |\Z)"
                replacement = f"### Nodos del Sistema\n\n{section_content}"
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)

            elif section_name == "endpoints":
                # Buscar y reemplazar sección de endpoints
                pattern = r"### Endpoints API Principales.*?(?=\n## |\Z)"
                replacement = f"### Endpoints API Principales\n\n{section_content}"
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        # Escribir archivo actualizado
        with open(context_file, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ CONTEXT.md actualizado exitosamente")


def main():
    """Función principal del script"""
    project_root = Path(__file__).parent.parent

    print("🔍 Analizando codebase para actualizar CONTEXT.md...")

    analyzer = ContextAnalyzer(project_root)

    print("📊 Analizando modelos SQLAlchemy...")
    analyzer.analyze_models()

    print("📋 Analizando schemas Pydantic...")
    analyzer.analyze_schemas()

    print("🤖 Analizando nodos de LangGraph...")
    analyzer.analyze_nodes()

    print("🌐 Analizando endpoints API...")
    analyzer.analyze_endpoints()

    print("📝 Actualizando CONTEXT.md...")
    analyzer.update_context_file()

    # Resumen
    print(f"\n📈 Resumen del análisis:")
    print(f"   • Modelos encontrados: {len(analyzer.models)}")
    print(f"   • Schemas encontrados: {len(analyzer.schemas)}")
    print(f"   • Nodos encontrados: {len(analyzer.nodes)}")
    print(f"   • Endpoints encontrados: {len(analyzer.endpoints)}")


if __name__ == "__main__":
    main()
