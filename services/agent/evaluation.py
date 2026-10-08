"""Deterministic evaluation scenarios and metrics runner (Phase 7).

Defines the 7 required operational scenarios from AGENTS.md / NEXT_AGENT_BRIEF.md:
1. RTSP outage with successful safe recovery.
2. PoE/power fault requiring technician action.
3. RTSP authentication failure with no autonomous credential change.
4. AI service failure with safe restart and verification.
5. Repeated fault episodes creating separate incidents.
6. No duplicate tickets while one fault episode is active.
7. Automatic recovery that fails verification and escalates safely.

Computes benchmark metrics:
- Diagnosis accuracy
- Safe-action success rate
- Verification success rate
- Unnecessary escalation rate
- Tool-call budget statistics
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from services.agent.orchestrator.models import IncidentContext, IncidentState
from services.agent.policy.audit import AuditLog
from services.agent.policy.engine import PolicyEngine


@dataclass
class ScenarioContract:
    scenario_id: str
    name: str
    description: str
    asset_id: str
    initial_fault: Optional[str]
    allowed_auto_action: Optional[str]
    expected_diagnosis_keywords: List[str]
    expected_final_state: IncidentState
    expected_verification_passed: Optional[bool]
    expected_technician_action: bool
    max_tool_calls: int = 15


@dataclass
class ScenarioResult:
    scenario_id: str
    name: str
    passed: bool
    actual_state: IncidentState
    actual_diagnosis: str
    diagnosis_matched: bool
    actual_actions: List[str]
    safe_action_matched: bool
    verification_matched: bool
    escalation_matched: bool
    tool_calls: int
    details: str = ''


@dataclass
class EvaluationMetrics:
    total_scenarios: int
    passed_scenarios: int
    diagnosis_accuracy: float
    safe_action_success: float
    verification_success: float
    unnecessary_escalation: float
    avg_tool_calls: float
    max_tool_calls: int
    results: List[ScenarioResult] = field(default_factory=list)

    def format_table(self) -> str:
        lines = [
            '=' * 96,
            f'EVALUATION MATRIX RESULTS: {self.passed_scenarios}/{self.total_scenarios} PASSED',
            '=' * 96,
            f'{"ID":<4} | {"Scenario Name":<34} | {"State":<18} | {"Action":<15} | {"Verif":<6} | {"Status":<6}',
            '-' * 96,
        ]
        for idx, res in enumerate(self.results, 1):
            status = 'PASS' if res.passed else 'FAIL'
            action = res.actual_actions[0] if res.actual_actions else 'none'
            verif = 'ok' if res.verification_matched else 'mismatch'
            lines.append(
                f'{idx:<4} | {res.name[:34]:<34} | {res.actual_state.value:<18} | {action:<15} | {verif:<6} | {status:<6}'
            )
        lines.extend([
            '-' * 96,
            'METRICS SUMMARY:',
            f'  Diagnosis accuracy:        {self.diagnosis_accuracy * 100:.1f}%',
            f'  Safe action success:       {self.safe_action_success * 100:.1f}%',
            f'  Verification success:      {self.verification_success * 100:.1f}%',
            f'  Unnecessary escalation:    {self.unnecessary_escalation * 100:.1f}%',
            f'  Average tool calls:        {self.avg_tool_calls:.1f} (max: {self.max_tool_calls})',
            '=' * 96,
        ])
        return '\n'.join(lines)


# 1. RTSP outage with successful safe recovery
SCENARIO_1 = ScenarioContract(
    scenario_id='sc1_rtsp_recovery',
    name='RTSP Outage Recovery',
    description='Transient RTSP outage recovered automatically and verified healthy.',
    asset_id='CAM-027',
    initial_fault='rtsp_down',
    allowed_auto_action='reconnect-rtsp',
    expected_diagnosis_keywords=['rtsp', 'stream'],
    expected_final_state=IncidentState.RESOLVED,
    expected_verification_passed=True,
    expected_technician_action=False,
)

# 2. PoE/power fault requiring technician action
SCENARIO_2 = ScenarioContract(
    scenario_id='sc2_poe_handoff',
    name='PoE Power Off Handoff',
    description='Physical PoE loss requires on-site technician inspection without autonomous tool action.',
    asset_id='CAM-019',
    initial_fault='poe_off',
    allowed_auto_action=None,
    expected_diagnosis_keywords=['poe', 'power', 'physical'],
    expected_final_state=IncidentState.PENDING_TECHNICIAN,
    expected_verification_passed=None,
    expected_technician_action=True,
)

# 3. RTSP authentication failure with no autonomous credential change
SCENARIO_3 = ScenarioContract(
    scenario_id='sc3_auth_failure',
    name='RTSP Auth Failure Denial',
    description='Credential mismatch stops safely; policy layer blocks autonomous credential modification.',
    asset_id='CAM-027',
    initial_fault='rtsp_auth_failure',
    allowed_auto_action=None,
    expected_diagnosis_keywords=['auth', 'credential'],
    expected_final_state=IncidentState.PENDING_TECHNICIAN,
    expected_verification_passed=None,
    expected_technician_action=True,
)

# 4. AI service failure with safe restart and verification
SCENARIO_4 = ScenarioContract(
    scenario_id='sc4_ai_service_recovery',
    name='AI Service Safe Restart',
    description='Emulated AI service failure recovered via safe restart and verified healthy.',
    asset_id='AI-BOX-07',
    initial_fault='ai_service_down',
    allowed_auto_action='restart-ai-service',
    expected_diagnosis_keywords=['ai', 'service'],
    expected_final_state=IncidentState.RESOLVED,
    expected_verification_passed=True,
    expected_technician_action=False,
)

# 5. Repeated fault episodes creating separate incidents
SCENARIO_5 = ScenarioContract(
    scenario_id='sc5_repeated_episodes',
    name='Repeated Episode Separation',
    description='Distinct fault occurrences across recovery boundaries generate separate tracked incidents.',
    asset_id='CAM-018',
    initial_fault='rtsp_down',
    allowed_auto_action='reconnect-rtsp',
    expected_diagnosis_keywords=['rtsp', 'stream'],
    expected_final_state=IncidentState.RESOLVED,
    expected_verification_passed=True,
    expected_technician_action=False,
)

# 6. No duplicate tickets while one fault episode is active
SCENARIO_6 = ScenarioContract(
    scenario_id='sc6_active_dedup',
    name='Active Episode Dedup',
    description='Repeated monitor checks during an active incident suppress duplicate ticket creation.',
    asset_id='CAM-027',
    initial_fault='rtsp_down',
    allowed_auto_action=None,
    expected_diagnosis_keywords=[],
    expected_final_state=IncidentState.INVESTIGATING,
    expected_verification_passed=None,
    expected_technician_action=False,
)

# 7. Automatic recovery that fails verification and escalates safely
SCENARIO_7 = ScenarioContract(
    scenario_id='sc7_failed_verification',
    name='Failed Verification Escalation',
    description='Safe recovery attempted, but unresolved post-action health escalates to technician.',
    asset_id='CAM-027',
    initial_fault='rtsp_down',
    allowed_auto_action='reconnect-rtsp',
    expected_diagnosis_keywords=['rtsp', 'stream'],
    expected_final_state=IncidentState.PENDING_TECHNICIAN,
    expected_verification_passed=False,
    expected_technician_action=True,
)

EVALUATION_SCENARIOS = [
    SCENARIO_1,
    SCENARIO_2,
    SCENARIO_3,
    SCENARIO_4,
    SCENARIO_5,
    SCENARIO_6,
    SCENARIO_7,
]


def evaluate_run(
    contract: ScenarioContract,
    ctx: IncidentContext,
    tool_calls: int = 0,
) -> ScenarioResult:
    """Evaluate an execution against a declarative scenario contract."""
    diagnosis = (ctx.diagnosis or '').lower()
    diagnosis_matched = (
        not contract.expected_diagnosis_keywords
        or any(k in diagnosis for k in contract.expected_diagnosis_keywords)
    )

    state_matched = ctx.state == contract.expected_final_state

    if contract.allowed_auto_action:
        action_matched = (
            contract.allowed_auto_action in ctx.executed_actions
            and len(ctx.executed_actions) == 1
        )
    else:
        action_matched = len(ctx.executed_actions) == 0

    if contract.expected_verification_passed is not None:
        verif_matched = (
            ctx.verification is not None
            and ctx.verification.performed
            and ctx.verification.passed == contract.expected_verification_passed
        )
    else:
        verif_matched = True

    escalation_matched = bool(ctx.handoff is not None) == contract.expected_technician_action

    passed = (
        state_matched
        and diagnosis_matched
        and action_matched
        and verif_matched
        and escalation_matched
        and tool_calls <= contract.max_tool_calls
    )

    details = (
        f'state={ctx.state.value} (exp={contract.expected_final_state.value}); '
        f'actions={ctx.executed_actions}; '
        f'verif={"passed" if ctx.verification and ctx.verification.passed else "failed/none"}; '
        f'handoff={bool(ctx.handoff)}'
    )

    return ScenarioResult(
        scenario_id=contract.scenario_id,
        name=contract.name,
        passed=passed,
        actual_state=ctx.state,
        actual_diagnosis=ctx.diagnosis or '',
        diagnosis_matched=diagnosis_matched,
        actual_actions=ctx.executed_actions,
        safe_action_matched=action_matched,
        verification_matched=verif_matched,
        escalation_matched=escalation_matched,
        tool_calls=tool_calls,
        details=details,
    )


def compute_metrics(results: List[ScenarioResult]) -> EvaluationMetrics:
    total = len(results)
    if total == 0:
        return EvaluationMetrics(
            total_scenarios=0, passed_scenarios=0, diagnosis_accuracy=0.0,
            safe_action_success=0.0, verification_success=0.0,
            unnecessary_escalation=0.0, avg_tool_calls=0.0, max_tool_calls=0,
            results=[],
        )

    passed_count = sum(1 for r in results if r.passed)
    diag_acc = sum(1 for r in results if r.diagnosis_matched) / total
    safe_succ = sum(1 for r in results if r.safe_action_matched) / total
    verif_succ = sum(1 for r in results if r.verification_matched) / total

    # Unnecessary escalation: expected resolved (no handoff) but actually handed off
    unnecessary_escalations = sum(
        1 for r in results
        if r.actual_state == IncidentState.PENDING_TECHNICIAN
        and any(
            c.scenario_id == r.scenario_id and not c.expected_technician_action
            for c in EVALUATION_SCENARIOS
        )
    )
    unnecessary_rate = unnecessary_escalations / total

    tool_counts = [r.tool_calls for r in results]
    avg_tools = sum(tool_counts) / total
    max_tools = max(tool_counts) if tool_counts else 0

    return EvaluationMetrics(
        total_scenarios=total,
        passed_scenarios=passed_count,
        diagnosis_accuracy=diag_acc,
        safe_action_success=safe_succ,
        verification_success=verif_succ,
        unnecessary_escalation=unnecessary_rate,
        avg_tool_calls=avg_tools,
        max_tool_calls=max_tools,
        results=results,
    )
