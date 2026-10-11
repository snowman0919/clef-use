import pytest

from clef_use.capabilities import capabilities, digest
from clef_use.installer import verify_contract


def test_mixed_runtime_guide_schema_bundle_cannot_pass_installer_validation():
    actual = capabilities()
    expected = {
        key: actual[key]
        for key in (
            "api_schema_version",
            "schema_sha256",
            "guide_contract_version",
            "operation_registry_version",
        )
    }
    expected["guide_bundle_sha256"] = digest(actual["guides"]["skills"])
    verify_contract(expected, actual)
    with pytest.raises(ValueError, match="schema_sha256"):
        verify_contract(expected, {**actual, "schema_sha256": "0" * 64})
    guides = {**actual["guides"], "skills": {}}
    with pytest.raises(ValueError, match="guide bundle"):
        verify_contract(expected, {**actual, "guides": guides})
