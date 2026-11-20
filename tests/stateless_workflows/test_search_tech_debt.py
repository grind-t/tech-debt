import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from tech_debt._entities.tech_debt_search_prompts import TECH_DEBT_SEARCH_PROMPTS
from tech_debt._stateless_workflows.search_tech_debt import (
    AgentSession,
    search_tech_debt,
)


def test_search_tech_debt_creates_requested_number_of_sessions(subtests):
    cases = {
        "single_session": 1,
        "multiple_sessions_boundary": 2,
        "multiple_sessions": 5,
    }
    for name, parallelism in cases.items():
        with subtests.test(msg=name, parallelism=parallelism):
            create_session = Mock(
                side_effect=lambda: Mock(spec_set=AgentSession, next_turn=AsyncMock())
            )

            asyncio.run(search_tech_debt(create_session, [Path("src")], parallelism))

            assert create_session.call_count == parallelism


def test_search_tech_debt_awaits_all_prompts_in_order_for_each_session(subtests):
    sessions = [Mock(spec_set=AgentSession, next_turn=AsyncMock()) for _ in range(3)]
    create_session = Mock(side_effect=sessions)
    expected_prompts = [
        prompt.format(paths="src") for prompt in TECH_DEBT_SEARCH_PROMPTS
    ]

    asyncio.run(search_tech_debt(create_session, [Path("src")], len(sessions)))

    for index, session in enumerate(sessions):
        with subtests.test(session=index):
            assert session.next_turn.await_count == len(TECH_DEBT_SEARCH_PROMPTS)
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
