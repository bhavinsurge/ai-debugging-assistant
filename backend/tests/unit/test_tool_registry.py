from app.tools import TOOL_REGISTRY


def test_tool_registry_contains_required_tools():
    required = {
        "search_logs",
        "get_metrics",
        "get_recent_deployments",
        "get_service_dependencies",
        "search_previous_incidents",
        "search_runbooks",
    }
    assert required.issubset(set(TOOL_REGISTRY.keys()))
