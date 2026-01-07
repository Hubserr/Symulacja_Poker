from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
from typing import List, Tuple, Any, Optional

class Suit(Enum):
    HEARTS = auto()
    DIAMONDS = auto()
    SPADES = auto()
    CLUBS = auto()

class HandValue(IntEnum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9

class ActionType(Enum):
    FOLD = auto()
    CHECK = auto()
    CALL = auto()
    RAISE = auto()
    ALL_IN = auto()

@dataclass(frozen=True)
class GameEvent:
    message: str

@dataclass(frozen=True)
class Card:
    rank: int
    suit: Suit

    def __repr__(self):
        r_str = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}.get(self.rank, str(self.rank))
        s_str = {Suit.HEARTS: '♥', Suit.DIAMONDS: '♦', Suit.SPADES: '♠', Suit.CLUBS: '♣'}.get(self.suit, self.suit.name)
        return f"{r_str}{s_str}"

@dataclass(frozen=True)
class Player:
    name: str
    chips: int
    hand: Tuple[Card, ...] | Tuple[()]
    controller: Any = field(default=None, compare=False, repr=False)

    folded: bool = False
    is_all_in: bool = False
    current_bet: int = 0
    total_bet_in_hand: int = 0

@dataclass(frozen=True)
class GameState:
    deck: List[Card]
    players: List[Player]
    community_cards: List[Card]
    pot: int = 0
    current_bet: int = 0
    dealer_index: int = 0
    min_raise: int = 20  # minimalne przebicie