"""Check schema/examples only. Does not implement the SEBI acceptance catalogue."""
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures" / "design"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def get(value, pointer):
    for key in pointer.strip("/").split("/"):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def mutate(value, case):
    result = copy.deepcopy(value)
    if case["operation"] == "append_copy":
        get(result, case["path"]).append(copy.deepcopy(get(result, case["value"])))
        return result
    prefix, _, last = case["path"].rpartition("/")
    parent = get(result, prefix) if prefix else result
    key = int(last) if isinstance(parent, list) else last
    if case["operation"] == "remove":
        del parent[key]
    else:
        parent[key] = case["value"]
    return result


def main():
    validators = {}
    for name in ("registry", "run", "report"):
        schema = read(ROOT / "schemas" / f"{name}.schema.json")
        Draft202012Validator.check_schema(schema)
        validators[name] = Draft202012Validator(schema, format_checker=FormatChecker())
    examples = {"registry": read(FIX / "registry.json"), "run": read(FIX / "run.json"),
                "report": read(FIX / "example_report.json")}
    for name, data in examples.items():
        validators[name].validate(data)
    cases = read(FIX / "mutation_cases.json")
    for case in cases:
        changed = mutate(examples[case["target"]], case)
        accepted = validators[case["target"]].is_valid(changed)
        assert accepted == case["schema_should_accept"], case["id"]
    source = examples["registry"]["sources"][0]
    assert hashlib.sha256((FIX / source["local_path"]).read_bytes()).hexdigest() == source["sha256"]
    claims = {x["id"]: x for x in examples["registry"]["claims"]}
    evidence = {x["id"]: x for x in examples["registry"]["evidence"]}
    for review in examples["registry"]["reviews"]:
        if review["subject_type"] != "evidence":
            continue
        claim = claims[evidence[review["subject_id"]]["claim_id"]]
        canonical = json.dumps({"claim_id": claim["id"], "value": claim["value"]}, sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        assert hashlib.sha256(canonical).hexdigest() == review["value_digest"]
    acceptance = {x["id"] for x in read(ROOT / "docs/requirements/ACCEPTANCE_SCENARIOS.json")["scenarios"]}
    assert all(c["scenario"] in acceptance for c in cases)
    print(json.dumps({"schemas_checked": 3, "examples_validated": 3, "shape_mutations_checked": len(cases),
                      "shape_rejections_expected": sum(not x["schema_should_accept"] for x in cases),
                      "fixture_source_and_review_digests": "match", "application_acceptance_cases_executed": 0,
                      "supplied_workbook_scenarios_executed": 0}, indent=2))


if __name__ == "__main__":
    main()
