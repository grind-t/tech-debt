import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import TypeAdapter

from tech_debt._entities.defect import Defect
from tech_debt._entities.minimal_findings import MinimalFindings
from tech_debt._entities.path_distribution import PathDistribution
from tech_debt._entities.search_tech_debt_prompt import (
    DEDUPLICATE_FINDINGS_PROMPT,
    DISTRIBUTE_PATHS_PROMPT,
    FORMAT_FINDINGS_PROMPT,
    SEARCH_TECH_DEBT_PROMPT,
)
from tech_debt._stateless_workflows.search_tech_debt import (
    AgentSession,
    search_tech_debt,
)

_SEARCH_PROMPTS = (
    SEARCH_TECH_DEBT_PROMPT,
    FORMAT_FINDINGS_PROMPT,
)


async def _run_search(create_session, paths, parallelism):
    # These tests exercise session orchestration with a stubbed filesystem snapshot.
    return await search_tech_debt(
        create_session,
        paths,
        parallelism,
        normalize_paths=lambda values: [Path(path).resolve() for path in values],
        list_files=lambda values: frozenset(),
    )


def test_search_tech_debt_creates_search_sessions_distributor_and_deduplicator(
    subtests,
):
    cases = {
        "multiple_search_sessions_boundary": 2,
        "multiple_search_sessions": 5,
    }
    for name, parallelism in cases.items():
        with subtests.test(msg=name, parallelism=parallelism):
            distribution = [
                [Path(f"src/part_{index}").resolve()] for index in range(parallelism)
            ]
            distributor = Mock(
                spec_set=AgentSession,
                next_turn=AsyncMock(return_value=distribution),
            )
            search_sessions = [
                Mock(
                    spec_set=AgentSession,
                    next_turn=AsyncMock(return_value=[]),
                )
                for _ in range(parallelism)
            ]
            deduplicator = Mock(
                spec_set=AgentSession, next_turn=AsyncMock(return_value=[])
            )
            create_session = Mock(
                side_effect=[distributor, *search_sessions, deduplicator]
            )

            asyncio.run(_run_search(create_session, [Path("src")], parallelism))

            assert create_session.call_count == parallelism + 2


def test_search_tech_debt_skips_distribution_for_single_search_session():
    session = Mock(
        spec_set=AgentSession,
        next_turn=AsyncMock(return_value=[]),
    )
    create_session = Mock(side_effect=[session])

    asyncio.run(_run_search(create_session, [Path("src")], parallelism=1))

    create_session.assert_called_once_with()
    assert session.next_turn.await_count == len(_SEARCH_PROMPTS)
    actual_prompts = [call.args[0] for call in session.next_turn.await_args_list]
    expected_prompts = [
        prompt.format(paths=str(Path("src").resolve())) for prompt in _SEARCH_PROMPTS
    ]
    assert actual_prompts == expected_prompts


def test_search_tech_debt_distributes_paths_before_creating_search_sessions():
    distribution = [[Path("src/a").resolve()], [Path("src/b").resolve()]]

    async def distribute(*args, **kwargs):
        assert create_session.call_count == 1
        return distribution

    distributor = Mock(
        spec_set=AgentSession, next_turn=AsyncMock(side_effect=distribute)
    )
    search_sessions = [
        Mock(
            spec_set=AgentSession,
            next_turn=AsyncMock(return_value=[]),
        )
        for _ in range(2)
    ]
    deduplicator = Mock(spec_set=AgentSession, next_turn=AsyncMock(return_value=[]))
    create_session = Mock(side_effect=[distributor, *search_sessions, deduplicator])

    asyncio.run(_run_search(create_session, [Path("src")], parallelism=2))

    distributor.next_turn.assert_awaited_once()
    assert distributor.next_turn.await_args.args[0] == DISTRIBUTE_PATHS_PROMPT.format(
        paths=str(Path("src").resolve()), parallelism=2
    )


def test_search_tech_debt_awaits_all_prompts_in_order_for_each_search_scope(subtests):
    distribution = [
        [Path("src/orders").resolve()],
        [Path("src/billing").resolve()],
        [Path("src/reports").resolve()],
    ]
    distributor = Mock(
        spec_set=AgentSession, next_turn=AsyncMock(return_value=distribution)
    )
    search_sessions = [
        Mock(
            spec_set=AgentSession,
            next_turn=AsyncMock(return_value=[]),
        )
        for _ in distribution
    ]
    deduplicator = Mock(spec_set=AgentSession, next_turn=AsyncMock(return_value=[]))
    create_session = Mock(side_effect=[distributor, *search_sessions, deduplicator])

    asyncio.run(_run_search(create_session, [Path("src")], len(search_sessions)))

    for index, (session, scope) in enumerate(
        zip(search_sessions, distribution, strict=True)
    ):
        with subtests.test(session=index):
            assert session.next_turn.await_count == len(_SEARCH_PROMPTS)
            expected_prompts = [
                prompt.format(paths=str(scope[0])) for prompt in _SEARCH_PROMPTS
            ]
            actual_prompts = [
                call.args[0] for call in session.next_turn.await_args_list
            ]
            assert actual_prompts == expected_prompts
            adapters = [call.args[1] for call in session.next_turn.await_args_list]
            assert [adapter.json_schema() for adapter in adapters] == [
                TypeAdapter(MinimalFindings).json_schema(),
                TypeAdapter(list[Defect]).json_schema(),
            ]


