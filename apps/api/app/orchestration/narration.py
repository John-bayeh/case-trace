"""Presentation of committed actions; no inference or synthetic activity."""

from typing import Any

AGENTS = {
    "retrieval": "Retrieval agent is discovering the patient's clinical history.",
    "timeline": "Timeline agent is comparing chronology across encounters.",
    "laboratory": "Laboratory agent is reviewing measurements and documented follow-up.",
    "medication": "Medication agent is checking recorded treatment changes and linked notes.",
    "contradiction": "Contradiction investigator is retrieving and comparing source evidence.",
    "synthesis": "Synthesis agent is assembling the evidence-backed report.",
}


def project(event: str, payload: dict[str, Any]) -> tuple[str, str]:
    status = event.rsplit(".", 1)[-1]
    if event == "agent.started":
        return AGENTS.get(
            payload.get("agent", ""), "A specialist started reviewing evidence."
        ), status
    messages = {
        "investigation.started": "The investigation has started.",
        "investigation.completed": "Investigation completed. Review findings and limitations.",
        "investigation.failed": "Investigation stopped with an error; results may be incomplete.",
        "verification.started": "Checking the proposed finding against original source records.",
        "verification.completed": "Evidence verification finished: "
        + str(payload.get("status", "")),
        "finding.proposed": "A source-backed candidate finding was proposed for verification.",
        "finding.verified": "The finding passed independent evidence verification.",
        "finding.rejected": "The proposed finding did not pass evidence verification.",
        "finding.unresolved": "The finding remains unresolved with the available evidence.",
        "tool.started": "Retrieving clinical evidence with "
        + str(payload.get("tool", "clinical tools")).replace("_", " ")
        + ".",
        "tool.completed": f"Retrieved {payload.get('record_count', 0)} source references.",
        "tool.failed": "A clinical retrieval failed; related evidence may be incomplete.",
        "agent.completed": "The specialist completed its evidence review.",
        "agent.failed": "The specialist could not complete its review; see limitations.",
        "task.started": "A planned specialist investigation task started.",
        "specialist.evidence_requested": "Medication and laboratory evidence is being compared.",
    }
    return messages.get(event, event.replace(".", " ").replace("_", " ").capitalize() + "."), status
