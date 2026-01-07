import random
from typing import List, Tuple
from models import Player, GameState, ActionType, Card
import poker_logic
import poker_evaluator

class HumanConsoleController:
    def decide_action(self, player: Player, state: GameState, legal_actions: List[ActionType]) -> Tuple[
        ActionType, int]:
        print(f"\n--- Twoja kolej: {player.name} ---")
        print(f"Karty: {player.hand}")
        print(f"Stół: {state.community_cards}")
        to_call = state.current_bet - player.current_bet
        print(f"Pula: {state.pot}, Do sprawdzenia: {to_call}")
        print(f"Dostępne akcje: {[a.name for a in legal_actions]}")

        while True:
            choice = input("Wybierz akcję (F/C/R/A): ").upper().strip()
            try:
                if choice == 'F': choice = 'FOLD'
                if choice == 'C': choice = 'CALL' if to_call > 0 else 'CHECK'
                if choice == 'R': choice = 'RAISE'
                if choice == 'A': choice = 'ALL_IN'

                if choice == 'CHECK' and ActionType.CHECK not in legal_actions and ActionType.CALL in legal_actions:
                    print("Nie możesz czekać (Check), musisz sprawdzić (Call) lub spasować.")
                    continue

                if choice not in ActionType.__members__:
                    print("Nieznana akcja.")
                    continue

                action = ActionType[choice]
                if action not in legal_actions:
                    print("Niedozwolona akcja!")
                    continue

                amount = 0
                if action == ActionType.RAISE:
                    min_r = state.current_bet + state.min_raise
                    max_r = player.chips + player.current_bet
                    if min_r > max_r:
                        print("Za mało żetonów na min. przebicie, może All-in?")
                        continue

                    amount_str = input(f"Podaj kwotę (min {min_r}, max {max_r}): ")
                    if not amount_str.isdigit(): continue
                    amount = int(amount_str)
                    if amount < min_r or amount > max_r:
                        print("Kwota poza zakresem.")
                        continue

                return action, amount
            except (KeyError, ValueError):
                print("Błąd, spróbuj ponownie.")