def test_search_tech_debt_rejects_nonpositive_parallelism(subtests):
    cases = {"zero": 0, "negative": -1}
    for name, parallelism in cases.items():
        with subtests.test(msg=name, parallelism=parallelism):
            create_session = Mock(
                side_effect=lambda: Mock(
                    spec_set=AgentSession,
                    next_turn=AsyncMock(return_value=[]),
                )
            )

            with pytest.raises(ValueError, match="parallelism"):
                asyncio.run(_run_search(create_session, [Path("src")], parallelism))

            create_session.assert_not_called()


def _defect(description):
    return Defect.model_validate(
        {
            "description": description,
            "location": "src/orders.py",
            "type": "Duplicated Code (Fowler, Refactoring, 2nd ed.)",
            "characteristic": "Maintainability",
            "subcharacteristic": "Modifiability",
            "risks": {
                "most_likely": {
                    "event": "A maintainer changes duplicated code",
                    "consequence": "Changes require repeated edits and reviews",
                    "likelihood": "High",
                    "severity": "Minor",
                },
                "worst_credible": None,
            },
        }
    )


def _minimal_findings(defects):
    return MinimalFindings.model_validate(
        {
            "findings": [
                defect.model_dump(include={"description", "location"})
                for defect in defects
            ]
        }
    )


def test_search_tech_debt_returns_formatted_findings_including_not_applicable_risks():
    not_applicable = _defect("Finding with an unrealistic risk")
    not_applicable.risks.most_likely.likelihood = "Not applicable"
    confirmed = _defect("Confirmed defect")
    session = Mock(
        spec_set=AgentSession,
        next_turn=AsyncMock(
            side_effect=[
                _minimal_findings([not_applicable, confirmed]),
                [not_applicable, confirmed],
            ]
        ),
    )

    result = asyncio.run(
        _run_search(lambda: session, [Path("src"), Path("tests")], parallelism=1)
    )

    assert result == [not_applicable, confirmed]
    calls = session.next_turn.await_args_list
    assert len(calls) == 2
    assert calls[0].args[0] == _SEARCH_PROMPTS[0].format(
        paths=", ".join(str(Path(path).resolve()) for path in ("src", "tests"))
    )
    assert isinstance(calls[0].args[1], TypeAdapter)
    first_schema = calls[0].args[1]
    assert first_schema.json_schema() == TypeAdapter(MinimalFindings).json_schema()
    assert first_schema.validate_json(
        '{"findings": [{"description": "Candidate", "location": "src/orders.py"}]}'
    ) == _minimal_findings([_defect("Candidate")])
    assert isinstance(calls[-1].args[1], TypeAdapter)
    assert calls[-1].args[1].json_schema() == TypeAdapter(list[Defect]).json_schema()


def test_search_tech_debt_collects_findings_from_all_search_scopes():
    defects = [_defect("Orders defect"), _defect("Billing defect")]
    distribution = [[Path("src/orders").resolve()], [Path("src/billing").resolve()]]
    distributor = Mock(
        spec_set=AgentSession, next_turn=AsyncMock(return_value=distribution)
    )
    sessions = [
        Mock(
            spec_set=AgentSession,
            next_turn=AsyncMock(
                side_effect=[
                    _minimal_findings([defect]),
                    [defect],
                ]
            ),
        )
        for defect in defects
    ]

    deduplicator = Mock(
        spec_set=AgentSession, next_turn=AsyncMock(return_value=defects)
    )
    result = asyncio.run(
        _run_search(
            Mock(side_effect=[distributor, *sessions, deduplicator]),
            [Path("src")],
            parallelism=2,
        )
    )

    assert result == defects
    schema = distributor.next_turn.await_args.args[1]
    assert isinstance(schema, TypeAdapter)
    assert schema.json_schema() == TypeAdapter(PathDistribution).json_schema()


def test_search_tech_debt_deduplicates_findings_in_one_final_session():
    duplicate = _defect("Duplicated finding")
    unique = _defect("Unique finding")
    findings = [[duplicate], [duplicate, unique]]
    distributor = Mock(
        spec_set=AgentSession,
        next_turn=AsyncMock(
            return_value=[[Path("src/a").resolve()], [Path("src/b").resolve()]]
        ),
    )
    search_sessions = [
        Mock(
            spec_set=AgentSession,
            next_turn=AsyncMock(side_effect=[_minimal_findings(result), result]),
        )
        for result in findings
    ]
    deduplicator = Mock(
        spec_set=AgentSession,
        next_turn=AsyncMock(return_value=[duplicate, unique]),
    )
    sessions = [distributor, *search_sessions, deduplicator]

    def create():
        index = create_session.call_count - 1
        if index == len(sessions) - 1:
            assert all(
                session.next_turn.await_count == len(_SEARCH_PROMPTS)
                for session in search_sessions
            )
        return sessions[index]

    create_session = Mock(side_effect=create)

    result = asyncio.run(_run_search(create_session, [Path("src")], parallelism=2))

    assert create_session.call_count == 4
    deduplicator.next_turn.assert_awaited_once()
    call = deduplicator.next_turn.await_args
    adapter = TypeAdapter(list[Defect])
    assert call.args[0] == DEDUPLICATE_FINDINGS_PROMPT.format(
        findings=adapter.dump_json([duplicate, duplicate, unique]).decode("utf-8")
    )
    assert isinstance(call.args[1], TypeAdapter)
    assert call.args[1].json_schema() == adapter.json_schema()
    assert result == [duplicate, unique]
