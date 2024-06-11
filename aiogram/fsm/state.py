import inspect
from typing import Any, Iterator, Optional, Tuple, Type, no_type_check

from aiogram.types import TelegramObject


class State:
    """
    State object
    """

    def __init__(self, state: Optional[str] = None, group_name: Optional[str] = None) -> None:
        self._state = state
        self._group_name = group_name
        self._group: Optional[Type[StatesGroup]] = None

    @property
    def group(self) -> "Type[StatesGroup]":
        if not self._group:
            raise RuntimeError("This state is not in any group.")
        return self._group

    @property
    def state(self) -> Optional[str]:
        if self._state is None or self._state == "*":
            return self._state

        if self._group_name is None and self._group:
            group = self._group.__full_group_name__
        elif self._group_name:
            group = self._group_name
        else:
            group = "@"

        return f"{group}:{self._state}"

    def set_parent(self, group: "Type[StatesGroup]") -> None:
        if not issubclass(group, StatesGroup):
            raise ValueError("Group must be subclass of StatesGroup")
        self._group = group

    def __set_name__(self, owner: "Type[StatesGroup]", name: str) -> None:
        if self._state is None:
            self._state = name
        self.set_parent(owner)

    def __str__(self) -> str:
        return f"<State '{self.state or ''}'>"

    __repr__ = __str__

    def __call__(self, event: TelegramObject, raw_state: Optional[str] = None) -> bool:
        if self.state == "*":
            return True
        return raw_state == self.state

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.state == other.state
        if isinstance(other, str):
            return self.state == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.state)


class StatesGroupMeta(type):
    __parent__: "Optional[Type[StatesGroup]]"
    __childs__: "Tuple[Type[StatesGroup], ...]"
    __states__: Tuple[State, ...]
    __state_names__: Tuple[str, ...]
    __all_childs__: Tuple[Type["StatesGroup"], ...]
    __all_states__: Tuple[State, ...]
    __all_states_names__: Tuple[str, ...]

    @no_type_check
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace)

        states = []
        childs = []

        for name, arg in namespace.items():
            if isinstance(arg, State):
                states.append(arg)
            elif inspect.isclass(arg) and issubclass(arg, StatesGroup):
                child = cls._prepare_child(arg)
                childs.append(child)

        cls.__parent__ = None
        cls.__childs__ = tuple(childs)
        cls.__states__ = tuple(states)
        cls.__state_names__ = tuple(state.state for state in states)

        cls.__all_childs__ = cls._get_all_childs()
        cls.__all_states__ = cls._get_all_states()

        # In order to ensure performance, we calculate this parameter
        # in advance already during the production of the class.
        # Depending on the relationship, it should be recalculated
        cls.__all_states_names__ = cls._get_all_states_names()

        return cls

    @property
    def __full_group_name__(cls) -> str:
        if cls.__parent__:
            return ".".join((cls.__parent__.__full_group_name__, cls.__name__))
        return cls.__name__

    def __prepare_child(cls, child: Type["StatesGroup"]) -> Type["StatesGroup"]:
        """Prepare child.

        While adding `cls` for its children, we also need to recalculate
        the parameter `__all_states_names__` for each child
        `StatesGroup`. Since the child class appears before the
        parent, at the time of adding the parent, the child's
        `__all_states_names__` is already recorded without taking into
        account the name of current parent.
        """
        child.__parent__ = cls  # type: ignore[assignment]
        child.__all_states_names__ = child._get_all_states_names()
        return child

    def _get_all_childs(cls) -> Tuple[Type["StatesGroup"], ...]:
        result = cls.__childs__
        for child in cls.__childs__:
            result += child.__childs__
        return result

    def _get_all_states(cls) -> Tuple[State, ...]:
        result = cls.__states__
        for group in cls.__childs__:
            result += group.__all_states__
        return result

    def _get_all_states_names(cls) -> Tuple[str, ...]:
        return tuple(state.state for state in cls.__all_states__ if state.state)

    def __contains__(cls, item: Any) -> bool:
        if isinstance(item, str):
            return item in cls.__all_states_names__
        if isinstance(item, State):
            return item in cls.__all_states__
        if isinstance(item, StatesGroupMeta):
            return item in cls.__all_childs__
        return False

    def __str__(self) -> str:
        return f"<StatesGroup '{self.__full_group_name__}'>"

    def __iter__(self) -> Iterator[State]:
        return iter(self.__all_states__)


class StatesGroup(metaclass=StatesGroupMeta):
    @classmethod
    def get_root(cls) -> Type["StatesGroup"]:
        if cls.__parent__ is None:
            return cls
        return cls.__parent__.get_root()

    def __call__(self, event: TelegramObject, raw_state: Optional[str] = None) -> bool:
        return raw_state in type(self).__all_states_names__

    def __str__(self) -> str:
        return f"StatesGroup {type(self).__full_group_name__}"


default_state = State()
any_state = State(state="*")
