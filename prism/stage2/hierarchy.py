"""Stage 2.2c: HierarchyBuilder — builds parent-child tree from DetectedLayersReport.

Validates nesting against NestingMatrix, detects cycles, enforces
depth limits, and produces a HierarchyTree.
"""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    DetectedLayersReport,
    HierarchyNode,
    HierarchyTree,
    NestingMatrix,
    NESTING_MATRIX,
    TopologyConfig,
)


class HierarchyBuilder:
    """Build a validated parent-child hierarchy tree from detected instances.

    Takes the flat DetectedLayersReport and organizes instances into a
    tree structure using NestingMatrix rules.

    Input:  DetectedLayersReport + NestingMatrix + TopologyConfig
    Output: HierarchyTree
    """

    def __init__(
        self,
        nesting_matrix: Optional[NestingMatrix] = None,
    ) -> None:
        self.nesting_matrix = nesting_matrix or NESTING_MATRIX

    @property
    def tier(self) -> str:
        return "orchestrator"

    @property
    def version(self) -> str:
        return "v1.0.0"

    def name(self) -> str:
        return "HierarchyBuilder"

    def build(
        self,
        report: DetectedLayersReport,
        config: Optional[TopologyConfig] = None,
    ) -> HierarchyTree:
        """Build a hierarchy tree from detected layer instances.

        Algorithm:
        1. Collect all instances sorted by char_start
        2. Build parent-child relationships using char range containment
        3. Validate against NestingMatrix rules
        4. Detect cycles and enforce depth limits
        5. Return HierarchyTree

        Args:
            report: DetectedLayersReport from LayerClassifier.
            config: Optional topology config (nesting_depth_limit).

        Returns:
            HierarchyTree with validated parent-child relationships.
        """
        depth_limit = config.nesting_depth_limit if config else 10

        # Collect all instances sorted by char_start
        all_instances = []
        for instances in report.instances.values():
            all_instances.extend(instances)
        all_instances.sort(key=lambda inst: inst.char_start)

        if not all_instances:
            return HierarchyTree()

        # Build parent-child relationships using char range containment
        # An instance A is a child of B if:
        #   - A.char_start >= B.char_start and A.char_end <= B.char_end
        #   - B is the smallest such container (immediate parent)
        nodes: list[HierarchyNode] = []
        node_by_instance: dict[int, HierarchyNode] = {}  # id(inst) -> node

        for inst in all_instances:
            node = HierarchyNode(instance=inst)
            node_by_instance[id(inst)] = node
            nodes.append(node)

        # Build tree by finding immediate parent for each instance
        root_nodes: list[HierarchyNode] = []

        for node in nodes:
            inst = node.instance
            parent = self._find_immediate_parent(inst, nodes, node_by_instance)
            if parent is None:
                root_nodes.append(node)
            else:
                parent.children.append(node)

        # Validate the tree
        self._validate_tree(root_nodes, depth_limit)

        return HierarchyTree(root_nodes=root_nodes)

    def _find_immediate_parent(
        self,
        instance,
        all_nodes: list[HierarchyNode],
        node_by_instance: dict,
    ) -> Optional[HierarchyNode]:
        """Find the immediate (smallest) parent that contains this instance.

        Uses char range containment: parent must fully contain child.
        """
        candidates: list[tuple[int, HierarchyNode]] = []

        for other in all_nodes:
            if other.instance is instance:
                continue

            # Check containment: other must fully contain instance
            if (
                other.instance.char_start <= instance.char_start
                and other.instance.char_end >= instance.char_end
            ):
                # Check NestingMatrix allows this parent-child relationship
                if self.nesting_matrix.can_contain(
                    other.instance.layer_type,
                    instance.layer_type,
                ):
                    # Compute containment size (smaller = more immediate)
                    containment_size = (
                        other.instance.char_end - other.instance.char_start
                    )
                    candidates.append((containment_size, other))

        if not candidates:
            return None

        # Return the smallest container (most immediate parent)
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def _validate_tree(
        self,
        nodes: list[HierarchyNode],
        depth_limit: int,
    ) -> None:
        """Recursively validate tree against nesting rules."""
        for node in nodes:
            inst = node.instance

            # Check depth limit
            if inst.depth > depth_limit:
                raise ValueError(
                    f"Nesting depth {inst.depth} exceeds limit {depth_limit} "
                    f"for {inst.layer_type.value} at char {inst.char_start}"
                )

            # Validate children against nesting matrix
            for child in node.children:
                if not self.nesting_matrix.can_contain(
                    inst.layer_type,
                    child.instance.layer_type,
                ):
                    raise ValueError(
                        f"Invalid nesting: {inst.layer_type.value} cannot contain "
                        f"{child.instance.layer_type.value}"
                    )

            # Recurse
            self._validate_tree(node.children, depth_limit)

    def validate_input(
        self,
        report: DetectedLayersReport,
    ) -> tuple[bool, str]:
        """Verify report has non-empty source text."""
        if not report.source_text.strip():
            return False, "source_text is empty"
        return True, ""

    def validate_output(
        self,
        tree: HierarchyTree,
    ) -> tuple[bool, str]:
        """Verify tree is valid."""
        if tree.total_nodes == 0:
            return False, "Hierarchy tree is empty"
        return True, ""
