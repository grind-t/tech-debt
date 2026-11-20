import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

from tech_debt._entities.tech_debt_search_prompts import (
    DISTRIBUTE_PATHS_PROMPT,
    TECH_DEBT_SEARCH_PROMPTS,
)
from tech_debt._stateless_workflows.search_tech_debt import (
    AgentSession,
    search_tech_debt,
)


class _PathDistribution(BaseModel):
    scopes: list[list[Path]]


def test_search_tech_debt_creates_search_sessions_and_one_distributor(subtests):
    cases = {
        "single_search_session": 1,
        "multiple_search_sessions_boundary": 2,
        "multiple_search_sessions": 5,
    }
    for name, parallelism in cases.items():
        with subtests.test(msg=name, parallelism=parallelism):
            distribution = _PathDistribution(
                scopes=[[Path(f"src/part_{index}")] for index in range(parallelism)]
            )
            distributor = Mock(
                spec_set=AgentSession,
                next_turn=AsyncMock(return_value=distribution),
            )
            search_sessions = [
                Mock(spec_set=AgentSession, next_turn=AsyncMock())
                for _ in range(parallelism)
            ]
            create_session = Mock(side_effect=[distributor, *search_sessions])

            asyncio.run(search_tech_debt(create_session, [Path("src")], parallelism))

            assert create_session.call_count == parallelism + 1


def test_search_tech_debt_distributes_paths_before_creating_search_sessions():
    distribution = _PathDistribution(scopes=[[Path("src/a")], [Path("src/b")]])

    async def distribute(*args, **kwargs):
        assert create_session.call_count == 1
        return distribution

    distributor = Mock(
        spec_set=AgentSession, next_turn=AsyncMock(side_effect=distribute)
    )
    search_sessions = [
        Mock(spec_set=AgentSession, next_turn=AsyncMock()) for _ in range(2)
    ]
    create_session = Mock(side_effect=[distributor, *search_sessions])

    asyncio.run(search_tech_debt(create_session, [Path("src")], parallelism=2))

    distributor.next_turn.assert_awaited_once()
    assert distributor.next_turn.await_args.args[0] == DISTRIBUTE_PATHS_PROMPT.format(
        paths="src", parallelism=2
    )


def test_search_tech_debt_awaits_all_prompts_in_order_for_each_search_scope(subtests):
    distribution = _PathDistribution(
        scopes=[[Path("src/orders")], [Path("src/billing")], [Path("src/reports")]]
    )
    distributor = Mock(
        spec_set=AgentSession, next_turn=AsyncMock(return_value=distribution)
    )
    search_sessions = [
        Mock(spec_set=AgentSession, next_turn=AsyncMock()) for _ in distribution.scopes
    ]
    create_session = Mock(side_effect=[distributor, *search_sessions])

    asyncio.run(search_tech_debt(create_session, [Path("src")], len(search_sessions)))

    for index, (session, scope) in enumerate(
        zip(search_sessions, distribution.scopes, strict=True)
    ):
        with subtests.test(session=index):
            assert session.next_turn.await_count == len(TECH_DEBT_SEARCH_PROMPTS)
            expected_prompts = [
                prompt.format(paths=str(scope[0]))
                for prompt in TECH_DEBT_SEARCH_PROMPTS
            ]
            actual_prompts = [
                call.args[0] for call in session.next_turn.await_args_list
            ]
            assert actual_prompts == expected_prompts


def test_search_tech_debt_rejects_nonpositive_parallelism(subtests):
    cases = {"zero": 0, "negative": -1}
    for name, parallelism in cases.items():
        with subtests.test(msg=name, parallelism=parallelism):
            create_session = Mock(
                side_effect=lambda: Mock(spec_set=AgentSession, next_turn=AsyncMock())
            )

            with pytest.raises(ValueError, match="parallelism"):
                asyncio.run(
                    search_tech_debt(create_session, [Path("src")], parallelism)
                )

            create_session.assert_not_called()
