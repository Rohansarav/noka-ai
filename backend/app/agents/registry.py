"""Only Matchmaker is executable; future identities have explicit boundaries."""
from backend.app.agents.contracts import EmptyArgs, RoleArgs

TOOLS = {
    "get_current_profile": EmptyArgs,
    "get_confirmed_skills": EmptyArgs,
    "get_ranked_matches": EmptyArgs,
    "get_role_requirements": RoleArgs,
    "get_skill_gaps": RoleArgs,
    "get_role_evidence": RoleArgs,
    "get_reviewed_sdg_connections": RoleArgs,
    "get_future_context": RoleArgs,
    "get_forecast_context": RoleArgs,
    "get_scout_findings": RoleArgs,
}
AGENTS = {
    "matchmaker": {"executable": True, "tools": tuple(TOOLS), "purpose": "Explain confirmed skill fit using evidence"},
    "scout": {"executable": False, "tools": (), "purpose": "Future public evidence discovery; no private resume access"},
    "guide": {"executable": False, "tools": (), "purpose": "Future learning guidance; no profile mutation"},
    "impact": {"executable": False, "tools": (), "purpose": "Future reviewed SDG context; no inferred impact metrics"},
}
ANALYTICAL_SERVICES = {"oracle": {"executable_agent": False, "purpose": "Analytical service only"}}


def definitions(role_ids=None):
    tools = []
    for name, schema in TOOLS.items():
        parameters = schema.model_json_schema()
        parameters.setdefault("required", list(parameters["properties"]))
        if schema is RoleArgs and role_ids is not None:
            parameters["properties"]["role_id"]["enum"] = sorted(role_ids)
            parameters["properties"]["role_id"]["description"] = "Bare occupation ID from this enum, without the graph's role: prefix."
        tools.append({"type": "function", "name": name, "description": name.replace("_", " ") + ". Read-only, current session only.",
                      "strict": True, "parameters": parameters})
    return tools