class SmartBotController:
    def __init__(self, aggression_factor: float = 0.5):
        # parametr agresji - jak często podbija i  blefuje
        self.aggression = aggression_factor


    def decide_action(self, player: Player, state: GameState, legal_actions: List[ActionType]) -> Tuple[
        ActionType, int]:

        is_preflop = (len(state.community_cards) == 0)
        to_call = state.current_bet - player.current_bet
        pot_odds = to_call / (state.pot + to_call) if (state.pot + to_call) > 0 else 0

        stack_percentage_committed = to_call / player.chips if player.chips > 0 else 1.0
        can_raise = (stack_percentage_committed < 0.30)

        # bot gra przed flopem
        if is_preflop:
            return self.play_preflop(player, state, legal_actions, can_raise)

        # bot po flopie symuluje wyniki metoda monte carlo
        equity = self.calculate_equity(player.hand, state.community_cards, iterations=100)

        # mały czynnik losowy
        final_strength = equity + random.uniform(-0.01, 0.01)

        # bot gra bardzo agresywnie jak ma bardzo mocne karty
        if final_strength > 0.90:
            if ActionType.RAISE in legal_actions and can_raise:
                bet_amount = int(state.pot * random.uniform(0.4, 0.6))
                return self.make_raise(player, state, bet_amount)
            elif ActionType.CALL in legal_actions:
                return ActionType.CALL, 0

        aggression_threshold = 0.80 - (self.aggression * 0.05)

        # rzadki blef
        should_bluff = (state.current_bet == 0 and random.random() < (self.aggression * 0.05))

        if final_strength > aggression_threshold or should_bluff:
            if ActionType.RAISE in legal_actions and can_raise:
                # mały bet: 30-45% puli
                bet_amount = int(state.pot * random.uniform(0.3, 0.45))
                return self.make_raise(player, state, bet_amount)

        # czy opłaca mu się sprawdzać
        required_equity = pot_odds

        if to_call > (player.chips * 0.2):
            required_equity += 0.15

        if final_strength > required_equity:
            if ActionType.CALL in legal_actions:
                return ActionType.CALL, 0
            if ActionType.CHECK in legal_actions:
                return ActionType.CHECK, 0


        if ActionType.CHECK in legal_actions:
            return ActionType.CHECK, 0

        return ActionType.FOLD, 0

    # metoda monte carlo - bot okresla czy oplaca mu sie wchodzić
    def calculate_equity(self, player_hand, community_cards, iterations=50) -> float:
        deck = poker_logic.create_deck()
        known_cards = set(player_hand + tuple(community_cards))
        unknown_deck = [c for c in deck if c not in known_cards]

        wins = 0
        ties = 0
        # losuje i* razy i oblicza punkty
        for r in range(iterations):
            sim_deck = poker_logic.shuffle_deck(list(unknown_deck))
            cards_needed = 5 - len(community_cards)
            sim_community = community_cards + sim_deck[:cards_needed]
            deck_ptr = cards_needed
            opp_hand = tuple(sim_deck[deck_ptr: deck_ptr + 2])

            my_score = poker_evaluator.evaluate(list(player_hand) + sim_community)
            opp_score = poker_evaluator.evaluate(list(opp_hand) + sim_community)

            if my_score > opp_score:
                wins += 1
            elif my_score == opp_score:
                ties += 1

        return (wins + (ties * 0.5)) / iterations


    # jak nie ma kart na stole to nie liczy prawdopodbientswa tylko patrzy na swoją rękę czy ma coś dobrego.
    def play_preflop(self, player: Player, state: GameState, legal: List[ActionType], can_raise: bool) -> Tuple[
        ActionType, int]:
        #oceniam co na rece, czy oplaca sie wchodzic
        ranks = sorted([c.rank for c in player.hand], reverse=True)
        high, low = ranks[0], ranks[1]
        is_pair = (high == low)
        suited = (player.hand[0].suit == player.hand[1].suit)
        gap = high - low

        score = 0
        # jak ma parę to silniejsza ręka
        if is_pair:
            score += 50 + (high * 2)
        else:
            score += high + (low * 0.5)
        if suited: score += 10
        if gap == 1: score += 8
        if gap == 2: score += 4

        # jeśli ręka jest bardzo mocna to szansa ze podbijam przed flopem
        if score > 50:
            if can_raise and ActionType.RAISE in legal and random.random() < 0.60:

                raise_amt = int(state.current_bet + (state.min_raise * random.uniform(1, 2)))
                return self.make_raise(player, state, raise_amt)

        # jak nie chce podbic i moge czekac to czekam
        if ActionType.CHECK in legal:
            return ActionType.CHECK, 0

        was_raised = (state.current_bet > 20)

        if not was_raised:
            return ActionType.CALL, 0

        # jeśli mocna ale nie podbijam to wchodze
        if score > 50:
            return ActionType.CALL, 0

        if score > 30:
            return ActionType.CALL, 0

        to_call = state.current_bet - player.current_bet
        is_cheap = (to_call <= 40)
        # jak tanio to wchodze zeby zobaczyc jakie karty
        if is_cheap:
            if random.random() < 0.9:
                return ActionType.CALL, 0

        # rzadki blef
        if random.random() < (self.aggression * 0.05):
            return ActionType.CALL, 0

        return ActionType.FOLD, 0

    def make_raise(self, player, state, amount):
        min_r = state.current_bet + state.min_raise
        max_r = player.chips + player.current_bet
        final_amt = max(min_r, min(amount, max_r))

        if final_amt > (player.chips * 0.9) + player.current_bet:
            return ActionType.ALL_IN, 0

        return ActionType.RAISE, final_amt