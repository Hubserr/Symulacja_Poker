from typing import List, Tuple
from collections import Counter
from models import Card, HandValue, Player
# sortowanie po sile karty - 2,3,4 az do asa
def get_ranks(cards: List[Card]) -> List[int]:
    return sorted([c.rank for c in cards], reverse=True)
# sprawdzamy czy wszystkie karty tego samego koloru
def check_flush(cards: List[Card]) -> Tuple[bool, List[int], List[Card]]:
    counts = Counter(c.suit for c in cards)
    for suit, count in counts.items():
        if count >= 5:
            flush_cards = [c for c in cards if c.suit == suit]
            flush_ranks = sorted([c.rank for c in flush_cards], reverse=True)
            return True, flush_ranks, flush_cards
    return False, [], []

#sprawdzam czy strit - karty kolejno po sobie np 5,6,7,8,9
def check_straight(ranks: List[int]) -> Tuple[bool, int]:
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    if len(unique_ranks) < 5:
        return False, 0

    # strit standardowy
    for i in range(len(unique_ranks) - 4):
        window = unique_ranks[i:i + 5]
        if window[0] - window[4] == 4:
            return True, window[0]

    # strit z asem jako "1" (A, 5, 4, 3, 2) - szczegółowy przypadek
    if set([14, 5, 4, 3, 2]).issubset(set(unique_ranks)):
        return True, 5

    return False, 0

#przeliczam na siłę ręki
def evaluate(cards: List[Card]) -> Tuple[HandValue, List[int]]:
    if not cards:
        return (HandValue.HIGH_CARD, [])

    # poker
    is_fl, fl_ranks, fl_cards = check_flush(cards)
    if is_fl:
        is_sf, sf_high = check_straight(fl_ranks)
        if is_sf:
            return (HandValue.STRAIGHT_FLUSH, [sf_high])

    # cztery takie same
    ranks = get_ranks(cards)
    counts = Counter(ranks)
    sorted_counts = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    if sorted_counts[0][1] == 4:
        quad_rank = sorted_counts[0][0]
        kickers = [r for r in ranks if r != quad_rank]
        return (HandValue.FOUR_OF_A_KIND, [quad_rank, kickers[0]])

    #  full - para i trójka
    if sorted_counts[0][1] == 3 and len(sorted_counts) > 1 and sorted_counts[1][1] >= 2:
        return (HandValue.FULL_HOUSE, [sorted_counts[0][0], sorted_counts[1][0]])

    #  kolor
    if is_fl:
        return (HandValue.FLUSH, fl_ranks[:5])

    #  strit
    is_str, str_high = check_straight(ranks)
    if is_str:
        return (HandValue.STRAIGHT, [str_high])

    # trzy takie same
    if sorted_counts[0][1] == 3:
        trip_rank = sorted_counts[0][0]
        kickers = [r for r in ranks if r != trip_rank]
        return (HandValue.THREE_OF_A_KIND, [trip_rank] + kickers[:2])

    # dwie pary
    if sorted_counts[0][1] == 2 and len(sorted_counts) > 1 and sorted_counts[1][1] == 2:
        pair1 = sorted_counts[0][0]
        pair2 = sorted_counts[1][0]
        kickers = [r for r in ranks if r != pair1 and r != pair2]
        return (HandValue.TWO_PAIR, [pair1, pair2, kickers[0]])
   # para
    if sorted_counts[0][1] == 2:
        pair_rank = sorted_counts[0][0]
        kickers = [r for r in ranks if r != pair_rank]
        return (HandValue.PAIR, [pair_rank] + kickers[:3])

    return (HandValue.HIGH_CARD, ranks[:5])

def best_hand(player: Player, community_cards: List[Card]) -> Tuple[HandValue, List[int]]:
    all_cards = list(player.hand) + community_cards
    return evaluate(all_cards)