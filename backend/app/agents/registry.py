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
}
AGENTS = {
    "matchmaker": {"executable": True, "tools": tuple(TOOLS), "purpose": "Explain confirmed skill fit using evidence"},
    "scout": {"executable": False, "tools": (), "purpose": "Future public evidence discovery; no private resume access"},
    "guide": {"executable": False, "tools": (), "purpose": "Future learning guidance; no profile mutation"},
    "impact": {"executable": False, "tools": (), "purpose": "Future reviewed SDG context; no inferred impact metrics"},
}
ANALYTICAL_SERVICES = {"oracle": {"executable_agent": False, "purpose": "Analytical service only"}}


def definitions():
    tools = []
    for name, schema in TOOLS.items():
        parameters = schema.model_json_schema()
        parameters.setdefault("required", list(parameters["properties"]))
        tools.append({"type": "function", "name": name, "description": name.replace("_", " ") + ". Read-only, current session only.",
                      "strict": True, "parameters": parameters})
    return tools
