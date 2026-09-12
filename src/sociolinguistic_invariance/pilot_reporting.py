from __future__ import annotations

from collections import Counter
from typing import Final

from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.pilot_analysis import (
    EXPECTED_CONDITIONS,
    PilotAnalysis,
)
from sociolinguistic_invariance.scoring import (
    FamilyOutcome,
    ResponseOutcome,
    StandardContrastOutcome,
)

PILOT_REPORT_FORMAT_VERSION: Final = (
    "pilot-report-v0.1"
)

_TASK_LABELS: Final[
    dict[TaskType, str]
] = {
    TaskType.FALSE_PREMISE_CORRECTION: (
        "False-premise correction"
    ),
    TaskType.EPISTEMIC_UNCERTAINTY: (
        "Epistemic uncertainty"
    ),
    TaskType.BENIGN_REQUEST: (
        "Benign request"
    ),
}

_CONDITION_LABELS: Final[
    dict[VariationCondition, str]
] = {
    VariationCondition.STANDARD: "Standard",
    VariationCondition.FORMAL: "Formal",
    VariationCondition.INFORMAL: "Informal",
    VariationCondition.GREEKLISH: "Greeklish",
}


def _task_label(
    task_type: TaskType,
) -> str:
    """Return a readable task label."""

    return _TASK_LABELS.get(
        task_type,
        task_type.value.replace(
            "_",
            " ",
        ).title(),
    )


def _condition_label(
    condition: VariationCondition,
) -> str:
    """Return a readable condition label."""

    return _CONDITION_LABELS.get(
        condition,
        condition.value.title(),
    )


def _bool_text(
    value: bool,
) -> str:
    """Render a Boolean consistently."""

    return (
        "true"
        if value
        else "false"
    )


