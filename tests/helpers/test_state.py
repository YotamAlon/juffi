"""Tests for the State infrastructure (Observable, Field, State)."""

from unittest.mock import Mock

from juffi.helpers.state import Field, Observable, State


def test_observable_tracks_list_mutations() -> None:
    """Test that Observable tracks mutations on list objects."""
    # Arrange
    callback = Mock()
    data = [1, 2, 3]
    obs = Observable(data, callback)

    # Act
    obs.append(4)

    # Assert
    callback.assert_called_once()
    assert obs == [1, 2, 3, 4]


def test_observable_tracks_dict_mutations() -> None:
    """Test that Observable tracks mutations on dict objects."""
    # Arrange
    callback = Mock()
    data = {"a": 1}
    obs = Observable(data, callback)

    # Act
    obs["b"] = 2

    # Assert
    callback.assert_called_once()
    assert obs == {"a": 1, "b": 2}


def test_observable_tracks_set_mutations() -> None:
    """Test that Observable tracks mutations on set objects."""
    # Arrange
    callback = Mock()
    data = {1, 2}
    obs = Observable(data, callback)

    # Act
    obs.add(3)

    # Assert
    callback.assert_called_once()
    assert obs == {1, 2, 3}


def test_observable_delegates_non_mutating_methods() -> None:
    """Test that Observable delegates non-mutating methods without triggering callback."""
    # Arrange
    callback = Mock()
    data = [1, 2, 3]
    obs = Observable(data, callback)

    # Act
    result = obs.count(2)

    # Assert
    callback.assert_not_called()
    assert result == 1


def test_observable_equality() -> None:
    """Test that Observable equality works correctly."""
    # Arrange
    callback = Mock()
    obs1 = Observable([1, 2, 3], callback)
    obs2 = Observable([1, 2, 3], callback)

    # Assert
    assert obs1 == [1, 2, 3]
    assert obs1 == obs2


def test_field_descriptor_with_factory() -> None:
    """Test that Field descriptor works with factory functions."""

    # Arrange
    class TestState(State):
        """Test state class."""

        items = Field[list[int]](list)

    # Act
    state = TestState()

    # Assert
    assert state.items == []
    assert isinstance(state.items, Observable)


def test_field_descriptor_with_value() -> None:
    """Test that Field descriptor works with direct values."""

    # Arrange
    class TestState(State):
        """Test state class."""

        count = Field[int](0)

    # Act
    state = TestState()

    # Assert
    assert state.count == 0


def test_field_tracks_changes_on_assignment() -> None:
    """Test that Field tracks changes when value is assigned."""

    # Arrange
    class TestState(State):
        """Test state class."""

        value = Field[int](0)

    state = TestState()
    state.clear_changes()

    # Act
    state.value = 5

    # Assert
    assert "value" in state.changes


def test_field_tracks_mutations_on_mutable_types() -> None:
    """Test that Field tracks mutations on mutable types."""

    # Arrange
    class TestState(State):
        """Test state class."""

        items = Field[list[int]](list)

    state = TestState()
    state.clear_changes()

    # Act
    state.items.append(1)

    # Assert
    assert "items" in state.changes


def test_state_tracks_non_field_attribute_changes() -> None:
    """Test that State tracks changes to non-Field attributes."""

    # Arrange
    class TestState(State):
        """Test state class."""

        def __init__(self) -> None:
            super().__init__()
            self.value = 0

    state = TestState()
    state.clear_changes()

    # Act
    state.value = 5

    # Assert
    assert "value" in state.changes


def test_state_watcher_notification() -> None:
    """Test that State notifies watchers when attributes change."""

    # Arrange
    class TestState(State):
        """Test state class."""

        value = Field[int](0)

    state = TestState()
    callback = Mock()
    state.register_watcher("value", callback)

    # Act
    state.value = 5

    # Assert
    callback.assert_called_once()


def test_state_clear_changes() -> None:
    """Test that clear_changes clears the changes set."""

    # Arrange
    class TestState(State):
        """Test state class."""

        value = Field[int](0)

    state = TestState()
    state.value = 5

    # Act
    state.clear_changes()

    # Assert
    assert len(state.changes) == 0
