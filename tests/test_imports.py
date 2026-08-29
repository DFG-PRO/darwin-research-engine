def test_package_imports() -> None:
    import darwin
    import darwin.construction
    import darwin.synthesis

    assert darwin.__version__
    assert darwin.construction.ClaimConstructionService
    assert darwin.synthesis.StructuredSynthesisService
