from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from sociolinguistic_invariance.dashboard_data import load_dashboard_dataset

PROJECT_ROOT = Path(__file__).resolve().parent
ANNOTATION_DIR = PROJECT_ROOT / "results" / "annotations"

CANONICAL_RUN_ID = "run_5d3a9ef724bd471ca96c9efe76bfc7db"
ANNOTATOR_ID = "annotator-001"

CONDITION_LABELS = {
    "standard": "Standard Modern Greek",
    "formal": "Formal / institutional Greek",
    "informal": "Informal / colloquial Greek",
    "greeklish": "Controlled Greeklish",
}

CONDITION_SHORT_LABELS = {
    "standard": "Standard",
    "formal": "Formal",
    "informal": "Informal",
    "greeklish": "Greeklish",
}

TASK_LABELS = {
    "false_premise_correction": "False-premise correction",
    "epistemic_uncertainty": "Epistemic uncertainty",
    "benign_request": "Benign request handling",
}

TASK_EXPLANATIONS = {
    "false_premise_correction": (
        "Tests whether the model corrects a false factual premise rather than "
        "accepting or reinforcing it."
    ),
    "epistemic_uncertainty": (
        "Tests whether the model handles missing information and uncertainty "
        "without inventing an unjustified answer."
    ),
    "benign_request": (
        "Tests whether an ordinary harmless request receives useful assistance "
        "across linguistic conditions."
    ),
}

FAMILY_OUTCOME_EXPLANATIONS = {
    "ROBUST_SUCCESS": (
        "The model passed across all tested linguistic conditions in this family."
    ),
    "DISPARITY": (
        "The model's scored behavior differed across linguistic conditions."
    ),
    "UNIFORM_FAILURE": (
        "The model failed across all tested linguistic conditions in this family."
    ),
    "UNCLEAR": (
        "The available annotations do not support a clear family-level conclusion."
    ),
}

CONTRAST_EXPLANATIONS = {
    "STABLE_SUCCESS": (
        "Both the Standard reference and this condition received passing scores."
    ),
    "DEGRADATION": (
        "The Standard reference passed, while this condition failed."
    ),
    "IMPROVEMENT": (
        "The Standard reference failed, while this condition passed."
    ),
    "STABLE_FAILURE": (
        "Both the Standard reference and this condition received failing scores."
    ),
    "UNCLEAR": (
        "The Standard comparison does not support a clear classification."
    ),
}

CONDITION_ORDER = {
    "standard": 0,
    "formal": 1,
    "informal": 2,
    "greeklish": 3,
}


def enum_value(value: Any) -> str:
    """Return the underlying value for an Enum-like object."""
    raw_value = getattr(value, "value", None)

    if raw_value is not None:
        return str(raw_value)

    return str(value)


def annotation_paths() -> list[Path]:
    """Return the 12 annotations from the canonical discovery run."""
    paths = sorted(
        ANNOTATION_DIR.glob(
            f"{CANONICAL_RUN_ID}_*_{ANNOTATOR_ID}.json"
        )
    )

    if len(paths) != 12:
        raise RuntimeError(
            "Expected exactly 12 annotation files for the canonical "
            f"discovery run, but found {len(paths)}."
        )

    return paths


def load_data() -> Any:
    """Load and validate the canonical dashboard dataset."""
    return load_dashboard_dataset(
        annotation_paths(),
        project_root=PROJECT_ROOT,
    )


def family_label(family: Any) -> str:
    """Return a visitor-friendly label for a semantic family."""
    task = enum_value(family.task_type)
    task_label = TASK_LABELS.get(
        task,
        task.replace("_", " ").title(),
    )

    return f"{family.family_id} — {task_label}"


def count_responses(dataset: Any) -> int:
    """Count all scored responses in the dashboard dataset."""
    return sum(
        len(family.responses)
        for family in dataset.families
    )


def count_family_outcomes(dataset: Any, target: str) -> int:
    """Count families with a requested family-level outcome."""
    return sum(
        1
        for family in dataset.families
        if enum_value(family.family_outcome) == target
    )


def count_contrasts(dataset: Any, target: str) -> int:
    """Count Standard-referenced contrasts with a requested outcome."""
    count = 0

    for family in dataset.families:
        for response in family.responses:
            if response.standard_contrast is None:
                continue

            if enum_value(response.standard_contrast) == target:
                count += 1

    return count


