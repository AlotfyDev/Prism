"""Graph configuration for Stage 2 subgraph.

Extends Stage2PipelineConfig with graph-specific options:
- SQLite checkpointing
- Retry limits
- Fallback routing
- Per-step timeouts
"""

from pydantic import BaseModel, Field

from prism.stage2.pipeline_config import Stage2PipelineConfig


class GraphConfig(Stage2PipelineConfig):
    """Extends Stage2PipelineConfig with graph-specific options."""

    checkpoint_db_path: str = Field(
        default="data/prism_checkpoints.db",
        description="SQLite database path for LangGraph checkpointing",
    )

    max_retries_per_step: int = Field(
        default=0,
        ge=0,
        description="Maximum retries per step on validation failure (0 = no retry)",
    )

    enable_fallback: bool = Field(
        default=False,
        description="Whether to enable fallback routing on step failure",
    )

    step_timeout_seconds: dict[str, int] = Field(
        default_factory=dict,
        description="Per-step timeout limits (e.g., {'parse': 30, 'classify': 60})",
    )
