from typing import List, Tuple, Callable, Optional
from random import sample
from dataclasses import replace
from models import Card, Suit, Player, GameState, ActionType, GameEvent
import poker_evaluator
import time

# tasowanie rozkładanie
def create_deck() -> List[Card]:
    return [Card(r, s) for s in Suit for r in range(2, 15)]

def shuffle_deck(deck: List[Card]) -> List[Card]:
    return sample(deck, len(deck))

def deal_hands(deck: List[Card], players: List[Player]) -> Tuple[List[Player], List[Card]]:
    n = 2
    new_players = [
        replace(p,
                hand=tuple(deck[i * n: (i + 1) * n]),
                folded=False,
                is_all_in=False,
                current_bet=0,
                total_bet_in_hand=0)
        for i, p in enumerate(players)
    ]
    remaining_deck = deck[len(players) * n:]
    return new_players, remaining_deck

def deal_table(state: GameState, n: int) -> Tuple[GameState, List[GameEvent]]:
    if len(state.deck) < n + 1:
        return state, [GameEvent("Błąd: Za mało kart w talii!")]

    drawn = state.deck[1: n + 1]  # Burn 1
    new_deck = state.deck[n + 1:]
    new_comm = state.community_cards + drawn

    new_state = replace(state, deck=new_deck, community_cards=new_comm)
    return new_state, [GameEvent(f"Na stół spadają: {drawn}")]

# Podbijanie, dzielenie kasy

def post_blinds(state: GameState, sb_amount: int = 10, bb_amount: int = 20) -> Tuple[GameState, List[GameEvent]]:
    n = len(state.players)
    events = []
    if n < 2: return state, events

    sb_idx = (state.dealer_index + 1) % n
    bb_idx = (state.dealer_index + 2) % n

    if n == 2: # jakby było tylko dwóch graczy to dealer jest też sb
        sb_idx = state.dealer_index
        bb_idx = (state.dealer_index + 1) % n
    #funkcja pomocnicza do wplacania sb i bb
    def pay_blind(p: Player, amount: int) -> Player:
        actual = min(p.chips, amount)
        return replace(p,
                       chips=p.chips - actual,
                       current_bet=actual,
                       total_bet_in_hand=p.total_bet_in_hand + actual,
                       is_all_in=(p.chips - actual == 0))

    new_players = list(state.players)
    #wplaca small blind
    sb_p = pay_blind(new_players[sb_idx], sb_amount)
    new_players[sb_idx] = sb_p
    events.append(GameEvent(f"{sb_p.name} wpłaca SB {sb_p.current_bet}"))
    #wplaca big blind
    bb_p = pay_blind(new_players[bb_idx], bb_amount)
    new_players[bb_idx] = bb_p
    events.append(GameEvent(f"{bb_p.name} wpłaca BB {bb_p.current_bet}"))

    added_chips = sb_p.current_bet + bb_p.current_bet
    return replace(state, players=new_players, pot=state.pot + added_chips, current_bet=bb_amount), events

# co może zrobić w danej chwili?
def get_legal_actions(player: Player, state: GameState) -> List[ActionType]:
    actions = [ActionType.FOLD]
    amount_to_call = state.current_bet - player.current_bet

    if amount_to_call == 0:
        actions.append(ActionType.CHECK)
    else:
        actions.append(ActionType.CALL)

    if player.chips > amount_to_call:
        actions.append(ActionType.RAISE)

    if player.chips > 0:
        actions.append(ActionType.ALL_IN)

    return actions

def apply_action(state: GameState, player_idx: int, action: ActionType, raise_amount: int) -> Tuple[GameState, str]:
    player = state.players[player_idx]
    new_pot = state.pot
    new_current_bet = state.current_bet
    new_min_raise = state.min_raise

    p_chips = player.chips
    p_bet = player.current_bet
    p_total = player.total_bet_in_hand
    p_folded = player.folded
    p_all_in = player.is_all_in
    msg = ""

    if action == ActionType.FOLD:
        p_folded = True
        msg = f"{player.name}: Pas"

    elif action == ActionType.CHECK:
        msg = f"{player.name}: Czekam"

    elif action == ActionType.CALL:
        to_call = state.current_bet - player.current_bet
        actual = min(to_call, player.chips)
        p_chips -= actual
        p_bet += actual
        p_total += actual
        new_pot += actual
        if p_chips == 0: p_all_in = True
        msg = f"{player.name}: Sprawdzam ({actual})"

    elif action == ActionType.RAISE:
        contribution = raise_amount - player.current_bet
        p_chips -= contribution

        raise_diff = raise_amount - state.current_bet
        # zwiekszamy minimalny raise co najmniej 2x
        if raise_diff > 0:
            new_min_raise = raise_diff

        p_bet = raise_amount
        p_total += contribution
        new_pot += contribution
        new_current_bet = raise_amount
        msg = f"{player.name}: Podbijam do {raise_amount}"

    elif action == ActionType.ALL_IN:
        contribution = player.chips
        p_chips = 0
        p_bet += contribution
        p_total += contribution
        p_all_in = True
        new_pot += contribution

        if p_bet > new_current_bet:
            raise_diff = p_bet - new_current_bet
            if raise_diff >= state.min_raise:
                new_min_raise = raise_diff
            new_current_bet = p_bet

        msg = f"{player.name}: All-in ({contribution})"

    new_p = replace(player, chips=p_chips, current_bet=p_bet, total_bet_in_hand=p_total, folded=p_folded,
                    is_all_in=p_all_in)

    new_players = [
        new_p if i == player_idx else p
        for i, p in enumerate(state.players)
    ]


    state = replace(state, min_raise=new_min_raise)
    return replace(state, players=new_players, pot=new_pot, current_bet=new_current_bet), msg
