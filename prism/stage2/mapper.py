"""Stage 2.2d: ComponentMapper — converts HierarchyTree to typed PhysicalComponents.

Uses LayerCRUD registry to create typed components (TableComponent,
ListComponent, PhysicalComponent) from hierarchy nodes.
"""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    HierarchyNode,
    HierarchyTree,
    ListComponent,
    ListStyle,
    PhysicalComponent,
    TableComponent,
    TopologyConfig,
)
from prism.stage2.layers import get_crud


class ComponentMapper:
    """Convert HierarchyTree nodes to typed PhysicalComponent objects.

    Uses the LayerCRUD registry to create the correct component type
    for each layer (TableComponent for tables, ListComponent for lists,
    PhysicalComponent for everything else).

    Input:  HierarchyTree + TopologyConfig
    Output: list[PhysicalComponent]
    """

    @property
    def tier(self) -> str:
        return "orchestrator"

    @property
    def version(self) -> str:
        return "v1.0.0"

    def name(self) -> str:
        return "ComponentMapper"

    def map(
        self,
        tree: HierarchyTree,
        config: Optional[TopologyConfig] = None,
    ) -> list[PhysicalComponent]:
        """Convert hierarchy nodes to typed PhysicalComponent objects.

        Args:
            tree: HierarchyTree from HierarchyBuilder.
            config: Optional topology config.

        Returns:
            List of typed PhysicalComponent objects with parent-child
            relationships established via component_id references.
        """
        components: dict[str, PhysicalComponent] = {}

        # First pass: create all components
        for node in tree.root_nodes:
            self._process_node(node, components)

        # Special handling for TableComponent and ListComponent
        components = self._enrich_structured_components(components, tree)

        return list(components.values())

    def _process_node(
        self,
        node: "HierarchyNode",
        components: dict[str, PhysicalComponent],
    ) -> None:
        """Recursively process a hierarchy node and its children."""
        inst = node.instance
        comp = self._create_component(node)
        components[comp.component_id] = comp

        # Establish parent-child relationships
        child_ids = []
        for child in node.children:
            self._process_node(child, components)
            child_id = f"{child.instance.layer_type.value}:depth{child.instance.depth}_sib{child.instance.sibling_index}"
            child_ids.append(child_id)

        comp.children = child_ids
        if inst.parent_id is not None:
            comp.parent_id = inst.parent_id

    def _flatten(self, tree: HierarchyTree):
        """Flatten hierarchy tree into list of nodes in tree order."""
        return tree.flatten()

    def _create_component(self, node) -> PhysicalComponent:
        """Create a typed component from a hierarchy node."""
        inst = node.instance
        crud = get_crud(inst.layer_type)

        # Generate identifier matching the tree's ID format
        identifier = f"depth{inst.depth}_sib{inst.sibling_index}"

        if inst.layer_type == LayerType.TABLE:
            return crud.create(  # type: ignore[return-value]
                identifier=identifier,
                raw_content=inst.raw_content,
            )
        elif inst.layer_type == LayerType.LIST:
            style = inst.attributes.get("style", "unordered")
            return crud.create(  # type: ignore[return-value]
                identifier=identifier,
                raw_content=inst.raw_content,
                style=style,
            )
        elif inst.layer_type == LayerType.HEADING:
            level = int(inst.attributes.get("level", "1"))
            return crud.create(
                identifier=identifier,
                raw_content=inst.raw_content,
                level=level,
            )
        elif inst.layer_type == LayerType.CODE_BLOCK:
            language = inst.attributes.get("language", "")
            return crud.create(
                identifier=identifier,
                raw_content=inst.raw_content,
                language=language,
            )
        elif inst.layer_type == LayerType.BLOCKQUOTE:
            return crud.create(
                identifier=identifier,
                raw_content=inst.raw_content,
            )
        elif inst.layer_type == LayerType.FOOTNOTE:
            label = inst.attributes.get("label", "")
            return crud.create(
                identifier=identifier,
                raw_content=inst.raw_content,
                label=label,
            )
        elif inst.layer_type == LayerType.METADATA:
            return crud.create(
                identifier=identifier,
                raw_content=inst.raw_content,
            )
        elif inst.layer_type == LayerType.FIGURE:
            caption = inst.attributes.get("caption", "")
            src = inst.attributes.get("src", "")
            return crud.create(
                identifier=identifier,
                raw_content=inst.raw_content,
                caption=caption,
                src=src,
            )
        elif inst.layer_type == LayerType.DIAGRAM:
            diagram_type = inst.attributes.get("diagram_type", "")
            return crud.create(
                identifier=identifier,
                raw_content=inst.raw_content,
                diagram_type=diagram_type,
            )
        else:
            # Default: Paragraph
            return crud.create(
                identifier=identifier,
                raw_content=inst.raw_content,
            )

    def _enrich_structured_components(
        self,
        components: dict[str, PhysicalComponent],
        tree: HierarchyTree,
    ) -> dict[str, PhysicalComponent]:
        """Enrich TableComponent and ListComponent with structured data.

        For tables: parse rows/cells from raw_content.
        For lists: parse items from raw_content.
        """
        for comp_id, comp in list(components.items()):
            if isinstance(comp, TableComponent) and not comp.rows:
                comp = self._parse_table_structure(comp)
                components[comp_id] = comp
            elif isinstance(comp, ListComponent) and not comp.items:
                comp = self._parse_list_structure(comp)
                components[comp_id] = comp

        return components

    def _parse_table_structure(self, comp: TableComponent) -> TableComponent:
        """Parse table rows/cells from raw Markdown content."""
        from prism.schemas.physical import CellPosition, TableCell, TableRow

        lines = comp.raw_content.strip().split("\n")
        if len(lines) < 2:
            return comp

        # Find separator line (---|---|---)
        sep_idx = -1
        for i, line in enumerate(lines):
            if "|" in line and all(
                c in "-|: \t" for c in line.strip()
            ):
                sep_idx = i
                break

        if sep_idx == -1:
            return comp

        header_line = lines[0]
        data_lines = lines[sep_idx + 1 :]
        num_cols = header_line.count("|") - 1

        if num_cols < 1:
            return comp

        has_header = sep_idx == 1

        rows: list[TableRow] = []

        # Parse header row
        if has_header:
            cells = self._parse_table_row(header_line, 0, num_cols, is_header=True)
            rows.append(TableRow(row_index=0, cells=cells))

        # Parse data rows
        for row_idx, line in enumerate(data_lines, start=1 if has_header else 0):
            cells = self._parse_table_row(line, row_idx, num_cols)
            rows.append(TableRow(row_index=row_idx, cells=cells))

        # Build flat children list from all cells
        all_children: list[str] = []
        for row in rows:
            for cell in row.cells:
                all_children.extend(cell.children)

        comp.rows = rows
        comp.num_cols = num_cols
        comp.has_header = has_header
        comp.children = all_children

        return comp

    def _parse_table_row(
        self,
        line: str,
        row_idx: int,
        num_cols: int,
        is_header: bool = False,
    ):
        """Parse a single table row line into TableCell objects."""
        from prism.schemas.physical import CellPosition, TableCell

        # Split by | and strip whitespace
        parts = [p.strip() for p in line.split("|")]
        # Remove empty first/last parts from leading/trailing |
        if parts and parts[0] == "":
            parts = parts[1:]
        if parts and parts[-1] == "":
            parts = parts[:-1]

        cells: list[TableCell] = []
        for col_idx in range(num_cols):
            content = parts[col_idx] if col_idx < len(parts) else ""
            cells.append(
                TableCell(
                    position=CellPosition(
                        row=row_idx,
                        col=col_idx,
                        is_header=is_header,
                    ),
                    children=[],  # Would need token mapping to populate
                    char_start=None,
                    char_end=None,
                )
            )

        return cells

    def _parse_list_structure(self, comp: ListComponent) -> ListComponent:
        """Parse list items from raw Markdown content."""
        from prism.schemas.physical import ListItem

        lines = comp.raw_content.strip().split("\n")
        if not lines:
            return comp

        items: list[ListItem] = []
        current_item_lines: list[str] = []
        item_index = 0

        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith(("-", "*", "+")) or (
                stripped[0:1].isdigit() and stripped[1:2] in (".", ")")
            ):
                # Save previous item
                if current_item_lines:
                    items.append(
                        ListItem(
                            item_index=item_index,
                            children=[],
                        )
                    )
                    item_index += 1
                current_item_lines = [line]
            else:
                current_item_lines.append(line)

        # Don't forget last item
        if current_item_lines:
            items.append(
                ListItem(
                    item_index=item_index,
                    children=[],
                )
            )

        comp.items = items
        comp.children = []  # Would need token mapping to populate

        return comp

    def validate_input(
        self,
        tree: HierarchyTree,
    ) -> tuple[bool, str]:
        """Verify tree has nodes."""
        if tree.total_nodes == 0:
            return False, "Hierarchy tree is empty"
        return True, ""

    def validate_output(
        self,
        components: list[PhysicalComponent],
    ) -> tuple[bool, str]:
        """Verify output has at least one component."""
        if not components:
            return False, "No components mapped"
        return True, ""
