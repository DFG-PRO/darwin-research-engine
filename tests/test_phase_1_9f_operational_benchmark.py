from __future__ import annotations

import importlib.util
from pathlib import Path


def test_phase_1_9f_operational_benchmark(tmp_path) -> None:
    runner_path = Path("benchmarks/phase-1.9f/run_operational_benchmark.py")
    spec = importlib.util.spec_from_file_location("phase_1_9f_benchmark", runner_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    summary = module.run_operational_benchmark(tmp_path / "artifacts")

    assert summary["benchmark_mode"] == "SUPPLIED_MATERIAL_OPERATIONAL_BENCHMARK"
    assert summary["result"]["state"] == "COMPLETED"
    assert summary["result"]["stop_reason"] == "SUCCESS_COMPLETE"
    assert summary["result"]["completion_assessment"] == "COMPLETE"
    assert summary["result"]["report_published"] is True
    assert summary["result"]["report_artifact_verified"] is True
    assert summary["metrics"]["required_plan_items"] == 10
    assert summary["metrics"]["satisfied_plan_items"] == 10
    assert summary["metrics"]["valid_grounded_evidence_candidates"] == 10
    assert summary["metrics"]["accepted_evidence"] == 10
    assert summary["metrics"]["accepted_claims"] == 10
    assert summary["metrics"]["claim_evidence_links"] == 10
    assert summary["validation_distribution"] == {"SUPPORTED": 10}
    assert summary["provenance_audit"]["exact_grounding_verified"] is True
    assert summary["provenance_audit"]["evidence_snapshot_segment_provenance_complete"] is True
    assert summary["provenance_audit"]["claim_evidence_links_complete"] is True
    assert summary["source_independence_audit"]["false_corroboration_detected"] is False
    assert summary["counters"]["provider_calls"] <= summary["budgets"]["max_provider_calls"]
