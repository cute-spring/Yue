from typing import List, Optional


class SkillPolicyGate:
    """
    Authorization checks for selection and runtime binding.
    """

    @staticmethod
    def check_tool_intersection(agent_tools: List[str], skill_allowed_tools: Optional[List[str]]) -> List[str]:
        if skill_allowed_tools is None:
            return agent_tools

        agent_set = set(agent_tools)
        skill_set = set(skill_allowed_tools)
        return list(agent_set.intersection(skill_set))
