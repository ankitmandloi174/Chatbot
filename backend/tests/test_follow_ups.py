"""Follow-up suggestions must be specific, grounded in the datasets, and new."""

import json

from app.schemas.dataset import ColumnMeta
from app.services.suggestions.candidates import generate_candidates
from app.services.suggestions.follow_up_service import FollowUpService
from app.services.suggestions.language import mentions, similar
from app.services.suggestions.llm_suggester import LLMSuggester
from app.services.suggestions.models import (
    ColumnRef,
    FollowUpContext,
    JoinKey,
    Suggestion,
    TableProfile,
)
from app.services.suggestions.validator import validate


def col(name: str, kind: str, unique: int = 5, samples=(), low=None, high=None) -> ColumnMeta:
    return ColumnMeta(
        name=name, dtype="x", kind=kind, null_count=0, unique_count=unique,
        samples=list(samples), min=low, max=high,
    )


SALES = TableProfile(
    "sales", "sales.csv", 100,
    (
        col("order_id", "integer", 100),
        col("order_date", "datetime", 100, low="2024-01-01", high="2024-12-31"),
        col("region", "categorical", 3, ["North", "South"]),
        col("channel", "categorical", 2, ["Web", "Store"]),
        col("revenue", "numeric", 90),
    ),
    missing={}, outliers={},
)
TARGETS = TableProfile(
    "targets", "targets.csv", 3, (col("region", "categorical", 3), col("target", "numeric", 3)), {}, {}
)
HR = TableProfile("employees", "employees.csv", 10, (col("department", "categorical", 3), col("salary", "numeric", 9)), {}, {})


def context(used=(("sales", "region"), ("sales", "revenue")), **overrides) -> FollowUpContext:
    values = dict(
        question="Revenue by region?",
        profiles=(SALES, TARGETS, HR),
        used=tuple(ColumnRef(*u) for u in used),
        joins=(JoinKey(ColumnRef("sales", "region"), ColumnRef("targets", "region")),),
        result_text="region revenue\nNorth 10\nSouth 4",
        result_rows=3,
        previous_questions=(),
    )
    return FollowUpContext(**{**values, **overrides})


def moves(ctx: FollowUpContext) -> dict[str, str]:
    return {s.move: s.question for s in generate_candidates(ctx)}


# --- deterministic candidates -------------------------------------------------

def test_candidates_use_real_columns_and_name_the_file_when_several_datasets():
    found = moves(context())
    assert found["break_down"] == "Break down revenue by channel in sales"
    assert found["trend"] == "Show the monthly trend of revenue in sales"
    assert found["cross_file"] == "Combine sales and targets on region and compare target"
    assert found["focus"] == "Compare revenue for North with the average across all region values in sales"


def test_unrelated_dataset_is_never_suggested():
    assert not any("salary" in q or "department" in q for q in moves(context()).values())


def test_trend_is_replaced_by_window_comparison_when_time_was_already_used():
    found = moves(context(used=(("sales", "order_date"), ("sales", "revenue"))))
    assert "trend" not in found
    assert found["change_window"].startswith("Compare revenue in the last 3 months")


def test_ranking_only_for_long_results():
    assert "ranking" not in moves(context(result_rows=3))
    assert moves(context(result_rows=40))["ranking"] == "Show the top 10 region by revenue in sales"


def test_outlier_and_missing_value_moves_come_from_the_cleaning_report():
    dirty = TableProfile(SALES.table_name, SALES.file_name, 100, SALES.columns, {"revenue": 4}, {"revenue": 2})
    found = moves(context(profiles=(dirty,), joins=()))
    assert found["outliers"] == "Which rows have unusually high or low revenue?"
    assert found["data_quality"] == "How many rows are missing revenue?"
    assert "outliers" not in moves(context(profiles=(SALES,), joins=()))


def test_no_trend_for_a_date_range_too_short_to_trend():
    short = TableProfile("sales", "sales.csv", 5, (
        col("order_date", "datetime", 5, low="2024-01-01", high="2024-01-09"), col("revenue", "numeric", 5),
    ), {}, {})
    assert "trend" not in moves(context(profiles=(short,), joins=(), used=(("sales", "revenue"),)))


