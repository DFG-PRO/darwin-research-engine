import importlib.util
from pathlib import Path


def load_benchmark_module():
    path = Path("benchmarks/phase-1.8i/run_benchmark.py")
    spec = importlib.util.spec_from_file_location("phase_1_8i_benchmark", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_phase_1_8i_benchmark_exercises_research_mvp_pipeline(tmp_path) -> None:
    module = load_benchmark_module()

    result = module.run_benchmark(tmp_path)

    assert result["execution_mode"] == "SUPPLIED_MATERIAL_BENCHMARK"
    assert result["plan"]["required_total"] == 10
    assert result["plan"]["required_satisfied"] == 10
    assert result["sources"]["total"] == 8
    assert result["sources"]["derived_republication_sources"] == 1
    assert result["evidence"]["total"] == 8
    assert result["evidence"]["snapshot_derived"] == 8
    assert result["claims"]["total"] == 11
    assert result["claims"]["false_corroboration_guard"]["state"] == "SUPPORTED"
    assert result["claims"]["false_corroboration_guard"]["independent_source_count"] == 1
    assert result["claims"]["distribution"]["CONTESTED"] == 1
    assert result["synthesis"]["evidence_gaps"] == []
    assert result["synthesis"]["unresolved_contradictions"]
    assert result["process"]["repeated_identical_snapshots"] == 1
    assert result["completion_assessment"] == "UNRESOLVED_CONTRADICTION"
    assert result["acceptance_result"] == "PHASE_1_8_READY_TO_CLOSE"


def test_phase_1_8i_completion_gate_audit_expectations(tmp_path) -> None:
    module = load_benchmark_module()

    result = module.run_benchmark(tmp_path)
    gates = result["completion_gate_audit"]

    assert gates["missing_required_evidence"] == "NEEDS_EVIDENCE"
    assert gates["contested_critical_claim"] == "UNRESOLVED_CONTRADICTION"
    assert gates["human_review_pending"] == "HUMAN_REVIEW_REQUIRED"