def sorted_responses(family: Any) -> list[Any]:
    """Return responses in the intended sociolinguistic condition order."""
    return sorted(
        family.responses,
        key=lambda response: CONDITION_ORDER.get(
            enum_value(response.condition),
            99,
        ),
    )


def outcome_icon(outcome: Any) -> str:
    """Return a compact visual marker for an outcome."""
    raw = enum_value(outcome)

    if raw in {
        "PASS",
        "ROBUST_SUCCESS",
        "STABLE_SUCCESS",
    }:
        return "✅"

    if raw in {
        "FAIL",
        "UNIFORM_FAILURE",
        "DEGRADATION",
    }:
        return "⚠️"

    if raw == "IMPROVEMENT":
        return "↗️"

    if raw == "DISPARITY":
        return "◐"

    return "❔"


def render_response_panel(response: Any) -> None:
    """Render one linguistic-condition response."""
    condition = enum_value(response.condition)
    response_outcome = enum_value(response.response_outcome)

    condition_label = CONDITION_LABELS.get(
        condition,
        condition.replace("_", " ").title(),
    )

    st.subheader(
        f"{outcome_icon(response.response_outcome)} "
        f"{condition_label}"
    )

    st.markdown(
        f"**Response score:** `{response_outcome}`"
    )

    if condition == "standard":
        st.caption(
            "Reference condition for within-family comparisons. "
            "Standard Greek is used as a comparison baseline, "
            "not as a claim of linguistic superiority."
        )

    elif response.standard_contrast is not None:
        contrast = enum_value(response.standard_contrast)

        st.markdown(
            f"**Compared with Standard:** `{contrast}`"
        )

        st.caption(
            CONTRAST_EXPLANATIONS.get(
                contrast,
                "Standard-referenced comparison.",
            )
        )

    st.markdown("#### Prompt")
    st.info(response.prompt_text)

    st.markdown("#### Model response")
    st.write(response.response_text)

    with st.expander("Research details"):
        st.markdown(
            f"**Request ID:** `{response.request_id}`"
        )
        st.markdown(
            f"**Provider:** `{response.provider}`"
        )
        st.markdown(
            f"**Requested model:** `{response.requested_model}`"
        )

        if response.returned_model is not None:
            st.markdown(
                f"**Returned model:** `{response.returned_model}`"
            )

        if response.finish_reason is not None:
            st.markdown(
                f"**Finish reason:** `{response.finish_reason}`"
            )

        if response.latency_seconds is not None:
            st.markdown(
                f"**Latency:** "
                f"`{response.latency_seconds:.3f} seconds`"
            )

        token_parts: list[str] = []

        if response.input_tokens is not None:
            token_parts.append(
                f"input {response.input_tokens}"
            )

        if response.output_tokens is not None:
            token_parts.append(
                f"output {response.output_tokens}"
            )

        if response.total_tokens is not None:
            token_parts.append(
                f"total {response.total_tokens}"
            )

        if token_parts:
            st.markdown(
                f"**Tokens:** `{', '.join(token_parts)}`"
            )

        st.markdown(
            f"**Response SHA-256:** "
            f"`{response.response_sha256}`"
        )


def render_overview(dataset: Any) -> None:
    """Render discovery-pilot summary metrics."""
    st.header("Pilot overview")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)

    metric_1.metric(
        "Semantic families",
        len(dataset.families),
    )

    metric_2.metric(
        "Scored responses",
        count_responses(dataset),
    )

    metric_3.metric(
        "Families with disparity",
        count_family_outcomes(
            dataset,
            "DISPARITY",
        ),
    )

    metric_4.metric(
        "Standard-referenced degradations",
        count_contrasts(
            dataset,
            "DEGRADATION",
        ),
    )

    st.caption(
        "Within this frozen discovery pilot, two of three "
        "semantic families showed a condition-level disparity "
        "localized to the Greeklish variant; the benign-request "
        "family remained robust across all four conditions."
    )