#
def run_betting_round(state: GameState, on_action_callback: Optional[Callable[[GameState, str], None]] = None) -> Tuple[
    GameState, List[GameEvent]]:

    n = len(state.players)
    # ustalenie gracza rozpoczynajacego
    if not state.community_cards:
        start_idx = (state.dealer_index + 3) % n
        if len(state.players) == 2:
            start_idx = state.dealer_index
    else:
        start_idx = (state.dealer_index + 1) % n

    # rekurencja, sprawdza czy nie koneic
    def _bet_step(current_state: GameState, actor_ptr: int, players_acted: int, accumulated_events: List[GameEvent]) -> \
    Tuple[GameState, List[GameEvent]]:

        not_folded = [p for p in current_state.players if not p.folded]
        # jeżeli został tylko jeden to koniec i wygrywa rozdanei
        if len(not_folded) == 1:
            return current_state, accumulated_events

        active_with_chips = [p for p in current_state.players if not p.folded and not p.is_all_in]
        # sprawdzamy czy wyrównali
        all_matched = all(p.current_bet == current_state.current_bet for p in not_folded if not p.is_all_in)
        # jesli wyrownali i wykonal kazy ruch to koniec
        if all_matched and players_acted >= len(active_with_chips):
            return current_state, accumulated_events
        # jak już nie ma komu licytować - np wszyscy all-in
        if len(active_with_chips) < 2:
            highest_bet = current_state.current_bet
            rich_player_matched = True
            if active_with_chips:
                rich_player_matched = (active_with_chips[0].current_bet >= highest_bet)

            if rich_player_matched:
                return current_state, accumulated_events
        # kto teraz wykonuje ruch?
        current_actor_idx = actor_ptr % n
        player = current_state.players[current_actor_idx]
        # jeżeli zfoldowal lub zagral all in to pomijam
        if player.folded or player.is_all_in:
            return _bet_step(current_state, actor_ptr + 1, players_acted, accumulated_events)
        # pobieramy deccyzje
        legal = get_legal_actions(player, current_state)
        if player.controller is None:
            action, amount = ActionType.CHECK, 0
        else:
            action, amount = player.controller.decide_action(player, current_state, legal)

        prev_bet = current_state.current_bet
        new_state, msg = apply_action(current_state, current_actor_idx, action, amount)
        # odświeżenie grafiki
        if on_action_callback:
            on_action_callback(new_state, msg)
            time.sleep(0.8)
        # jak ktoś przebije to gramy dalej
        did_raise = new_state.current_bet > prev_bet
        next_players_acted = 1 if did_raise else players_acted + 1

        return _bet_step(
            current_state=new_state,
            actor_ptr=actor_ptr + 1,
            players_acted=next_players_acted,
            accumulated_events=accumulated_events + [GameEvent(msg)]
        )

    return _bet_step(state, start_idx, 0, [])


def reset_bets(state: GameState) -> GameState:
    new_players = [replace(p, current_bet=0) for p in state.players]
    return replace(state, players=new_players, current_bet=0, min_raise=20)

# funkcja do podzialu kasy
def resolve_payouts(state: GameState) -> Tuple[GameState, List[GameEvent]]:
    events = [GameEvent("Rozliczenie")]
    players = state.players
    # lista kwot które wpłacili gracze zeby policzyć dobrze sidepoty
    all_bets = sorted(list(set(p.total_bet_in_hand for p in players if p.total_bet_in_hand > 0)))
    temp_chips = {i: p.chips for i, p in enumerate(players)}
    last_bet_level = 0

    for bet_level in all_bets:
        chunk_size = bet_level - last_bet_level
        pot_chunk = 0
        contributors_indices = []

        for i, p in enumerate(players):
            if p.total_bet_in_hand >= bet_level:
                pot_chunk += chunk_size
                if not p.folded: contributors_indices.append(i)
            elif p.total_bet_in_hand > last_bet_level:
                pot_chunk += (p.total_bet_in_hand - last_bet_level)

        if pot_chunk == 0:
            last_bet_level = bet_level
            continue

        candidates = [players[i] for i in contributors_indices]
        if not candidates:
            last_bet_level = bet_level
            continue
        # wyłaniamy zwycięzce
        cand_scores = []
        for p in candidates:
            score = poker_evaluator.best_hand(p, state.community_cards)
            cand_scores.append((p, score))

        best_score_entry = max(cand_scores, key=lambda x: x[1])
        best_score_val = best_score_entry[1]
        winners = [p for p, s in cand_scores if s == best_score_val]

        win_amount = pot_chunk // len(winners)
        extra = pot_chunk % len(winners)

        hand_name = best_score_val[0].name
        events.append(
            GameEvent(f"Pula {pot_chunk} dla: {[w.name for w in winners]} ({hand_name})"))

        for w in winners:
            w_idx = next(i for i, p in enumerate(players) if p.name == w.name)
            bonus = 1 if extra > 0 else 0
            if bonus: extra -= 1
            temp_chips[w_idx] += (win_amount + bonus)

        last_bet_level = bet_level

    new_players_list = []
    for i, p in enumerate(players):
        new_p = replace(p,
                        chips=temp_chips[i],
                        hand=(),
                        current_bet=0,
                        total_bet_in_hand=0,
                        folded=False,
                        is_all_in=False)
        new_players_list.append(new_p)

    return replace(state, players=new_players_list, pot=0, current_bet=0, community_cards=[]), events