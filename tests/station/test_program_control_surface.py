from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_station_program_control_surface_is_wired():
    server = (ROOT / "residual/station/server.py").read_text(encoding="utf-8")
    service = (ROOT / "residual/station/service.py").read_text(encoding="utf-8")
    shell = (ROOT / "residual/station/static/index.html").read_text(encoding="utf-8")
    app = (ROOT / "residual/station/static/app.js").read_text(encoding="utf-8")
    program = (ROOT / "residual/station/static/program.js").read_text(encoding="utf-8")

    assert 'ProgramControl(self.store.root / "program-control")' in service
    assert '"/api/program"' in server
    assert '"/api/program/sync"' in server
    assert '"/api/program/item"' in server
    assert '"/program.js"' in server

    assert 'href="#program"' in shell
    assert '<script src="/program.js" defer></script>' in shell
    assert 'program:"Program control"' in app
    assert '({overview,board,program,comms,models,diagnostics}' in app
    assert 'a.startsWith("program-")' in app
    assert 'function program()' in program
    assert 'function programAction(el)' in program


def test_program_control_ui_names_authority_boundary():
    program = (ROOT / "residual/station/static/program.js").read_text(encoding="utf-8")
    assert "GitHub remains observational input" in program
    assert "STALE AUTHORITY OVERRIDE" in program
    assert "Owner action queue" in program