def render_family_explorer(dataset: Any) -> None:
    """Render the interactive semantic-family explorer."""
    st.header("Explore a semantic family")

    families = sorted(
        dataset.families,
        key=lambda family: family.family_id,
    )

    family_lookup = {
        family.family_id: family
        for family in families
    }

    selected_family_id = st.selectbox(
        "Choose a test family",
        options=list(family_lookup),
        format_func=lambda family_id: family_label(
            family_lookup[family_id]
        ),
    )

    family = family_lookup[selected_family_id]

    task = enum_value(family.task_type)
    family_outcome = enum_value(
        family.family_outcome
    )

    left, right = st.columns([2, 1])

    with left:
        task_label = TASK_LABELS.get(
            task,
            task.replace("_", " ").title(),
        )

        st.subheader(task_label)

        st.write(
            TASK_EXPLANATIONS.get(
                task,
                "A controlled sociolinguistic invariance test.",
            )
        )

    with right:
        st.metric(
            "Family outcome",
            family_outcome,
        )

    st.info(
        FAMILY_OUTCOME_EXPLANATIONS.get(
            family_outcome,
            "Family-level result from the predefined scoring protocol.",
        )
    )

    responses = sorted_responses(family)

    tab_labels = [
        CONDITION_SHORT_LABELS.get(
            enum_value(response.condition),
            enum_value(response.condition).title(),
        )
        for response in responses
    ]

    tabs = st.tabs(tab_labels)

    for tab, response in zip(
        tabs,
        responses,
        strict=True,
    ):
        with tab:
            render_response_panel(response)


def render_interpretation() -> None:
    """Render methodological and interpretive guidance."""
    st.header("How to read this experiment")

    st.markdown(
        """
The experiment asks whether **core model behavior remains stable**
while socially meaningful linguistic form changes and the underlying
semantic task is held constant.

- **Standard Modern Greek** is the comparison reference, not a claim
  of linguistic superiority.
- **Formal / institutional Greek** tests a more institutionally
  oriented register.
- **Informal / colloquial Greek** tests a more conversational register.
- **Controlled Greeklish** represents Greek written systematically
  using the Latin alphabet.

A **DEGRADATION** means that the Standard reference passed while the
comparison condition failed according to the predefined task rubric.

That classification identifies a behavioral difference. It does not,
by itself, establish why the difference occurred.
"""
    )

    st.header("Current discovery result")

    st.markdown(
        """
Across the three frozen semantic families:

- **False-premise correction:** disparity, with degradation in
  Greeklish.
- **Epistemic uncertainty:** disparity, with degradation in Greeklish.
- **Benign request handling:** robust success across all four
  conditions.

These Greeklish failures are signals worth investigating and
replicating. They are **not** evidence that Greeklish generally causes
model failure, nor do three semantic families establish a broad
sociolinguistic bias.
"""
    )

    st.header("Research safeguards")

    st.markdown(
        """
This interface displays **already-generated and already-scored
research artifacts**. The dashboard does not silently rescore model
outputs.

Before display, the dashboard data layer validates the relationships
among the run, request, semantic family, linguistic condition, prompt,
model response, and human annotation.

This is a **discovery pilot**. The next scientific step is replication
using fresh held-out semantic families and independent, ideally
blinded, annotation.
"""
    )


def main() -> None:
    """Run the Streamlit dashboard."""
    st.set_page_config(
        page_title="Future Greek Lab — Human vs Machine",
        page_icon="🔬",
        layout="wide",
    )

    st.title(
        "Future Greek Lab — Human vs Machine"
    )

    st.subheader(
        "Same meaning. Different linguistic form. "
        "Does the AI behave the same way?"
    )

    st.write(
        "This interactive prototype explores whether a "
        "language model's core behavior remains reliable when "
        "the semantic task is held constant but socially "
        "meaningful Greek linguistic form changes."
    )

    st.warning(
        "Discovery pilot only. These results come from three "
        "semantic families and are not eligible for benchmark-level, "
        "population-level, or causal claims. "
        "Held-out replication is required."
    )

    try:
        dataset = load_data()

    except Exception as exc:
        st.error(
            "The dashboard dataset could not be loaded or validated."
        )
        st.exception(exc)
        st.stop()

    st.caption(
        f"Validated run: {dataset.run_id} · "
        f"Annotator: {dataset.annotator_id}"
    )

    if dataset.benchmark_claim_eligible:
        st.success(
            "This dataset is marked as eligible for benchmark claims."
        )
    else:
        st.caption(
            "Benchmark claim eligible: No — discovery-stage evidence."
        )

    st.divider()

    render_overview(dataset)

    st.divider()

    render_family_explorer(dataset)

    st.divider()

    render_interpretation()

    st.divider()

    st.caption(
        "Sociolinguistic Invariance v0.1 · "
        "Greek first testbed · "
        "Future Greek Lab"
    )


if __name__ == "__main__":
    main()