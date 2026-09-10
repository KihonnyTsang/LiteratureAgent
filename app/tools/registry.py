from app.tools.metadata_tool import (
    query_metadata,
)

from app.tools.table_tool import (
    sort_table,
    aggregate_table,
    limit_table,
)

from app.tools.plot_tool import (
    plot_table,
)

from app.tools.fact_tool import (
    query_facts,
)

from app.tools.rag_tool import (
    rag_search,
)

TOOL_REGISTRY = {

    "query_metadata":
        query_metadata,

    "sort_table":
        sort_table,

    "aggregate_table":
        aggregate_table,

    "limit_table":
        limit_table,

    "plot_table":
        plot_table,

    "rag_search":
        rag_search,

    "query_facts":
        query_facts,
}

def get_tool(
    tool_name: str,
):
    tool = TOOL_REGISTRY.get(
        tool_name
    )

    if tool is None:
        raise ValueError(
            f"工具尚未注册："
            f"{tool_name}"
        )

    return tool