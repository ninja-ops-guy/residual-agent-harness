"""ALM/package drift tests for Copilot Studio deployment metadata."""
from __future__ import annotations

import json
import yaml
from pathlib import Path

from residual.integrations.copilot_studio.departments import department_catalog,DepartmentGroups


ROOT=Path(__file__).resolve().parents[2]
DEPLOY=ROOT/"deploy"/"copilot-studio"


def _groups(prefix):
    return DepartmentGroups(
        frozenset({prefix+"-members"}),frozenset({prefix+"-reviewers"}),
        frozenset({prefix+"-leads"}),frozenset({"audit"}),
    )


def test_solution_manifest_declares_all_five_agents_and_no_secrets():
    manifest=json.loads((DEPLOY/"solution-manifest.json").read_text())
    assert set(manifest["components"]["agents"])=={
        "Firmware Engineering","Mechanical Engineering","Electromechanical Engineering",
        "Automated Testing","Quality Assurance",
    }
    text=(DEPLOY/"environment.example.json").read_text().lower()
    assert "secret" not in text and "password" not in text and "client_secret" not in text


def test_agent_manifests_match_residual_template_catalog():
    catalog=department_catalog({
        "firmware":_groups("fw"),"mechanical":_groups("mech"),
        "electromechanical":_groups("emech"),"automated_testing":_groups("test"),
        "quality_assurance":_groups("qa"),
    })
    files={
        "firmware":"firmware.json","mechanical":"mechanical.json",
        "electromechanical":"electromechanical.json",
        "automated_testing":"automated-testing.json",
        "quality_assurance":"quality-assurance.json",
    }
    for name,filename in files.items():
        manifest=json.loads((DEPLOY/"agents"/filename).read_text())
        _,templates=catalog[name]
        assert set(manifest["residual_actions"])==set(templates)
        assert manifest["profile"]==name


def test_agent_library_template_defaults_inactive():
    metadata=json.loads((DEPLOY/"agent-library-template.json").read_text())
    assert metadata["publish_status"]=="Inactive"
    assert metadata["solution_unique_name"]=="ResidualEngineeringAgents"


def test_openapi_is_valid_yaml_and_lists_every_department_template():
    spec=yaml.safe_load((ROOT/"residual"/"integrations"/"copilot_studio"/"openapi.yaml").read_text())
    assert spec["openapi"]=="3.0.3"
    enum=set(spec["components"]["schemas"]["MissionRequest"]["properties"]["template_id"]["enum"])
    catalog=department_catalog({
        "firmware":_groups("fw"),"mechanical":_groups("mech"),
        "electromechanical":_groups("emech"),"automated_testing":_groups("test"),
        "quality_assurance":_groups("qa"),
    })
    expected={tid for _,templates in catalog.values() for tid in templates}
    assert enum==expected
    inputs=spec["components"]["schemas"]["MissionRequest"]["properties"]["inputs"]
    assert inputs["additionalProperties"] is False
    assert "required" not in inputs