def render_pilot_report(
    analysis: PilotAnalysis,
) -> str:
    """Render one pilot analysis as Markdown."""

    response_counts: Counter[
        ResponseOutcome
    ] = Counter(
        record.outcome
        for record in analysis.annotations
    )

    family_counts: Counter[
        FamilyOutcome
    ] = Counter(
        family.family_outcome
        for family in analysis.families
    )

    contrast_counts: Counter[
        StandardContrastOutcome
    ] = Counter(
        contrast
        for family in analysis.families
        for contrast
        in family.standard_contrasts.values()
    )

    greeklish_degradations = sum(
        1
        for family in analysis.families
        if family.standard_contrasts.get(
            VariationCondition.GREEKLISH
        )
        is StandardContrastOutcome.DEGRADATION
    )

    lines: list[str] = [
        (
            "# Sociolinguistic Invariance — "
            "Discovery Pilot Report"
        ),
        "",
        (
            f"Report format: "
            f"`{PILOT_REPORT_FORMAT_VERSION}`"
        ),
        "",
        (
            "> **Scope:** This is a discovery-pilot "
            "analysis. "
            f"`benchmark_claim_eligible="
            f"{_bool_text(analysis.benchmark_claim_eligible)}`. "
            "The results are descriptive and must not "
            "be presented as confirmatory benchmark claims."
        ),
        "",
        "## Run metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Run ID | `{analysis.run_id}` |",
        f"| Annotator | `{analysis.annotator_id}` |",
        (
            "| Annotation protocol | "
            f"`{analysis.annotation_protocol_version}` |"
        ),
        (
            "| Scoring protocol | "
            f"`{analysis.scoring_protocol_version}` |"
        ),
        (
            "| Benchmark claim eligible | "
            f"`{_bool_text(analysis.benchmark_claim_eligible)}` |"
        ),
        (
            "| Annotated responses | "
            f"{len(analysis.annotations)} |"
        ),
        (
            "| Semantic families | "
            f"{len(analysis.families)} |"
        ),
        "",
        "## Aggregate response outcomes",
        "",
        "| Response outcome | Count |",
        "| --- | ---: |",
    ]

    for response_outcome in ResponseOutcome:
        lines.append(
            f"| {response_outcome.value} | "
            f"{response_counts[response_outcome]} |"
        )

    lines.extend(
        [
            "",
            "## Aggregate family outcomes",
            "",
            "| Family outcome | Count |",
            "| --- | ---: |",
        ]
    )

    for family_outcome in FamilyOutcome:
        lines.append(
            f"| {family_outcome.value} | "
            f"{family_counts[family_outcome]} |"
        )

    lines.extend(
        [
            "",
            "## Standard-referenced contrasts",
            "",
            "| Contrast outcome | Count |",
            "| --- | ---: |",
        ]
    )

    for contrast_outcome in StandardContrastOutcome:
        lines.append(
            f"| {contrast_outcome.value} | "
            f"{contrast_counts[contrast_outcome]} |"
        )

    lines.extend(
        [
            "",
            "## Family summary",
            "",
            "| Family | Task | Family outcome |",
            "| --- | --- | --- |",
        ]
    )

    for family in analysis.families:
        lines.append(
            f"| `{family.family_id}` | "
            f"{_task_label(family.task_type)} | "
            f"**{family.family_outcome.value}** |"
        )

    lines.extend(
        [
            "",
            "## Family-level results",
            "",
        ]
    )

    for family in analysis.families:
        lines.extend(
            [
                (
                    f"### {family.family_id} — "
                    f"{_task_label(family.task_type)}"
                ),
                "",
                (
                    f"Family outcome: "
                    f"**{family.family_outcome.value}**"
                ),
                "",
                (
                    f"Rubric: "
                    f"`{family.rubric_version}`"
                ),
                "",
                (
                    "| Condition | Response outcome | "
                    "Standard-referenced contrast |"
                ),
                "| --- | --- | --- |",
            ]
        )

        for condition in EXPECTED_CONDITIONS:
            response_outcome = (
                family.response_outcomes[
                    condition
                ]
            )

            if (
                condition
                is VariationCondition.STANDARD
            ):
                contrast_text = "REFERENCE"
            else:
                contrast_text = (
                    family.standard_contrasts[
                        condition
                    ].value
                )

            lines.append(
                f"| {_condition_label(condition)} | "
                f"**{response_outcome.value}** | "
                f"{contrast_text} |"
            )

        lines.append(
            ""
        )

    disparity_count = family_counts[
        FamilyOutcome.DISPARITY
    ]

    robust_success_count = family_counts[
        FamilyOutcome.ROBUST_SUCCESS
    ]

    degradation_count = contrast_counts[
        StandardContrastOutcome.DEGRADATION
    ]

    robust_success_verb = (
        "was"
        if robust_success_count == 1
        else "were"
    )

    degradation_label = (
        "contrast"
        if degradation_count == 1
        else "contrasts"
    )

    lines.extend(
        [
            "## Descriptive interpretation",
            "",
            (
                f"The run contains "
                f"{len(analysis.families)} semantic families "
                f"and {len(analysis.annotations)} annotated "
                "responses."
            ),
            "",
            (
                f"{disparity_count} families were classified "
                f"as **DISPARITY**, while "
                f"{robust_success_count} "
                f"{robust_success_verb} classified as "
                "**ROBUST_SUCCESS**."
            ),
            "",
            (
                f"The Standard-referenced analysis contains "
                f"{degradation_count} **DEGRADATION** "
                f"{degradation_label}. "
                f"{greeklish_degradations} of these involved "
                "the Greeklish condition."
            ),
            "",
            (
                "These patterns identify candidate effects "
                "for replication. They do not establish that "
                "Greeklish, register, or any other linguistic "
                "condition generally causes degraded model "
                "behavior."
            ),
            "",
            "## Interpretation limits",
            "",
            (
                "- This is a discovery run, not a held-out "
                "confirmatory replication."
            ),
            (
                "- The current analysis contains only "
                f"{len(analysis.families)} semantic families."
            ),
            (
                "- The annotations represented here come "
                f"from one annotator: "
                f"`{analysis.annotator_id}`."
            ),
            (
                "- No inferential significance tests are "
                "reported for this pilot."
            ),
            (
                "- Family outcomes summarize within-family "
                "condition patterns; they are not population-"
                "level effect estimates."
            ),
            (
                "- Any candidate disparity should be tested "
                "on fresh held-out semantic families before "
                "being treated as a replicated finding."
            ),
            "",
        ]
    )

    return "\n".join(
        lines
    )