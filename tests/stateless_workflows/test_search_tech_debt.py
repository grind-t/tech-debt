import asyncio
from pathlib import Path
from unittest.mock import Mock

import pytest

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
            create_session = Mock(side_effect=lambda: Mock(spec_set=AgentSession))

            asyncio.run(search_tech_debt(create_session, [Path("src")], parallelism))

            assert create_session.call_count == parallelism


def test_search_tech_debt_rejects_nonpositive_parallelism(subtests):
    cases = {"zero": 0, "negative": -1}
    for name, parallelism in cases.items():
        with subtests.test(msg=name, parallelism=parallelism):
            create_session = Mock(side_effect=lambda: Mock(spec_set=AgentSession))

            with pytest.raises(ValueError, match="parallelism"):
                asyncio.run(
                    search_tech_debt(create_session, [Path("src")], parallelism)
                )

            create_session.assert_not_called()
