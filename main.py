import pygame
import threading
import time
import poker_logic
from models import Player, GameState, ActionType
from controllers import SmartBotController
from gui_renderer import PokerGUI, SCREEN_WIDTH, SCREEN_HEIGHT

class GameContext:
    def __init__(self):
        self.state: GameState = None
        self.current_actor_idx = -1
        self.waiting_for_human = False
        self.raising_mode = False
        self.legal_actions = []
        self.human_decision = None
        self.game_over = False
        self.last_message = "Czekam na start..."
        self.show_all_cards = False
        self.waiting_for_next_round = False
        self.showdown_hands = {}
        self.community_snapshot = []
        self.logs = []

    def add_log(self, msg):
        self.logs.append(msg)
        #log do 50 wpisów
        if len(self.logs) > 50:
            self.logs.pop(0)

context = GameContext()
def on_game_action(state, msg):
    #ta funkcja jest wołana przez poker_logic po kazdym ruchu bota/gracza
    context.state = state
    context.add_log(msg)

class HumanGuiController:
    def decide_action(self, player, state, legal_actions):
        context.waiting_for_human = True
        context.legal_actions = legal_actions
        context.last_message = "Twój ruch!"
        context.human_decision = None
        context.raising_mode = False

        while context.human_decision is None:
            time.sleep(0.1)
            if context.game_over:
                return ActionType.FOLD, 0

        action, amount = context.human_decision

        context.waiting_for_human = False
        context.raising_mode = False
        return action, amount

# logika gry
def game_logic_thread(num_players):
    human = Player(name="Ty", chips=1000, hand=(), controller=HumanGuiController())
    bot_names = ["Bot Andrzej", "Bot Bartek", "Bot Celina", "Bot Dominika","Bot Edward"]

    players = [human]
    for i in range(num_players - 1):
        players.append(Player(name=bot_names[i], chips=1000, hand=(), controller=SmartBotController()))

    dealer_idx = 0
    hand_count = 1

    deck = poker_logic.create_deck()
    context.state = GameState(deck=deck, players=players, community_cards=[])

    while len([p for p in players if p.chips > 0]) > 1 and not context.game_over:
        active_players = [p for p in players if p.chips > 0]
        dealer_idx = dealer_idx % len(active_players)

        context.last_message = f"Rozdanie #{hand_count}"
        context.add_log(f"ROZDANIE #{hand_count} ---")
        context.show_all_cards = False
        context.showdown_hands = {}
        context.community_snapshot = []  # Reset
        time.sleep(1.5)

        deck = poker_logic.create_deck()
        deck = poker_logic.shuffle_deck(deck)
        active_players, deck = poker_logic.deal_hands(deck, active_players)

        state = GameState(deck=deck, players=active_players, community_cards=[],
                          dealer_index=dealer_idx)
        context.state = state

        context.add_log("Pre-Flop")
        state, events = poker_logic.post_blinds(state)
        for e in events: context.add_log(e.message)
        context.state = state
        time.sleep(0.5)

        state, events = poker_logic.run_betting_round(state, on_action_callback=on_game_action)
        context.state = state

        if len([p for p in state.players if not p.folded]) > 1:

            state = poker_logic.reset_bets(state)
            state, events = poker_logic.deal_table(state, 3)
            context.add_log(f"FLOP: {state.community_cards}")
            context.state = state
            time.sleep(1)
            state, events = poker_logic.run_betting_round(state, on_action_callback=on_game_action)
            context.state = state

            if len([p for p in state.players if not p.folded]) > 1:

                state = poker_logic.reset_bets(state)
                state, events = poker_logic.deal_table(state, 1)
                context.add_log("TURN")
                context.state = state
                time.sleep(1)
                state, events = poker_logic.run_betting_round(state, on_action_callback=on_game_action)
                context.state = state

                if len([p for p in state.players if not p.folded]) > 1:

                    state = poker_logic.reset_bets(state)
                    state, events = poker_logic.deal_table(state, 1)
                    context.add_log("RIVER")
                    context.state = state
                    time.sleep(1)
                    state, events = poker_logic.run_betting_round(state, on_action_callback=on_game_action)
                    context.state = state

        # snapshot kart graczy do podsumowania
        for i, p in enumerate(state.players):
            context.showdown_hands[i] = p.hand

        # snapshot kart stolu do podsumowania
        context.community_snapshot = list(state.community_cards)

        context.show_all_cards = True

        # rozliczenie
        state, events = poker_logic.resolve_payouts(state)
        context.state = state

        winners_msg = ""
        for e in events:
            context.add_log(e.message)
            if "Pula" in e.message:
                winners_msg = e.message.replace("Pula", "Wygrał:")

        context.last_message = winners_msg if winners_msg else "Koniec rozdania"

        context.waiting_for_next_round = True
        while context.waiting_for_next_round:
            time.sleep(0.1)
            if context.game_over: break

        context.show_all_cards = False
        context.showdown_hands = {}
        context.community_snapshot = []

        players = state.players
        dealer_idx += 1
        hand_count += 1

# Główna pętla
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Poker Simulator")
    clock = pygame.time.Clock()
    gui = PokerGUI(screen)

    print("Uruchamianie GUI...")
    num_players = 6

    logic_thread = threading.Thread(target=game_logic_thread, args=(num_players,))
    logic_thread.daemon = True
    logic_thread.start()

    running = True
    mouse_down = False

    while running:
        clock.tick(30)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                context.game_over = True

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_down = True

                    if context.waiting_for_next_round:
                        if gui.next_round_btn and gui.next_round_btn.collidepoint(mouse_pos):
                            context.waiting_for_next_round = False

                    elif context.waiting_for_human:
                        if not context.raising_mode:
                            for action, rect in gui.buttons.items():
                                if rect.collidepoint(mouse_pos):
                                    if action == ActionType.RAISE:
                                        context.raising_mode = True
                                        gui.raise_slider = None
                                    else:
                                        context.human_decision = (action, 0)
                        else:
                            if gui.confirm_raise_btn and gui.confirm_raise_btn.collidepoint(mouse_pos):
                                val = gui.raise_slider.val
                                context.human_decision = (ActionType.RAISE, val)

            elif event.type == pygame.MOUSEBUTTONUP:
                mouse_down = False

        if context.raising_mode and gui.raise_slider:
            gui.raise_slider.update(mouse_pos, mouse_down)

        if context.state:
            current_actor = 0 if context.waiting_for_human else -1

            gui.render(
                state=context.state,
                human_msg=context.last_message,
                legal_actions=context.legal_actions,
                waiting_for_human=context.waiting_for_human,
                current_actor_idx=current_actor,
                show_all_cards=context.show_all_cards,
                raising_mode=context.raising_mode,
                wait_for_next=context.waiting_for_next_round,
                showdown_hands=context.showdown_hands,
                game_logs=context.logs,
                override_community=context.community_snapshot if context.waiting_for_next_round else None
            )
        else:
            screen.fill((35, 40, 50))
            gui.draw_text("Ładowanie gry...", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()