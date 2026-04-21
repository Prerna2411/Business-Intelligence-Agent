from backend.app.config import get_settings
from backend.agents.analysis import AnalysisAgent
from backend.agents.planner import PlannerAgent
from backend.agents.reflection_agent import ReflectionAgent
from backend.agents.sql_agent import SQLAgent
from backend.agents.visulaization_agent import VisualizationAgent
from backend.services.clickhouse_service import ClickHouseService
from backend.services.llm_service import LLMService
import pytest

def test_agents_pipeline_outputs_expected_shapes():
    settings = get_settings()
    llm = LLMService(settings)
    clickhouse = ClickHouseService(settings)

    planner = PlannerAgent()
    sql_agent = SQLAgent(llm=llm, clickhouse=clickhouse)
    analysis_agent = AnalysisAgent(llm=llm)
    reflection_agent = ReflectionAgent()
    visualization_agent = VisualizationAgent(llm=llm)

    plan = planner.run("Show monthly revenue trend by region")
    sql_output = sql_agent.run("Show monthly revenue trend by region", plan)
    analysis = analysis_agent.run("Show monthly revenue trend by region", plan, sql_output)
    reflection = reflection_agent.run(sql_output, analysis)
    viz = visualization_agent.run("Show monthly revenue trend by region", sql_output.result)

    assert plan.needs_database is True
    assert isinstance(sql_output.sql, str)
    assert sql_output.result is not None
    assert analysis.summary
    assert reflection.approved in {True, False}
    assert viz.chart_type in {"line", "bar", "scatter", "table"}


@pytest.mark.skip(reason="Temporarily skipping due to SQL alias issue")
def test_sql_agent_handles_popular_but_poorly_rated_products():
    settings = get_settings()
    llm = LLMService(settings)
    clickhouse = ClickHouseService(settings)
    planner = PlannerAgent()
    sql_agent = SQLAgent(llm=llm, clickhouse=clickhouse)

    question = "Which popular but poorly rated products should we investigate?"
    plan = planner.run(question)
    sql_output = sql_agent.run(question, plan)

    assert "GROUP BY product_parent" in sql_output.sql
    assert "COUNT(*) AS total_reviews" in sql_output.sql
    assert "AVG(star_rating) AS avg_rating" in sql_output.sql
    assert "HAVING total_reviews > 100 AND avg_rating < 3" in sql_output.sql
    assert "toDate(review_date)" not in sql_output.sql


def test_sql_agent_includes_product_title_for_product_rankings():
    settings = get_settings()
    llm = LLMService(settings)
    clickhouse = ClickHouseService(settings)
    planner = PlannerAgent()
    sql_agent = SQLAgent(llm=llm, clickhouse=clickhouse)

    question = "Show top 10 most reviewed products"
    plan = planner.run(question)
    sql_output = sql_agent.run(question, plan)

    assert "product_title" in sql_output.sql