def test_every_candidate_names_an_existing_column():
    ctx = context(result_rows=40)
    known = {(p.table_name, c.name) for p in ctx.profiles for c in p.columns}
    for suggestion in generate_candidates(ctx):
        assert suggestion.columns and all(tuple(ref) in known for ref in suggestion.columns)
        assert any(mentions(suggestion.question, ref.column) for ref in suggestion.columns)
    assert validate(generate_candidates(ctx), ctx) == generate_candidates(ctx)


# --- validator -----------------------------------------------------------------

def s(question: str, *refs: tuple[str, str]) -> Suggestion:
    return Suggestion(question, "insight", tuple(ColumnRef(*r) for r in refs))


def test_validator_rejects_vague_hallucinated_unrelated_and_repeated_questions():
    ctx = context(previous_questions=("Show monthly revenue trend by channel",))
    rejected = [
        s("What else can I learn?", ("sales", "revenue")),
        s("Tell me more about revenue", ("sales", "revenue")),
        s("Show profit by warehouse", ("sales", "profit")),                    # column does not exist
        s("Show salary by department", ("employees", "salary")),               # dataset not relevant to this answer
        s("Which region is doing best overall?", ("sales", "revenue")),        # mentions no listed column
        s("Show revenue by region please", ("sales", "revenue")),              # repeats the current question
        s("Show the monthly revenue trend by channel", ("sales", "revenue")),  # repeats an earlier one
        s("Why is revenue low?"),                                          # no columns declared
    ]
    assert validate(rejected, ctx) == []


def test_validator_keeps_specific_questions_and_drops_duplicates_among_them():
    ctx = context()
    first = s("Why is revenue in North so much higher than in South?", ("sales", "revenue"))
    twin = s("Why is revenue in North so much higher than South?", ("sales", "revenue"))
    other = s("Compare revenue by channel", ("sales", "revenue"), ("sales", "channel"))
    assert validate([first, twin, other], ctx) == [first, other]


def test_column_mention_handles_underscores_and_plurals():
    assert mentions("Show the order dates with gaps", "order_date")
    assert not mentions("Show dates", "order_date")
    assert similar("Show revenue by channel", "show the revenue by channel")


# --- service -------------------------------------------------------------------

class _Replies:
    def __init__(self, reply: str | Exception) -> None:
        self.reply, self.prompts = reply, []

    def complete(self, system: str, user: str) -> str:
        self.prompts.append(user)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def service(reply: str | Exception | None, limit: int = 3) -> tuple[FollowUpService, _Replies | None]:
    llm = _Replies(reply) if reply is not None else None
    return FollowUpService(LLMSuggester(llm, limit) if llm else None, limit), llm


def test_llm_questions_come_first_and_bad_ones_are_filtered():
    reply = json.dumps({"suggestions": [
        {"question": "Why is revenue in North higher than in South by region?", "columns": ["sales.revenue", "sales.region"]},
        {"question": "Anything else worth looking at?", "columns": ["sales.revenue"]},
        {"question": "Show salary by department", "columns": ["employees.salary"]},
    ]})
    follow_ups = service(reply)[0].suggest(context())
    assert follow_ups[0] == "Why is revenue in North higher than in South by region?"
    assert len(follow_ups) == 3
    assert all("salary" not in q and "Anything else" not in q for q in follow_ups)


def test_service_falls_back_to_profile_questions_when_llm_fails_or_returns_junk():
    for reply in (RuntimeError("provider down"), "not json at all", '{"suggestions": "oops"}', None):
        follow_ups = service(reply)[0].suggest(context())
        assert follow_ups[0] == "Break down revenue by channel in sales"
        assert len(follow_ups) == 3


def test_service_shows_nothing_rather_than_filler_when_nothing_is_valid():
    bare = TableProfile("sales", "sales.csv", 5, (col("region", "categorical", 1),), {}, {})
    ctx = context(profiles=(bare,), joins=(), used=(("sales", "region"),))
    assert service('{"suggestions": [{"question": "Tell me more", "columns": []}]}')[0].suggest(ctx) == []


def test_prompt_only_lists_columns_of_relevant_datasets_and_previous_questions():
    llm_service, llm = service('{"suggestions": []}')
    llm_service.suggest(context(previous_questions=("Earlier question about channel?",)))
    prompt = llm.prompts[0]
    assert "targets" in prompt and "employees" not in prompt and "salary" not in prompt
    assert "Earlier question about channel?" in prompt
    assert "Break down revenue by channel in sales" in prompt  # already-covered ideas are not repeated


def test_respects_the_configured_limit():
    assert len(service(None, limit=2)[0].suggest(context())) == 2
