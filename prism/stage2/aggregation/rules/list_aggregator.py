"""List Aggregator — Structured list index with nesting hierarchy.

Builds list matrix, item counting, nesting tree from markdown-it-py AST.
Reliability: 100% — AST tokens are explicit.
"""

from __future__ import annotations

from prism.schemas.physical import MarkdownNode, NodeType
from prism.stage2.aggregation.aggregation_models import (
    ListIndex,
    ListItemIndex,
    NestedItem,
)


class ListAggregator:
    """Builds structured list index from markdown-it-py AST nodes."""

    # ------------------------------------------------------------------
    # IAggregator Protocol
    # ------------------------------------------------------------------

    def aggregate(self, input_data: list[MarkdownNode]) -> list[ListIndex]:
        return self._parse_lists(input_data)

    def validate_input(self, input_data: list[MarkdownNode]) -> tuple[bool, str]:
        if not isinstance(input_data, list):
            return False, "Input must be a list of MarkdownNode"
        return True, ""

    def validate_output(self, output_data: list[ListIndex]) -> tuple[bool, str]:
        for li in output_data:
            if not li.component_id:
                return False, "ListIndex must have component_id"
            if li.total_items < li.top_level_items:
                return False, "total_items must be >= top_level_items"
        return True, ""

    def name(self) -> str:
        return "ListAggregator"

    @property
    def tier(self) -> str:
        return "rules"

    @property
    def version(self) -> str:
        return "1.0.0"

    # ------------------------------------------------------------------
    # Implementation
    # ------------------------------------------------------------------

    def _parse_lists(self, nodes: list[MarkdownNode]) -> list[ListIndex]:
        """Extract list indices from AST nodes."""
        results = []
        for node in nodes:
            if node.node_type == NodeType.LIST:
                list_index = self._parse_single_list(node)
                results.append(list_index)
            # Recurse into children
            if node.children:
                results.extend(self._parse_lists(node.children))
        return results

    def _parse_single_list(self, list_node: MarkdownNode) -> ListIndex:
        """Parse a single list node into ListIndex."""
        # Detect style from attributes or content
        style = list_node.attributes.get("style", "unordered")
        if "ordered" in style.lower() or list_node.node_type.value == "ordered_list":
            style = "ordered"
        else:
            style = "unordered"

        # Extract items
        items = self._extract_items(list_node)
        total_items = len(items)

        # Count top-level items (depth 0)
        top_level = [i for i in items if i.depth == 0]
        top_level_items = len(top_level)

        # Calculate max depth
        max_depth = max((i.depth for i in items), default=0)

        # Build nesting tree
        nesting_tree = self._build_nesting_tree(items)

        # Extract indentation levels
        indent_levels = sorted(set(range(max_depth + 1)))

        return ListIndex(
            component_id=list_node.attributes.get("component_id", f"list:{id(list_node)}"),
            style=style,
            total_items=total_items,
            top_level_items=top_level_items,
            max_depth=max_depth,
            items=items,
            nesting_tree=nesting_tree,
            indentation_levels=indent_levels,
        )

    def _extract_items(self, list_node: MarkdownNode) -> list[ListItemIndex]:
        """Extract list items from list node and its children."""
        items = []

        for child in list_node.children:
            if child.node_type == NodeType.LIST_ITEM:
                item = self._parse_list_item(child, depth=0)
                items.extend(item)
            elif child.node_type == NodeType.LIST:
                # Nested list — parse with depth+1
                nested_items = self._parse_single_list(child).items
                for ni in nested_items:
                    ni.depth += 1
                    items.append(ni)

        # Assign sequential indices
        for i, item in enumerate(items):
            item.item_index = i

        return items

    def _parse_list_item(
        self, item_node: MarkdownNode, depth: int = 0
    ) -> list[ListItemIndex]:
        """Parse a single list item and its nested content."""
        item = ListItemIndex(
            item_index=0,  # Will be assigned later
            depth=depth,
            text=item_node.raw_content.strip(),
            has_children=False,
        )
        items = [item]

        # Check for nested lists
        for child in item_node.children:
            if child.node_type == NodeType.LIST:
                item.has_children = True
                nested = self._extract_items(child)
                for ni in nested:
                    ni.depth = depth + 1
                    items.append(ni)

        return items

    def _build_nesting_tree(self, items: list[ListItemIndex]) -> list[NestedItem]:
        """Build hierarchical nesting tree from flat item list."""
        if not items:
            return []

        tree: list[NestedItem] = []
        stack: list[tuple[int, NestedItem]] = []  # (depth, node)

        for item in items:
            node = NestedItem(item=item, children=[])

            # Pop stack until we find parent at depth-1
            while stack and stack[-1][0] >= item.depth:
                stack.pop()

            if stack:
                stack[-1][1].children.append(node)
            else:
                tree.append(node)

            stack.append((item.depth, node))

        return tree
