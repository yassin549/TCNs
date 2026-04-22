from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from frontier_execution import ContractSpec, validate_contract_spec


@dataclass(frozen=True)
class InstrumentConfigValidation:
    instrument_id: str
    valid: bool
    errors: List[str]


def validate_contract_specs(contracts: List[ContractSpec]) -> List[InstrumentConfigValidation]:
    results: List[InstrumentConfigValidation] = []
    for contract in contracts:
        errors: List[str] = []
        try:
            validate_contract_spec(contract)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
        results.append(
            InstrumentConfigValidation(
                instrument_id=contract.instrument_id,
                valid=len(errors) == 0,
                errors=errors,
            )
        )
    return results


def raise_for_invalid_contracts(contracts: List[ContractSpec]) -> None:
    results = validate_contract_specs(contracts)
    invalid = [result for result in results if not result.valid]
    if not invalid:
        return
    rendered = []
    for item in invalid:
        rendered.append(f"{item.instrument_id}: {'; '.join(item.errors)}")
    raise ValueError("Invalid contract configuration: " + " | ".join(rendered))


def validation_results_to_dict(results: List[InstrumentConfigValidation]) -> List[Dict[str, object]]:
    return [
        {
            "instrument_id": item.instrument_id,
            "valid": item.valid,
            "errors": list(item.errors),
        }
        for item in results
    ]
