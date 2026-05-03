"""Stage 2 Aggregation Protocols — structural subtyping interfaces.

Defines typing.Protocol classes for each Stage 2 aggregation step.
All inherit from IAggregator base protocol for uniform interface.

Usage:
    from prism.stage2.aggregation.aggregation_protocols import ITokenRangeAggregator
    from prism.stage2.aggregation.rules.token_range_aggregator import TokenRangeAggregator

    assert isinstance(TokenRangeAggregator(), ITokenRangeAggregator)  # True
"""

from typing import Protocol, runtime_checkable, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@runtime_checkable
class IAggregator(Protocol[InputT, OutputT]):
    """Base protocol for all Stage 2 aggregation operations.

    Generic over input and output types — all aggregation steps
    implement this protocol for uniform dispatch.
    """

    def aggregate(self, input_data: InputT) -> OutputT: ...

    def validate_input(self, input_data: InputT) -> tuple[bool, str]: ...

    def validate_output(self, output_data: OutputT) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...
