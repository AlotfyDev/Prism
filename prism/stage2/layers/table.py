"""CRUD operations for TableComponent."""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    CellPosition,
    PhysicalComponent,
    TableComponent,
    TableCell,
    TableRow,
)

from prism.stage2.layers.base import LayerCRUD, LayerRegistry


class TableCRUD(LayerCRUD[TableComponent]):
    """CRUD operations for table components.

    Provides table-specific operations: rows, cells, headers,
    plus all common PhysicalComponent operations from LayerCRUD.

    Usage:
        crud = TableCRUD()
        table = crud.create("tbl1", "| A | B |\\n| 1 | 2 |")
        crud.add_row(table, row_index=0)
        crud.add_cell(table, 0, col=0, is_header=True)
        crud.add_cell(table, 0, col=1, is_header=True)
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.TABLE

    def create(
        self,
        identifier: str,
        raw_content: str,
        has_header: bool = False,
        num_cols: int = 0,
    ) -> TableComponent:
        """Create a new TableComponent.

        Args:
            identifier: Short ID (e.g. "tbl1").
            raw_content: Raw Markdown table text.
            has_header: Whether first row is a header.
            num_cols: Column count (0 = auto-detect from rows).

        Returns:
            A new TableComponent.
        """
        return TableComponent(
            component_id=f"table:{identifier}",
            layer_type=LayerType.TABLE,
            raw_content=raw_content,
            has_header=has_header,
            num_cols=num_cols,
            children=[],
            rows=[],
        )

    def add_row(
        self,
        table: TableComponent,
        row_index: Optional[int] = None,
    ) -> TableRow:
        """Add an empty row to the table.

        Args:
            table: The table component.
            row_index: Explicit row index. None = auto-append.

        Returns:
            The newly created TableRow.

        Raises:
            ValueError: If row_index is already used.
        """
        existing_indices = {r.row_index for r in table.rows}

        if row_index is None:
            if not table.rows:
                row_index = 0
            else:
                row_index = max(r.row_index for r in table.rows) + 1

        if row_index in existing_indices:
            raise ValueError(
                f"Row index {row_index} already exists in table {table.component_id}"
            )

        row = TableRow(row_index=row_index, cells=[])
        table.rows.append(row)

        # Auto-sort by row_index
        table.rows.sort(key=lambda r: r.row_index)
        return row

    def remove_row(
        self,
        table: TableComponent,
        row_index: int,
    ) -> TableComponent:
        """Remove a row and all its cells from the table.

        Args:
            table: The table component.
            row_index: Index of the row to remove.

        Returns:
            Updated table.

        Raises:
            ValueError: If row not found.
        """
        for row in table.rows:
            if row.row_index == row_index:
                # Remove child references from table's flat children
                for cell in row.cells:
                    for child_id in cell.children:
                        if child_id in table.children:
                            table.children.remove(child_id)
                table.rows.remove(row)
                return table

        raise ValueError(
            f"Row {row_index} not found in table {table.component_id}"
        )

    def add_cell(
        self,
        table: TableComponent,
        row_index: int,
        col: int,
        is_header: bool = False,
    ) -> TableCell:
        """Add a cell to a specific row.

        Args:
            table: The table component.
            row_index: Target row index.
            col: Column index within the row.
            is_header: Whether this cell is in the header row.

        Returns:
            The newly created TableCell.

        Raises:
            ValueError: If row not found, or col already exists.
        """
        row = self.get_row(table, row_index)
        existing_cols = {c.position.col for c in row.cells}

        if col in existing_cols:
            raise ValueError(
                f"Cell at ({row_index}, {col}) already exists in table {table.component_id}"
            )

        cell = TableCell(
            position=CellPosition(
                row=row_index,
                col=col,
                is_header=is_header,
            ),
            children=[],
        )
        row.cells.append(cell)
        row.cells.sort(key=lambda c: c.position.col)
        return cell

    def remove_cell(
        self,
        table: TableComponent,
        row_index: int,
        col: int,
    ) -> TableComponent:
        """Remove a cell from a row.

        Args:
            table: The table component.
            row_index: Row index.
            col: Column index.

        Returns:
            Updated table.

        Raises:
            ValueError: If cell not found.
        """
        row = self.get_row(table, row_index)
        for cell in row.cells:
            if cell.position.col == col:
                # Remove child references from table's flat children
                for child_id in cell.children:
                    if child_id in table.children:
                        table.children.remove(child_id)
                row.cells.remove(cell)
                return table

        raise ValueError(
            f"Cell at ({row_index}, {col}) not found in table {table.component_id}"
        )

    def get_row(
        self,
        table: TableComponent,
        row_index: int,
    ) -> TableRow:
        """Get a row by its index.

        Raises:
            ValueError: If row not found.
        """
        for row in table.rows:
            if row.row_index == row_index:
                return row
        raise ValueError(
            f"Row {row_index} not found in table {table.component_id}"
        )

    def get_cell(
        self,
        table: TableComponent,
        row_index: int,
        col: int,
    ) -> TableCell:
        """Get a cell by row and column.

        Raises:
            ValueError: If cell not found.
        """
        row = self.get_row(table, row_index)
        for cell in row.cells:
            if cell.position.col == col:
                return cell
        raise ValueError(
            f"Cell at ({row_index}, {col}) not found in table {table.component_id}"
        )

    def add_child_to_cell(
        self,
        table: TableComponent,
        row_index: int,
        col: int,
        child_id: str,
        child_type: LayerType,
    ) -> TableComponent:
        """Add a child component to a specific cell.

        Validates against NestingMatrix (what can a table cell contain).

        Args:
            table: The table component.
            row_index: Target row.
            col: Target column.
            child_id: Child component_id.
            child_type: Child LayerType.

        Returns:
            Updated table.
        """
        cell = self.get_cell(table, row_index, col)

        if child_id in cell.children:
            raise ValueError(
                f"Child '{child_id}' already in cell ({row_index}, {col})"
            )

        cell.children.append(child_id)
        if child_id not in table.children:
            table.children.append(child_id)
        return table

    def remove_child_from_cell(
        self,
        table: TableComponent,
        row_index: int,
        col: int,
        child_id: str,
    ) -> TableComponent:
        """Remove a child component from a specific cell.

        Args:
            table: The table component.
            row_index: Target row.
            col: Target column.
            child_id: Child component_id to remove.

        Returns:
            Updated table.
        """
        cell = self.get_cell(table, row_index, col)

        if child_id not in cell.children:
            raise ValueError(
                f"Child '{child_id}' not in cell ({row_index}, {col})"
            )

        cell.children.remove(child_id)
        if child_id not in table.children:
            pass
        return table

    def set_header(
        self,
        table: TableComponent,
        has_header: bool = True,
    ) -> TableComponent:
        """Mark/unmark the first row as header.

        Updates is_header flag on all cells in the first row.

        Args:
            table: The table component.
            has_header: Whether first row is a header.

        Returns:
            Updated table.
        """
        table.has_header = has_header

        if table.rows:
            first_row = table.rows[0]
            for cell in first_row.cells:
                cell.position.is_header = has_header

        return table

    def get_row_count(self, table: TableComponent) -> int:
        """Return number of rows."""
        return len(table.rows)

    def get_col_count(self, table: TableComponent) -> int:
        """Return number of columns (from first row)."""
        if not table.rows:
            return 0
        return len(table.rows[0].cells)

    def get_cell_children(
        self,
        table: TableComponent,
        row_index: int,
        col: int,
    ) -> list[str]:
        """Get child component IDs for a specific cell."""
        cell = self.get_cell(table, row_index, col)
        return list(cell.children)

    def all_cell_children(
        self,
        table: TableComponent,
    ) -> dict[tuple[int, int], list[str]]:
        """Get all children for all cells as {(row, col): children}."""
        result = {}
        for row in table.rows:
            for cell in row.cells:
                result[(cell.position.row, cell.position.col)] = list(cell.children)
        return result


# Auto-register on import
LayerRegistry.register(LayerType.TABLE, TableCRUD())
