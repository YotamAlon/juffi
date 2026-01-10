"""Tests for the HelpMode view"""

import pytest

from juffi.helpers.curses_utils import Size
from juffi.models.juffi_model import JuffiState
from juffi.output_controller import Window
from juffi.views.help import HelpMode
from tests.infra.mock_output_controller import MockOutputController


@pytest.fixture(name="state")
def state_fixture() -> JuffiState:
    """Create a JuffiState instance for testing"""
    return JuffiState()


@pytest.fixture(name="output_controller")
def output_controller_fixture() -> MockOutputController:
    """Create a MockOutputController instance for testing"""
    return MockOutputController(Size(100, 80))


@pytest.fixture(name="mock_window")
def mock_window_fixture(output_controller: MockOutputController) -> Window:
    """Create a MockWindow instance for testing"""
    return output_controller.create_main_window()


@pytest.fixture(name="help_mode")
def help_mode_fixture(state: JuffiState) -> HelpMode:
    """Create a HelpMode instance for testing"""
    return HelpMode(state)


def test_help_mode_draws_title(
    help_mode: HelpMode,
    mock_window: Window,
    state: JuffiState,
    output_controller: MockOutputController,
) -> None:
    """Test that help mode draws the title"""
    state.terminal_size = Size(24, 80)

    help_mode.draw(mock_window)

    line = output_controller.get_screen_line(0)
    assert "JSON LOG VIEWER - HELP" in line


def test_help_mode_draws_navigation_section(
    help_mode: HelpMode,
    mock_window: Window,
    state: JuffiState,
    output_controller: MockOutputController,
) -> None:
    """Test that help mode draws the navigation section"""
    state.terminal_size = Size(100, 80)

    help_mode.draw(mock_window)

    screen = output_controller.get_screen()
    assert "Navigation:" in screen
    assert "Move up" in screen
    assert "Move down" in screen


def test_help_mode_draws_filtering_section(
    help_mode: HelpMode,
    mock_window: Window,
    state: JuffiState,
    output_controller: MockOutputController,
) -> None:
    """Test that help mode draws the filtering section"""
    state.terminal_size = Size(100, 80)

    help_mode.draw(mock_window)

    screen = output_controller.get_screen()
    assert "Filtering & Search:" in screen
    assert "Search all fields" in screen
    assert "Filter by column" in screen


def test_help_mode_draws_quit_instruction(
    help_mode: HelpMode,
    mock_window: Window,
    state: JuffiState,
    output_controller: MockOutputController,
) -> None:
    """Test that help mode draws the quit instruction"""
    state.terminal_size = Size(100, 80)

    help_mode.draw(mock_window)

    screen = output_controller.get_screen()
    assert "Press any key to continue..." in screen
