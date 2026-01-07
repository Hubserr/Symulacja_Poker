import pygame
import math
from models import Suit, ActionType

# kolory i wymiary
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720 # rozdzielczosci ekranu
LOG_WIDTH = 250

BG_COLOR = (35, 40, 50)
TABLE_FELT_COLOR = (34, 139, 34)
TABLE_RIM_COLOR = (100, 70, 30)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 20, 60)
GOLD = (255, 215, 0)
GRAY = (140, 140, 150)

BUTTON_COLOR = (40, 100, 200)
BUTTON_HOVER = (60, 130, 230)
SLIDER_BG = (30, 30, 40)
SLIDER_FILL = (0, 200, 100)

CARD_W, CARD_H = 60, 90
FONT_SIZE = 20
class Slider:
    def __init__(self, x, y, w, h, min_val, max_val):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.val = min_val
        self.dragging = False
        self.handle_rect = pygame.Rect(x, y - 5, 20, h + 10)

    def update(self, mouse_pos, mouse_down):
        if mouse_down:
            if self.handle_rect.collidepoint(mouse_pos) or self.rect.collidepoint(mouse_pos):
                self.dragging = True
        else:
            self.dragging = False

        if self.dragging:
            rel_x = mouse_pos[0] - self.rect.x
            rel_x = max(0, min(rel_x, self.rect.width))
            percent = rel_x / self.rect.width
            self.val = int(self.min_val + (self.max_val - self.min_val) * percent)
            handle_x = self.rect.x + rel_x - 10
            self.handle_rect.x = handle_x
        else:
            if self.max_val > self.min_val:
                percent = (self.val - self.min_val) / (self.max_val - self.min_val)
                self.handle_rect.x = self.rect.x + (self.rect.width * percent) - 10

    def draw(self, screen, font):
        pygame.draw.rect(screen, SLIDER_BG, self.rect, border_radius=5)
        fill_w = self.handle_rect.centerx - self.rect.x
        if fill_w < 0: fill_w = 0
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
        pygame.draw.rect(screen, SLIDER_FILL, fill_rect, border_radius=5)
        pygame.draw.rect(screen, WHITE, self.handle_rect, border_radius=5)
        label = font.render(f"Kwota: {self.val}", True, WHITE)
        screen.blit(label, (self.rect.centerx - label.get_width() // 2, self.rect.y - 30))
class PokerGUI:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", FONT_SIZE, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 16)
        self.big_font = pygame.font.SysFont("Arial", 30, bold=True)
        self.buttons = {}
        self.raise_slider = None
        self.confirm_raise_btn = None
        self.next_round_btn = None

    def draw_text(self, text, x, y, color=WHITE, center=True, font=None):
        f = font if font else self.font
        surf = f.render(str(text), True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surf, rect)

    def draw_card(self, card, x, y):
        rect = pygame.Rect(x, y, CARD_W, CARD_H)
        pygame.draw.rect(self.screen, WHITE, rect, border_radius=5)
        pygame.draw.rect(self.screen, BLACK, rect, 2, border_radius=5)

        color = RED if card.suit in [Suit.HEARTS, Suit.DIAMONDS] else BLACK
        rank_str = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}.get(card.rank, str(card.rank))
        suit_sym = {Suit.HEARTS: '♥', Suit.DIAMONDS: '♦', Suit.SPADES: '♠', Suit.CLUBS: '♣'}.get(card.suit, '?')

        self.draw_text(rank_str, x + 15, y + 20, color)
        self.draw_text(suit_sym, x + CARD_W - 15, y + CARD_H - 20, color)

    def draw_player(self, player, idx, total_players, is_active_actor, show_all_cards, override_hand=None):
        cx, cy = (SCREEN_WIDTH - LOG_WIDTH) // 2, SCREEN_HEIGHT // 2 - 40
        rx, ry = 420, 230

        angle = (2 * math.pi / total_players) * idx + math.pi / 2
        x = cx + int(rx * math.cos(angle))
        y = cy + int(ry * math.sin(angle))

        color = GOLD if is_active_actor else (80, 80, 100)
        if player.folded: color = (60, 60, 70)

        pygame.draw.circle(self.screen, (20, 20, 20), (x + 2, y + 2), 35)
        pygame.draw.circle(self.screen, color, (x, y), 35)
        pygame.draw.circle(self.screen, WHITE, (x, y), 35, 2)

        self.draw_text(player.name, x, y - 75, WHITE)
        self.draw_text(f"${player.chips}", x, y - 55, GOLD)

        status = ""
        if player.folded:
            status = "FOLD"
        elif player.is_all_in:
            status = "ALL-IN"
        if status:
            self.draw_text(status, x, y, RED)

        hand_to_draw = override_hand if override_hand is not None else player.hand

        if not player.folded and hand_to_draw:
            card_y = y - 10
            is_human = (player.name == "Ty")
            should_show_face = is_human or show_all_cards

            if is_human:
                offset = CARD_W + 5
            else:
                offset = 20 if not should_show_face else CARD_W + 5

            total_width = (len(hand_to_draw) - 1) * offset + CARD_W
            start_x = x - total_width // 2

            for i, c in enumerate(hand_to_draw):
                pos_x = start_x + (i * offset)

                if should_show_face:
                    self.draw_card(c, pos_x, card_y)
                else:
                    r = pygame.Rect(pos_x, card_y, CARD_W, CARD_H)
                    pygame.draw.rect(self.screen, (60, 60, 180), r, border_radius=5)
                    pygame.draw.rect(self.screen, WHITE, r, 2, border_radius=5)
                    pygame.draw.rect(self.screen, (80, 80, 200), (pos_x + 5, card_y + 5, CARD_W - 10, CARD_H - 10),
                                     border_radius=3)

        if player.current_bet > 0:
            self.draw_text(f"Bet: {player.current_bet}", x, y + 95, WHITE)

    def draw_table_info(self, state, pot, override_community=None):
        cx, cy = (SCREEN_WIDTH - LOG_WIDTH) // 2, SCREEN_HEIGHT // 2 - 40

        rim_rect = pygame.Rect(0, 0, 980, 530)
        rim_rect.center = (cx, cy)
        pygame.draw.ellipse(self.screen, TABLE_RIM_COLOR, rim_rect)
        pygame.draw.ellipse(self.screen, (50, 30, 10), rim_rect, 3)

        table_rect = pygame.Rect(0, 0, 930, 480)
        table_rect.center = (cx, cy)
        pygame.draw.ellipse(self.screen, TABLE_FELT_COLOR, table_rect)
        pygame.draw.ellipse(self.screen, (30, 110, 30), table_rect, 2)

        # Użyj kart ze stanu LUB z zapisu (snapshotu)
        cards = override_community if override_community is not None else state.community_cards

        start_x = cx - (5 * (CARD_W + 10)) // 2 + 30
        for i, c in enumerate(cards):
            self.draw_card(c, start_x + i * (CARD_W + 10), cy - CARD_H // 2)

        self.draw_text(f"PULA: ${pot}", cx, cy - 80, GOLD, font=self.big_font)
        self.draw_text(f"Min Bet: {state.current_bet}", cx, cy + 80, (200, 200, 200))

    def draw_action_log(self, logs):
        # tlo panelu
        panel_rect = pygame.Rect(SCREEN_WIDTH - LOG_WIDTH, 0, LOG_WIDTH, SCREEN_HEIGHT)
        s = pygame.Surface((LOG_WIDTH, SCREEN_HEIGHT))
        s.fill((25, 30, 40))
        self.screen.blit(s, (SCREEN_WIDTH - LOG_WIDTH, 0))
        pygame.draw.line(self.screen, (100, 100, 100), (SCREEN_WIDTH - LOG_WIDTH, 0),
                         (SCREEN_WIDTH - LOG_WIDTH, SCREEN_HEIGHT), 2)

        self.draw_text("LOG GRY", SCREEN_WIDTH - LOG_WIDTH // 2, 30, GOLD, font=self.font)

        max_items = 25
        visible_logs = logs[-max_items:]

        start_y = 70
        for i, line in enumerate(visible_logs):
            color = WHITE
            if "Ty" in line: color = GOLD
            if "All-in" in line: color = RED
            if "Wygrał" in line: color = (100, 255, 100)

            self.draw_text(line, SCREEN_WIDTH - LOG_WIDTH + 10, start_y + i * 25, color, center=False,
                           font=self.small_font)

    def draw_controls(self, legal_actions, waiting_for_human, raising_mode=False):
        self.buttons = {}
        if not waiting_for_human or raising_mode:
            return

        btn_w, btn_h = 130, 50

        center_x = (SCREEN_WIDTH - LOG_WIDTH) // 2
        start_x = center_x - (len(legal_actions) * (btn_w + 20)) // 2
        y = SCREEN_HEIGHT - 80

        for i, action in enumerate(legal_actions):
            x = start_x + i * (btn_w + 20)
            rect = pygame.Rect(x, y, btn_w, btn_h)

            mouse_pos = pygame.mouse.get_pos()
            col = BUTTON_HOVER if rect.collidepoint(mouse_pos) else BUTTON_COLOR

            pygame.draw.rect(self.screen, (20, 20, 40), (x + 3, y + 3, btn_w, btn_h), border_radius=10)
            pygame.draw.rect(self.screen, col, rect, border_radius=10)
            pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=10)

            name = action.name
            self.draw_text(name, x + btn_w // 2, y + btn_h // 2)
            self.buttons[action] = rect

    def draw_raise_ui(self, min_r, max_r):
        center_x = (SCREEN_WIDTH - LOG_WIDTH) // 2
        panel_rect = pygame.Rect(0, 0, 400, 160)
        panel_rect.center = (center_x, SCREEN_HEIGHT - 120)

        pygame.draw.rect(self.screen, (30, 30, 40), panel_rect, border_radius=15)
        pygame.draw.rect(self.screen, (100, 100, 120), panel_rect, 2, border_radius=15)

        if self.raise_slider is None:
            self.raise_slider = Slider(panel_rect.x + 30, panel_rect.y + 70, 340, 20, min_r, max_r)

        self.raise_slider.min_val = min_r
        self.raise_slider.max_val = max_r
        if self.raise_slider.val < min_r: self.raise_slider.val = min_r
        if self.raise_slider.val > max_r: self.raise_slider.val = max_r

        self.draw_text("Wybierz kwotę podbicia:", panel_rect.centerx, panel_rect.y + 30, GOLD)
        self.raise_slider.draw(self.screen, self.font)

        btn_rect = pygame.Rect(0, 0, 160, 40)
        btn_rect.midtop = (panel_rect.centerx, panel_rect.bottom - 50)

        mouse_pos = pygame.mouse.get_pos()
        col = BUTTON_HOVER if btn_rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(self.screen, col, btn_rect, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, btn_rect, 2, border_radius=8)
        self.draw_text("ZATWIERDŹ", btn_rect.centerx, btn_rect.centery)
        self.confirm_raise_btn = btn_rect

    def draw_next_round_btn(self):
        center_x = (SCREEN_WIDTH - LOG_WIDTH) // 2
        btn_rect = pygame.Rect(0, 0, 320, 60)
        btn_rect.center = (center_x, SCREEN_HEIGHT - 100)

        mouse_pos = pygame.mouse.get_pos()
        col = (0, 160, 0) if btn_rect.collidepoint(mouse_pos) else (0, 120, 0)

        pygame.draw.rect(self.screen, (20, 40, 20), (btn_rect.x + 4, btn_rect.y + 4, 320, 60), border_radius=12)
        pygame.draw.rect(self.screen, col, btn_rect, border_radius=12)
        pygame.draw.rect(self.screen, WHITE, btn_rect, 2, border_radius=12)
        self.draw_text("DALEJ (NOWE ROZDANIE)", btn_rect.centerx, btn_rect.centery, font=self.font)

        self.next_round_btn = btn_rect

    def render(self, state, human_msg, legal_actions, waiting_for_human, current_actor_idx, show_all_cards=False,
               raising_mode=False, wait_for_next=False, showdown_hands=None, game_logs=[], override_community=None):
        self.screen.fill(BG_COLOR)
        self.draw_table_info(state, state.pot, override_community)

        n = len(state.players)
        for i, p in enumerate(state.players):
            is_actor = (i == current_actor_idx)

            hand_to_use = None
            if wait_for_next and showdown_hands and i in showdown_hands:
                hand_to_use = showdown_hands[i]

            self.draw_player(p, i, n, is_actor, show_all_cards, override_hand=hand_to_use)

        self.draw_action_log(game_logs)

        if human_msg:
            msg_width = (SCREEN_WIDTH - LOG_WIDTH) - 100
            msg_rect = pygame.Rect(50, 10, msg_width, 40)

            s = pygame.Surface((msg_rect.width, msg_rect.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, msg_rect.topleft)

            pygame.draw.rect(self.screen, GOLD, msg_rect, 1, border_radius=5)
            self.draw_text(human_msg, 50 + msg_width // 2, 30, GOLD)

        if wait_for_next:
            self.draw_next_round_btn()
        else:
            self.draw_controls(legal_actions, waiting_for_human, raising_mode)
            if raising_mode:
                try:
                    human = next(p for p in state.players if p.name == "Ty")
                    min_r = state.current_bet + state.min_raise
                    max_r = human.chips + human.current_bet
                    if min_r > max_r: min_r = max_r
                    self.draw_raise_ui(min_r, max_r)
                except StopIteration:
                    pass

        pygame.display.flip()