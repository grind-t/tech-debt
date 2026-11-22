import asyncio
from pathlib import PurePosixPath
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import TypeAdapter

from tech_debt._entities.defect import Defect
from tech_debt._entities.minimal_findings import MinimalFindings
from tech_debt._entities.search_tech_debt_prompt import (
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
_PROJECT = PurePosixPath("/project")
_DISTRIBUTE_PATHS = "tech_debt._stateless_workflows.search_tech_debt.distribute_paths"


async def _run_search(create_session, paths, parallelism, *, distribution=None):
    if distribution is None:
        distribution = [
            [_PROJECT / paths[0] / f"part_{index}"] for index in range(parallelism)
        ]

    with patch(_DISTRIBUTE_PATHS, return_value=distribution):
        return await search_tech_debt(
            create_session,
            paths,
            parallelism,
            normalize_paths=lambda values: [_PROJECT / path for path in values],
            list_files=lambda _: {},
            log_info=Mock(),
        )


def test_search_tech_debt_creates_one_session_per_scope(subtests):
    cases = {
        "multiple_search_sessions_boundary": 2,
        "multiple_search_sessions": 5,
    }
    for name, parallelism in cases.items():
        with subtests.test(msg=name, parallelism=parallelism):
            search_sessions = [
                Mock(
                    spec_set=AgentSession,
                    next_turn=AsyncMock(return_value=[]),
                )
                for _ in range(parallelism)
            ]
            create_session = Mock(side_effect=search_sessions)

            asyncio.run(
                _run_search(create_session, [PurePosixPath("src")], parallelism)
            )

            assert create_session.call_count == parallelism


def test_search_tech_debt_skips_distribution_for_single_search_session():
    session = Mock(
        spec_set=AgentSession,
        next_turn=AsyncMock(return_value=[]),
    )
    create_session = Mock(side_effect=[session])

    asyncio.run(_run_search(create_session, [PurePosixPath("src")], parallelism=1))

    create_session.assert_called_once_with()
    assert session.next_turn.await_count == len(_SEARCH_PROMPTS)
    actual_prompts = [call.args[0] for call in session.next_turn.await_args_list]
    expected_prompts = [
        prompt.format(paths=str(_PROJECT / "src")) for prompt in _SEARCH_PROMPTS
    ]
    assert actual_prompts == expected_prompts


def test_search_tech_debt_awaits_all_prompts_in_order_for_each_search_scope(subtests):
    distribution = [
        [_PROJECT / "src/billing"],
        [_PROJECT / "src/orders"],
        [_PROJECT / "src/reports"],
    ]
    search_sessions = [
        Mock(
            spec_set=AgentSession,
            next_turn=AsyncMock(return_value=[]),
        )
        for _ in distribution
    ]
    create_session = Mock(side_effect=search_sessions)

    asyncio.run(
        _run_search(
            create_session,
            [PurePosixPath("src")],
            len(search_sessions),
            distribution=distribution,
        )
    )

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


def test_search_tech_debt_aborts_before_starting_sessions_if_distribution_fails():
    paths = [PurePosixPath("src")]
    normalized = [_PROJECT / "src"]
    files = {normalized[0] / "only.py": 42}
    normalize_paths = Mock(return_value=normalized)
    list_files = Mock(return_value=files)
    create_session = Mock()
    with (
        patch(
            _DISTRIBUTE_PATHS, side_effect=ValueError("distribution failed")
        ) as distribute,
        pytest.raises(ValueError, match="distribution failed"),
    ):
        asyncio.run(
            search_tech_debt(
                create_session,
                paths,
                2,
                normalize_paths=normalize_paths,
                list_files=list_files,
                log_info=Mock(),
            )
        )

    normalize_paths.assert_called_once_with(paths)
    list_files.assert_called_once_with(normalized)
    distribute.assert_called_once_with(normalized, files, 2)
    create_session.assert_not_called()


def test_search_tech_debt_logs_and_uses_reduced_parallelism(subtests):
    root = _PROJECT / "src"
    files = {root / "first.py": 20, root / "second.py": 10}
    for scope_count in range(3):
        with subtests.test(scope_count=scope_count):
            scopes = [[file] for file in list(files)[:scope_count]]
            sessions = [
                Mock(spec_set=AgentSession, next_turn=AsyncMock(return_value=[]))
                for _ in scopes
            ]
            create_session = Mock(side_effect=sessions)
            log_info = Mock()
            with patch(_DISTRIBUTE_PATHS, return_value=scopes):
                result = asyncio.run(
                    search_tech_debt(
                        create_session,
                        [root],
                        3,
                        normalize_paths=list,
                        list_files=Mock(
                            return_value={scope[0]: files[scope[0]] for scope in scopes}
                        ),
                        log_info=log_info,
                    )
                )

            assert result == []
            log_info.assert_called_once_with(
                f"Reduced parallelism from 3 to {scope_count}."
            )
            assert create_session.call_count == scope_count
            for session, scope in zip(sessions, scopes, strict=True):
                assert session.next_turn.await_args_list[0].args[0] == (
                    SEARCH_TECH_DEBT_PROMPT.format(paths=str(scope[0]))
                )


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
                asyncio.run(
                    _run_search(create_session, [PurePosixPath("src")], parallelism)
                )

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
        _run_search(
            lambda: session,
            [PurePosixPath("src"), PurePosixPath("tests")],
            parallelism=1,
        )
    )

    assert result == [not_applicable, confirmed]
    calls = session.next_turn.await_args_list
    assert len(calls) == 2
    assert calls[0].args[0] == _SEARCH_PROMPTS[0].format(
        paths=", ".join(str(_PROJECT / path) for path in ("src", "tests"))
    )
    assert isinstance(calls[0].args[1], TypeAdapter)
    first_schema = calls[0].args[1]
    assert first_schema.json_schema() == TypeAdapter(MinimalFindings).json_schema()
    assert isinstance(calls[-1].args[1], TypeAdapter)
    assert calls[-1].args[1].json_schema() == TypeAdapter(list[Defect]).json_schema()


def test_search_tech_debt_returns_all_findings_in_scope_order():
    orders = _defect("Orders defect")
    shared = _defect("Finding reported by both scopes")
    billing = _defect("Billing defect")
    findings = [[orders, shared], [shared, billing]]
    search_sessions = [
        Mock(
            spec_set=AgentSession,
            next_turn=AsyncMock(side_effect=[_minimal_findings(result), result]),
        )
        for result in findings
    ]
    create_session = Mock(side_effect=search_sessions)

    result = asyncio.run(
        _run_search(create_session, [PurePosixPath("src")], parallelism=2)
    )

    assert create_session.call_count == 2
    assert result == [orders, shared, shared, billing]
