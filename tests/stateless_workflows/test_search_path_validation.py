import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from tech_debt._entities.search_tech_debt_prompt import (
    CORRECT_PATH_DISTRIBUTION_PROMPT,
    SEARCH_TECH_DEBT_PROMPT,
)
from tech_debt._stateless_effects.list_search_files import list_search_files
from tech_debt._stateless_effects.normalize_search_paths import normalize_search_paths
from tech_debt._stateless_workflows.search_tech_debt import (
    AgentSession,
    search_tech_debt,
)


def _tree(tmp_path):
    root = tmp_path / "src"
    first, second = root / "a", root / "b"
    for directory in (first, second):
        directory.mkdir(parents=True)
        (directory / "module.py").write_text("", encoding="utf-8")
    return root.resolve(), [[first.resolve()], [second.resolve()]]


async def _search(create_session, paths):
    return await search_tech_debt(
        create_session,
        paths,
        parallelism=2,
        normalize_paths=normalize_search_paths,
        list_files=list_search_files,
    )


def test_search_corrects_invalid_distributions_before_starting_sessions(
    tmp_path, subtests
):
    root, corrected = _tree(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "other.py").write_text("", encoding="utf-8")
    empty = root / "empty"
    empty.mkdir()
    alias = root / "alias"
    alias.symlink_to(corrected[0][0], target_is_directory=True)
    escape = root / "escape"
    escape.symlink_to(outside, target_is_directory=True)
    cases = {
        "wrong_count": [[root]],
        "empty_scope": [[], [root]],
        "overlap": [[root], corrected[0]],
        "missing_files": [corrected[0], [empty]],
        "outside": [corrected[0], [outside]],
        "missing_path": [corrected[0], [root / "missing"]],
        "symlink_escape": [corrected[0], [escape]],
        "symlink_overlap": [[alias], [*corrected[0], *corrected[1]]],
        "parent_escape": [corrected[0], [root / "../outside"]],
        "relative": [[Path("a")], corrected[1]],
    }
    for name, initial in cases.items():
        with subtests.test(msg=name):
            distributor = Mock(
                spec_set=AgentSession,
                next_turn=AsyncMock(side_effect=[initial, corrected]),
            )
            searches = [
                Mock(spec_set=AgentSession, next_turn=AsyncMock(return_value=[]))
                for _ in range(2)
            ]
            deduplicator = Mock(
                spec_set=AgentSession, next_turn=AsyncMock(return_value=[])
            )

            session_iterator = iter([distributor, *searches, deduplicator])

            def create(distributor=distributor, sessions=session_iterator):
                session = next(sessions)
                if session is not distributor:
                    assert distributor.next_turn.await_count == 2
                return session

            create_session = Mock(side_effect=create)

            assert asyncio.run(_search(create_session, [root])) == []

            assert create_session.call_count == 4
            assert distributor.next_turn.await_count == 2
            initial_call, correction_call = distributor.next_turn.await_args_list
            assert correction_call.args[1] is initial_call.args[1]
            assert correction_call.args[0].startswith(
                CORRECT_PATH_DISTRIBUTION_PROMPT.split("{errors}")[0]
            )
            for session, scope in zip(searches, corrected, strict=True):
                assert session.next_turn.await_args_list[0].args[0] == (
                    SEARCH_TECH_DEBT_PROMPT.format(paths=str(scope[0]))
                )


def test_search_does_not_retry_again_for_a_different_distribution_error(tmp_path):
    root, valid = _tree(tmp_path)
    distributor = Mock(
        spec_set=AgentSession,
        next_turn=AsyncMock(side_effect=[[[Path("a")], valid[1]], [[root], valid[0]]]),
    )
    create_session = Mock(side_effect=[distributor])

    with pytest.raises(ValueError, match="overlap"):
        asyncio.run(_search(create_session, [root]))

    create_session.assert_called_once_with()
    assert distributor.next_turn.await_count == 2


def test_search_uses_canonical_scopes_without_retry_when_links_are_valid(tmp_path):
    root, valid = _tree(tmp_path)
    alias = root / "alias"
    alias.symlink_to(valid[0][0], target_is_directory=True)
    distributor = Mock(
        spec_set=AgentSession,
        next_turn=AsyncMock(return_value=[[alias / "../alias"], valid[1]]),
    )
    searches = [
        Mock(spec_set=AgentSession, next_turn=AsyncMock(return_value=[]))
        for _ in range(2)
    ]
    deduplicator = Mock(spec_set=AgentSession, next_turn=AsyncMock(return_value=[]))

    asyncio.run(
        _search(Mock(side_effect=[distributor, *searches, deduplicator]), [root])
    )

    distributor.next_turn.assert_awaited_once()
    assert searches[0].next_turn.await_args_list[0].args[0] == (
        SEARCH_TECH_DEBT_PROMPT.format(paths=str(valid[0][0]))
    )
