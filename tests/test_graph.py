from services.service import BIService


def test_workflow_runs_full_state():
    service = BIService()
    result = service.ask("Show monthly revenue trend by region")

    assert result["plan"] is not None
    assert result["sql"] is not None
    assert result["analysis"] is not None
    assert result["reflection"] is not None
    assert result["visualization"] is not None
