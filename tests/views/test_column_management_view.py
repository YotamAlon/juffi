"""Test the column management view"""

import pytest

from juffi.helpers.curses_utils import Size
from juffi.helpers.indexed_dict import IndexedDict
from juffi.models.column import Column
from juffi.models.juffi_model import JuffiState
from juffi.output_controller import Window
from juffi.views.column_management import ColumnManagementMode
from tests.infra.mock_output_controller import MockOutputController


@pytest.fixture(name="state")
def state_fixture() -> JuffiState:
    """Create a JuffiState instance for testing"""
    return JuffiState()


@pytest.fixture(name="output_controller")
def output_controller_fixture() -> MockOutputController:
    """Create a MockOutputController instance for testing"""
    return MockOutputController(Size(24, 80))


@pytest.fixture(name="mock_window")
def mock_window_fixture(output_controller: MockOutputController) -> Window:
    """Create a MockWindow instance for testing"""
    return output_controller.create_main_window()


@pytest.fixture(name="column_management_mode")
def column_management_mode_fixture(
    state: JuffiState, mock_window: Window
) -> ColumnManagementMode:
    """Create a ColumnManagementMode instance for testing"""
    return ColumnManagementMode(state, mock_window)


def test_column_management_draws_title(
    column_management_mode: ColumnManagementMode,
    output_controller: MockOutputController,
):
    """Test that column management screen displays the title"""
    column_management_mode.draw()

    screen = output_controller.get_screen()
    assert "Column Management" in screen


def test_column_management_draws_instructions(
    column_management_mode: ColumnManagementMode,
    output_controller: MockOutputController,
):
    """Test that column management screen displays instructions"""
    column_management_mode.draw()

    screen = output_controller.get_screen()
    assert "Move between panes" in screen or "Navigate" in screen
    assert "Tab" in screen


def test_column_management_draws_panes(
    column_management_mode: ColumnManagementMode,
    output_controller: MockOutputController,
):
    """Test that column management screen displays both panes"""
    column_management_mode.draw()

    screen = output_controller.get_screen()
    assert "Available Columns" in screen
    assert "Selected Columns" in screen


def test_column_management_draws_buttons(
    column_management_mode: ColumnManagementMode,
    output_controller: MockOutputController,
):
    """Test that column management screen displays all buttons"""
    column_management_mode.draw()

    screen = output_controller.get_screen()
    assert "OK" in screen
    assert "Cancel" in screen
    assert "Reset" in screen


def test_column_management_displays_available_columns(
    state: JuffiState, mock_window: Window, output_controller: MockOutputController
):
    """Test that available columns are displayed in the available pane"""
    state.columns = IndexedDict(
        {
            "timestamp": Column("timestamp"),
            "level": Column("level"),
        }
    )
    state.all_discovered_columns = {"timestamp", "level", "message", "service"}
    view = ColumnManagementMode(state, mock_window)

    view.enter_mode()
    view.draw()

    screen = output_controller.get_screen()
    assert "message" in screen
    assert "service" in screen


def test_column_management_displays_selected_columns(
    state: JuffiState, mock_window: Window, output_controller: MockOutputController
):
    """Test that selected columns are displayed in the selected pane"""
    state.columns = IndexedDict(
        {
            "timestamp": Column("timestamp"),
            "level": Column("level"),
            "message": Column("message"),
        }
    )
    state.all_discovered_columns = {"timestamp", "level", "message", "service"}
    view = ColumnManagementMode(state, mock_window)

    view.enter_mode()
    view.draw()

    screen = output_controller.get_screen()
    assert "timestamp" in screen
    assert "level" in screen
    assert "message" in screen
