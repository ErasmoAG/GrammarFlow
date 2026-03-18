import arcade
import random

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE,
    LANES, LANE_WIDTH,   # LANE_WIDTH se mantiene importado por compatibilidad con FallingWord
    HITBOX_HEIGHT, HITBOX_Y,
    BASE_FALL_SPEED
)

from utils.loader import load_data
from game.states import STATE_START, STATE_MENU, STATE_GAME, STATE_GAMEOVER
from game.falling_word import FallingWord

# NUEVO: settings de dificultad (archivo limpio separado)
from game.difficulty import get_difficulty_settings


class GrammarGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Pantalla completa por defecto (puedes quitarlo si quieres)
        self.set_fullscreen(True)

        arcade.set_background_color(arcade.color.BLACK)

        # Inicia en pantalla de titulo
        self.current_state = STATE_START

        self.game_data = []
        self.current_sentences = []

        self.word_list = arcade.SpriteList()
        self.current_sentence_idx = 0
        self.current_wave_idx = 0

        self.score = 0
        self.combo = 0
        self.lives = 6  # sobreescrito por apply_difficulty_settings()
        self.constructed_sentence = ""

        # Flash feedback
        self.flash_alpha = 0
        self.flash_color = arcade.color.GREEN

        # --- MENU CONFIG ---
        self.selected_difficulty = "facil"          # ids de UI
        self.selected_tense = "presente_simple"     # debe existir en data.json
        self.selected_theme = "comida"              # debe existir en data.json

        # --- Valores base (siempre iguales) ---
        self.base_fall_speed = float(BASE_FALL_SPEED)
        self.base_hitbox_height = float(HITBOX_HEIGHT)

        # --- Valores activos (cambian según dificultad seleccionada al iniciar partida) ---
        self.fall_speed = self.base_fall_speed
        self.hitbox_height = self.base_hitbox_height

        self.menu_buttons = []
        self.start_button = None
        self.menu_y = {}

        self._init_menu_layout()

    # -------------------------
    # RESIZE
    # -------------------------
    def on_resize(self, width, height):
        super().on_resize(width, height)
        self._init_menu_layout()

    # -------------------------
    # DIFFICULTY HELPERS
    # -------------------------
    def apply_difficulty_settings(self):
        """
        Aplica SOLO al iniciar la partida.
        Delega completamente en difficulty.py como fuente de verdad.
        """
        settings = get_difficulty_settings(self.selected_difficulty)
        self.fall_speed = self.base_fall_speed * settings.fall_speed_multiplier
        self.hitbox_height = self.base_hitbox_height * settings.hitbox_scale
        self.lives = settings.lives

    def _update_speed_by_combo(self):
        """
        Recalcula fall_speed según dificultad + combo actual.
        Incremento leve: +5% por nivel de combo sobre la velocidad base de dificultad.
        Ej: combo 3 → ×1.15, combo 6 → ×1.30
        """
        settings = get_difficulty_settings(self.selected_difficulty)
        base_speed = self.base_fall_speed * settings.fall_speed_multiplier
        self.fall_speed = base_speed * (1 + self.combo * 0.05)

    # -------------------------
    # GAME FLOW
    # -------------------------
    def setup_game(self, tense, category):
        # Aplicar dificultad SOLO cuando se inicia partida desde el menú
        self.apply_difficulty_settings()

        self.game_data = load_data()

        self.current_sentences = [
            s for s in self.game_data
            if s.get("tense") == tense
            and s.get("category") == category
            and s.get("difficulty") == self.selected_difficulty
        ]

        random.shuffle(self.current_sentences)

        self.current_sentence_idx = 0
        self.current_wave_idx = 0
        self.score = 0
        self.combo = 0
        # self.lives ya fue seteado por apply_difficulty_settings() al inicio de setup_game
        self.constructed_sentence = ""
        self.word_list = arcade.SpriteList()

        # Si no hay oraciones, termina de forma clara (evita pantalla “vacía”)
        if not self.current_sentences:
            self.current_state = STATE_GAMEOVER
            return

        self.spawn_wave()
        self.current_state = STATE_GAME

    def spawn_wave(self):
        self.word_list = arcade.SpriteList()

        if self.current_sentence_idx >= len(self.current_sentences):
            self.current_state = STATE_GAMEOVER
            return

        if self.current_wave_idx == 0:
            self.constructed_sentence = ""

        sentence = self.current_sentences[self.current_sentence_idx]
        wave = sentence["waves"][self.current_wave_idx]

        options = [{"text": wave["correct"], "correct": True}]
        for dist in wave["distractors"]:
            options.append({"text": dist, "correct": False})

        random.shuffle(options)

        # Crea exactamente 4 palabras (una por carril)
        for i, option in enumerate(options):
            word = FallingWord(option["text"], i + 1, option["correct"])

            # ✅ Velocidad real según dificultad
            word.change_y = -self.fall_speed

            self.word_list.append(word)

    # -------------------------
    # DRAW
    # -------------------------
    def on_draw(self):
        self.clear()

        if self.current_state == STATE_START:
            self.draw_start()
        elif self.current_state == STATE_MENU:
            self.draw_menu()
        elif self.current_state == STATE_GAME:
            self.draw_gameplay()
        elif self.current_state == STATE_GAMEOVER:
            self.draw_gameover()

        # Flash overlay
        if self.flash_alpha > 0:
            safe_color = (*self.flash_color[:3], int(self.flash_alpha))
            arcade.draw_lrbt_rectangle_filled(0, self.width, 0, self.height, safe_color)

    def draw_start(self):
        W, H = self.width, self.height
        cx, cy = W / 2, H / 2

        arcade.draw_text(
            "GrammarFlow",
            cx,
            cy + H * 0.10,
            arcade.color.WHITE,
            int(max(H * 0.07, 36)),
            anchor_x="center",
            bold=True
        )
        arcade.draw_text(
            "Presiona 1 o Enter para continuar",
            cx,
            cy,
            arcade.color.GRAY,
            int(max(H * 0.025, 16)),
            anchor_x="center"
        )

    def draw_menu(self):
        W, H = self.width, self.height
        cx = W / 2

        # --- Título ---
        arcade.draw_text(
            "GrammarFlow",
            cx,
            H * 0.86,
            arcade.color.WHITE,
            int(max(H * 0.055, 28)),
            anchor_x="center",
            bold=True
        )
        arcade.draw_text(
            "CONFIGURACIÓN DE PARTIDA",
            cx,
            H * 0.81,
            arcade.color.GRAY,
            int(max(H * 0.018, 12)),
            anchor_x="center",
        )

        # --- Labels alineados con filas reales ---
        y_diff = self.menu_y.get("difficulty", H * 0.62)
        y_tense = self.menu_y.get("tense", H * 0.42)
        y_theme = self.menu_y.get("theme", H * 0.23)

        label_size = int(max(H * 0.018, 12))
        label_offset = int(max(H * 0.06, 38))

        arcade.draw_text("DIFICULTAD", cx, y_diff + label_offset, arcade.color.GRAY, label_size, anchor_x="center")
        arcade.draw_text("TIEMPO GRAMATICAL", cx, y_tense + label_offset, arcade.color.GRAY, label_size, anchor_x="center")
        arcade.draw_text("TEMA", cx, y_theme + label_offset, arcade.color.GRAY, label_size, anchor_x="center")

        # Botones de opciones
        for btn in self.menu_buttons:
            self._draw_button(btn)

        # Botón empezar
        self._draw_start_button()

        # Pie
        arcade.draw_text(
            "Disponible: Fácil/Normal • Presente • Comida / Separación de residuos",
            cx,
            H * 0.05,
            arcade.color.GRAY,
            int(max(H * 0.016, 11)),
            anchor_x="center",
        )

    def draw_gameplay(self):
        W, H = self.width, self.height

        # Separadores de carriles (RESPONSIVO)
        lane_width = W / LANES
        for i in range(1, LANES):
            x = i * lane_width
            arcade.draw_line(x, 0, x, H, arcade.color.DARK_GRAY, 1)

        # ✅ Hitbox real: ahora usa self.hitbox_height
        arcade.draw_lrbt_rectangle_outline(
            10, W - 10,
            HITBOX_Y - self.hitbox_height / 2,
            HITBOX_Y + self.hitbox_height / 2,
            arcade.color.MAGENTA, 3
        )

        # Texto de la oración
        if self.current_sentence_idx < len(self.current_sentences):
            sentence_data = self.current_sentences[self.current_sentence_idx]
            arcade.draw_text(
                f"Español: {sentence_data['spanish']}",
                20, H - 40,
                arcade.color.WHITE, 18
            )
            arcade.draw_text(
                f"Inglés: {self.constructed_sentence} ...",
                20, H - 70,
                arcade.color.YELLOW, 20,
                bold=True
            )

        # Score (RESPONSIVO)
        arcade.draw_text(
            f"Puntaje: {self.score}",
            W - 220,
            H - 40,
            arcade.color.YELLOW,
            18
        )

        # Combo
        if self.combo >= 6:
            combo_color = arcade.color.ORANGE
            combo_label = f"🔥 COMBO x{self.combo}"
        elif self.combo >= 3:
            combo_color = arcade.color.CYAN
            combo_label = f"⚡ COMBO x{self.combo}"
        elif self.combo > 0:
            combo_color = arcade.color.WHITE
            combo_label = f"COMBO x{self.combo}"
        else:
            combo_color = arcade.color.DARK_GRAY
            combo_label = "COMBO x0"

        arcade.draw_text(
            combo_label,
            W - 220,
            H - 70,
            combo_color,
            16,
            bold=self.combo >= 3
        )

        # Vidas
        arcade.draw_text(
            "Vidas: " + "❤" * self.lives,
            20,
            H - 105,
            arcade.color.PINK,
            18,
            bold=True
        )

        # Dibujo de palabras
        for word in self.word_list:
            word.draw_text()

    def draw_gameover(self):
        W, H = self.width, self.height
        cx, cy = W / 2, H / 2

        arcade.draw_text(
            "FIN DEL JUEGO",
            cx,
            cy + 50,
            arcade.color.GREEN,
            30,
            anchor_x="center"
        )
        arcade.draw_text(
            f"Puntaje Final: {self.score}",
            cx,
            cy,
            arcade.color.WHITE,
            20,
            anchor_x="center"
        )
        arcade.draw_text(
            "Enter para Menú",
            cx,
            cy - 60,
            arcade.color.GRAY,
            14,
            anchor_x="center"
        )

        # Mensaje útil si se quedó sin data por filtro
        if self.current_state == STATE_GAMEOVER and not self.current_sentences:
            arcade.draw_text(
                "No hay oraciones para esa selección.",
                cx,
                cy - 95,
                arcade.color.ORANGE,
                14,
                anchor_x="center"
            )

    # -------------------------
    # UPDATE / INPUT
    # -------------------------
    def on_update(self, delta_time):
        if self.flash_alpha > 0:
            self.flash_alpha -= 10

        if self.current_state != STATE_GAME:
            return

        self.word_list.update(delta_time)

        # Si la correcta salió de pantalla sin ser elegida -> miss
        wave_missed = False
        for word in self.word_list:
            if word.is_correct and word.center_y < 0:
                wave_missed = True

        if wave_missed:
            self.lives -= 1
            self.combo = self.combo // 2
            self._update_speed_by_combo()
            self.trigger_flash(is_success=False)
            if self.lives <= 0:
                self.current_state = STATE_GAMEOVER
                return
            self.advance_wave(word_chosen_text="[MISSED]")

    def on_key_press(self, key, modifiers):
        # Toggle fullscreen
        if key == arcade.key.F11:
            self.set_fullscreen(not self.fullscreen)
            return

        # START -> MENU
        if self.current_state == STATE_START:
            if key in (arcade.key.KEY_1, arcade.key.ENTER):
                self.current_state = STATE_MENU
            return

        if self.current_state == STATE_MENU:
            if key == arcade.key.ENTER:
                self.setup_game(self.selected_tense, self.selected_theme)

        elif self.current_state == STATE_GAMEOVER:
            if key == arcade.key.ENTER:
                self.current_state = STATE_MENU

        elif self.current_state == STATE_GAME:
            lane_pressed = 0
            if key == arcade.key.KEY_1:
                lane_pressed = 1
            elif key == arcade.key.KEY_2:
                lane_pressed = 2
            elif key == arcade.key.KEY_3:
                lane_pressed = 3
            elif key == arcade.key.KEY_4:
                lane_pressed = 4

            if lane_pressed != 0:
                self.check_collision(lane_pressed)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.current_state != STATE_MENU:
            return

        # Click en opciones
        for btn in self.menu_buttons:
            if self._point_in_rect(x, y, btn["rect"]):
                if btn["enabled"]:
                    self._set_selected_id(btn["group"], btn["id"])
                return

        # Click en empezar
        if self.start_button and self._point_in_rect(x, y, self.start_button["rect"]):
            self.setup_game(self.selected_tense, self.selected_theme)

    # -------------------------
    # COLLISION / GAME LOGIC
    # -------------------------
    def check_collision(self, lane):
        hit_something = False

        for word in self.word_list:
            if word.lane == lane:
                distance_y = abs(word.center_y - HITBOX_Y)

                # ✅ Hitbox real: ahora usa self.hitbox_height
                if distance_y <= (self.hitbox_height / 2):
                    hit_something = True

                    if word.is_correct:
                        self.score += 100
                        self.trigger_flash(is_success=True)
                        self.advance_wave(word_chosen_text=word.text)
                    else:
                        self.score -= 50
                        self.lives -= 1
                        self.combo = self.combo // 2
                        self._update_speed_by_combo()
                        self.trigger_flash(is_success=False)
                        if self.lives <= 0:
                            self.current_state = STATE_GAMEOVER
                            return
                        self.advance_wave(word_chosen_text=f"({word.text})")
                    break

        if not hit_something:
            self.score -= 10
            self.lives -= 1
            self.combo = self.combo // 2
            self._update_speed_by_combo()
            self.trigger_flash(is_success=False)
            if self.lives <= 0:
                self.current_state = STATE_GAMEOVER

    def advance_wave(self, word_chosen_text):
        self.constructed_sentence += " " + word_chosen_text
        sentence = self.current_sentences[self.current_sentence_idx]

        if self.current_wave_idx < len(sentence["waves"]) - 1:
            # Todavía hay fases en esta oración → avanzar fase
            self.current_wave_idx += 1
            self.spawn_wave()
        else:
            # ✅ Oración completa → subir combo y dar bonus
            self.combo += 1
            bonus = 50 * self.combo
            self.score += bonus
            self._update_speed_by_combo()

            self.current_sentence_idx += 1
            self.current_wave_idx = 0

            # Si ya usamos todas las oraciones, volver a mezclar
            if self.current_sentence_idx >= len(self.current_sentences):
                random.shuffle(self.current_sentences)
                self.current_sentence_idx = 0

            self.spawn_wave()

    def trigger_flash(self, is_success):
        self.flash_alpha = 150
        self.flash_color = arcade.color.NEON_GREEN if is_success else arcade.color.RED

    # -------------------------
    # MENU UI HELPERS
    # -------------------------
    def _init_menu_layout(self):
        self.menu_buttons = []
        self.menu_y = {}

        W, H = self.width, self.height
        cx = W / 2

        # Tamaños responsivos (mínimos para que no se rompa)
        gap = max(int(W * 0.02), 14)
        h_small = max(int(H * 0.05), 34)
        h_big = max(int(H * 0.075), 52)

        w_diff = max(int(W * 0.14), 120)       # dificultad
        w_big = max(int(W * 0.20), 180)        # tense / theme

        # Filas centradas
        y_diff = H * 0.62
        y_tense = H * 0.42
        y_theme = H * 0.23

        self.menu_y["difficulty"] = y_diff
        self.menu_y["tense"] = y_tense
        self.menu_y["theme"] = y_theme

        # Dificultad (Normal desbloqueado)
        diff_items = [
            {"id": "facil", "label": "Fácil", "enabled": True},
            {"id": "normal", "label": "Normal", "enabled": True},
            {"id": "dificil", "label": "Difícil", "enabled": False},
        ]
        self._add_row_buttons(
            group="difficulty",
            items=diff_items,
            y=y_diff,
            w=w_diff,
            h=h_small,
            gap=gap,
            start_x=cx - (3 * w_diff + 2 * gap) / 2
        )

        # Tiempo gramatical
        tense_items = [
            {"id": "presente_simple", "label": "Presente", "enabled": True},
            {"id": "pasado", "label": "Pasado", "enabled": False},
            {"id": "futuro", "label": "Futuro", "enabled": False},
        ]
        self._add_row_buttons(
            group="tense",
            items=tense_items,
            y=y_tense,
            w=w_big,
            h=h_big,
            gap=gap,
            start_x=cx - (3 * w_big + 2 * gap) / 2
        )

        # Tema (una fila, sin duplicados)
        theme_items = [
            {"id": "comida", "label": "Comida", "enabled": True},
            {"id": "separacion_residuos", "label": "Separación de residuos", "enabled": True},
            {"id": "viajes", "label": "Viajes", "enabled": False},
        ]
        self._add_row_buttons(
            group="theme",
            items=theme_items,
            y=y_theme,
            w=w_big,
            h=h_big,
            gap=gap,
            start_x=cx - (3 * w_big + 2 * gap) / 2
        )

        # Botón empezar (siempre visible)
        y_start = max(H * 0.10, y_theme - max(H * 0.16, 120))
        w_start = max(int(W * 0.18), 220)
        h_start = max(int(H * 0.07), 55)

        l = cx - w_start / 2
        r = cx + w_start / 2
        b = y_start - h_start / 2
        t = y_start + h_start / 2
        self.start_button = {"rect": (l, r, b, t), "label": "¡EMPEZAR!"}

    def _add_row_buttons(self, group, items, y, w, h, gap, start_x):
        x = start_x
        for it in items:
            l = x
            r = x + w
            b = y - h / 2
            t = y + h / 2
            self.menu_buttons.append({
                "group": group,
                "id": it["id"],
                "label": it["label"],
                "enabled": it["enabled"],
                "rect": (l, r, b, t),
            })
            x += w + gap

    def _point_in_rect(self, x, y, rect):
        l, r, b, t = rect
        return l <= x <= r and b <= y <= t

    def _get_selected_id(self, group):
        if group == "difficulty":
            return self.selected_difficulty
        if group == "tense":
            return self.selected_tense
        if group == "theme":
            return self.selected_theme
        return None

    def _set_selected_id(self, group, value):
        if group == "difficulty":
            self.selected_difficulty = value
        elif group == "tense":
            self.selected_tense = value
        elif group == "theme":
            self.selected_theme = value

    def _draw_button(self, btn):
        l, r, b, t = btn["rect"]
        enabled = btn["enabled"]
        selected = (btn["id"] == self._get_selected_id(btn["group"]))

        if enabled:
            arcade.draw_lrbt_rectangle_filled(l, r, b, t, arcade.color.DARK_SLATE_GRAY)
        else:
            arcade.draw_lrbt_rectangle_filled(l, r, b, t, arcade.color.DIM_GRAY)

        border_color = arcade.color.CYAN if selected else arcade.color.LIGHT_GRAY
        arcade.draw_lrbt_rectangle_outline(l, r, b, t, border_color, 2)

        label = btn["label"] + ("" if enabled else " 🔒")
        arcade.draw_text(
            label,
            (l + r) / 2,
            (b + t) / 2,
            arcade.color.WHITE,
            14,
            anchor_x="center",
            anchor_y="center",
        )

    def _draw_start_button(self):
        l, r, b, t = self.start_button["rect"]
        arcade.draw_lrbt_rectangle_filled(l, r, b, t, arcade.color.GOLD)
        arcade.draw_lrbt_rectangle_outline(l, r, b, t, arcade.color.WHITE, 2)
        arcade.draw_text(
            self.start_button["label"],
            (l + r) / 2,
            (b + t) / 2,
            arcade.color.BLACK,
            16,
            anchor_x="center",
            anchor_y="center",
            bold=True
        )