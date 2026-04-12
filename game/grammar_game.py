import arcade
import random
import math
from PIL import Image
import numpy as np

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE,
    LANES, LANE_WIDTH,   # LANE_WIDTH se mantiene importado por compatibilidad con FallingWord
    HITBOX_HEIGHT, HITBOX_Y,
    BASE_FALL_SPEED
)

from utils.loader import load_data
from game.states import STATE_START, STATE_MENU, STATE_GAME, STATE_GAMEOVER
from game.falling_word import FallingWord, LANE_COLORS, LANE_LETTERS


def _rr_fill(cx, cy, w, h, r, color):
    """Rounded rect filled — sin artefactos."""
    r = min(r, w / 2, h / 2)
    hw, hh = w / 2, h / 2
    # Barra horizontal central
    arcade.draw_lrbt_rectangle_filled(cx - hw, cx + hw, cy - hh + r, cy + hh - r, color)
    # Barra vertical central
    arcade.draw_lrbt_rectangle_filled(cx - hw + r, cx + hw - r, cy - hh, cy + hh, color)
    # 4 esquinas circulares exactas
    arcade.draw_circle_filled(cx - hw + r, cy - hh + r, r, color)
    arcade.draw_circle_filled(cx + hw - r, cy - hh + r, r, color)
    arcade.draw_circle_filled(cx - hw + r, cy + hh - r, r, color)
    arcade.draw_circle_filled(cx + hw - r, cy + hh - r, r, color)


def _rr_border(cx, cy, w, h, r, border_color, lw=2):
    """Borde sólido: dibuja exterior (color borde) y luego interior (blanco puro)."""
    _rr_fill(cx, cy, w + lw * 2, h + lw * 2, r + lw, border_color)
    _rr_fill(cx, cy, w, h, r, (255, 255, 255))
from game.difficulty import get_difficulty_settings
from game.particles import ParticleSystem


class GrammarGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Pantalla completa por defecto (puedes quitarlo si quieres)
        self.set_fullscreen(True)

        self.bg_sprite_list = None
        self._build_gradient_bg()

        # Botones de pantalla de inicio (se calculan en on_resize también)
        self._start_btn_play = None
        self._start_btn_quit = None
        self._init_start_buttons()

        arcade.set_background_color((225, 225, 240))

        # Inicia en pantalla de titulo
        self.current_state = STATE_START

        self.game_data = []
        self.current_sentences = []

        self.word_list = arcade.SpriteList()
        self.current_sentence_idx = 0
        self.current_wave_idx = 0

        self.score = 0
        self.combo = 0
        self.lives = 6
        self.constructed_sentence = ""

        # ── Tracking de partida ──
        self.hits      = 0   # fases correctas
        self.errors    = 0   # errores totales
        self.max_combo = 0   # combo máximo alcanzado

        # ── Textos HUD cacheados (arcade.Text es ~10x más rápido que draw_text) ──
        self._txt_spanish  = arcade.Text("", 20, 0, (60, 70, 100), 18)
        self._txt_english  = arcade.Text("", 20, 0, (70, 130, 200), 20, bold=True)
        self._txt_score    = arcade.Text("", 0,  0, (70, 130, 200), 18)
        self._txt_combo    = arcade.Text("", 0,  0, (180, 185, 200), 16, bold=False)
        self._txt_lives    = arcade.Text("", 20, 0, (220, 80, 90),  18, bold=True)

        # Flash feedback
        self.flash_alpha = 0
        self.flash_color = arcade.color.GREEN

        # ── Efectos visuales de combo ──
        self.combo_tier    = 0
        self.pulse_t       = 0.0
        self.ambient_timer = 0

        # Screen shake
        self.shake_frames = 0       # frames restantes de shake
        self.shake_magnitude = 8    # píxeles máx de desplazamiento
        self.shake_x = 0
        self.shake_y = 0

        # Partículas
        self.particle_system = ParticleSystem()

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
        self.menu_back_button = None
        self.menu_y = {}
        self._result_btn_back   = None
        self._result_btn_retry  = None

        self._init_menu_layout()
        self._init_result_buttons()

    # -------------------------
    # RESIZE
    # -------------------------
    def on_resize(self, width, height):
        super().on_resize(width, height)
        self._build_gradient_bg()
        self._init_start_buttons()
        self._init_result_buttons()
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

    def _update_combo_tier(self):
        """Actualiza el tier visual segun el combo actual."""
        if self.combo >= 6:
            self.combo_tier = 2
        elif self.combo >= 3:
            self.combo_tier = 1
        else:
            self.combo_tier = 0

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
        self.combo_tier    = 0
        self.pulse_t       = 0.0
        self.ambient_timer = 0
        self.hits      = 0
        self.errors    = 0
        self.max_combo = 0
        # self.lives ya fue seteado por apply_difficulty_settings() al inicio de setup_game
        self.constructed_sentence = ""
        self.word_list = arcade.SpriteList()
        self.particle_system.clear()

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

        # Degradado pastel simulado (esquinas semitransparentes sobre base)
        self._draw_gradient_bg()

        # Calcular offset de shake para draw_gameplay
        if self.shake_frames > 0:
            self.shake_x = random.randint(-self.shake_magnitude, self.shake_magnitude)
            self.shake_y = random.randint(-self.shake_magnitude, self.shake_magnitude)
        else:
            self.shake_x = 0
            self.shake_y = 0

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

    def _build_gradient_bg(self):
        """
        Genera un gradiente pastel pixel-perfect con PIL y lo convierte a sprite de Arcade.
        Esquina sup-izq: lavanda rosa → centro: blanco cremoso → inf-der: azul melocotón.
        """
        W, H = self.width, self.height
        if W <= 0 or H <= 0:
            return

        # Colores de las 4 esquinas (R,G,B) — más vibrantes
        tl = np.array([210, 175, 235], dtype=np.float32)   # lavanda rosa fuerte
        tr = np.array([250, 200, 185], dtype=np.float32)   # melocotón vivo
        bl = np.array([175, 215, 250], dtype=np.float32)   # azul cielo
        br = np.array([185, 245, 225], dtype=np.float32)   # menta verde

        xs = np.linspace(0, 1, W, dtype=np.float32)
        ys = np.linspace(0, 1, H, dtype=np.float32)
        xg, yg = np.meshgrid(xs, ys)

        # Interpolación bilineal
        r = ((1 - xg) * (1 - yg) * tl[0] + xg * (1 - yg) * tr[0] +
             (1 - xg) * yg       * bl[0] + xg * yg       * br[0])
        g = ((1 - xg) * (1 - yg) * tl[1] + xg * (1 - yg) * tr[1] +
             (1 - xg) * yg       * bl[1] + xg * yg       * br[1])
        b = ((1 - xg) * (1 - yg) * tl[2] + xg * (1 - yg) * tr[2] +
             (1 - xg) * yg       * bl[2] + xg * yg       * br[2])

        arr = np.stack([r, g, b], axis=2).astype(np.uint8)
        img = Image.fromarray(arr, "RGB").transpose(Image.FLIP_TOP_BOTTOM).convert("RGBA")

        tex = arcade.Texture(image=img)
        sprite = arcade.Sprite()
        sprite.texture = tex
        sprite.center_x = W / 2
        sprite.center_y = H / 2
        self.bg_sprite_list = arcade.SpriteList()
        self.bg_sprite_list.append(sprite)

    def _draw_gradient_bg(self):
        if self.bg_sprite_list:
            self.bg_sprite_list.draw()

    def _init_start_buttons(self):
        W, H = self.width, self.height
        cx = W / 2
        bw = min(int(W * 0.28), 340)
        bh = max(int(H * 0.075), 54)
        r = bh / 2
        y_play = H * 0.34
        y_quit = H * 0.22
        self._start_btn_play = (cx - bw/2, cx + bw/2, y_play - bh/2, y_play + bh/2)
        self._start_btn_quit = (cx - bw/2, cx + bw/2, y_quit - bh/2, y_quit + bh/2)

    def draw_start(self):
        W, H = self.width, self.height
        cx = W / 2

        # ── Título grande bicolor ──
        title_size = int(max(H * 0.088, 48))
        t1 = arcade.Text("GRAMMAR", 0, 0, (25, 35, 75),  title_size, bold=True)
        t2 = arcade.Text("FLOW",    0, 0, (60, 185, 195), title_size, bold=True)
        total_w = t1.content_width + t2.content_width
        tx = cx - total_w / 2
        title_y = H * 0.75

        arcade.draw_text("GRAMMAR", tx, title_y,
                         (25, 35, 75), title_size, bold=True)
        arcade.draw_text("FLOW", tx + t1.content_width, title_y,
                         (60, 185, 195), title_size, bold=True)

        # Subtítulo
        arcade.draw_text(
            "Domina el inglés al ritmo del juego",
            cx, title_y - title_size - 8,
            (100, 110, 135), int(max(H * 0.024, 14)),
            anchor_x="center"
        )

        # ── Ilustración: mini carriles intercalados ──
        card_w = min(W * 0.14, 165)
        card_h = card_w * 0.90
        card_cx = cx
        card_cy = H * 0.52

        # Card blanca
        _rr_fill(card_cx, card_cy, card_w, card_h, 16, (255, 255, 255, 245))

        col_colors = [(60, 185, 195), (50, 200, 100), (230, 175, 45), (220, 70, 120)]
        n = 4
        col_w = card_w * 0.16
        col_h = card_h * 0.68
        gap   = (card_w - n * col_w) / (n + 1)
        dot_r = col_w * 0.38

        for i, c in enumerate(col_colors):
            lx = card_cx - card_w / 2 + gap + i * (col_w + gap) + col_w / 2
            offset = card_h * 0.06 if i % 2 == 0 else -card_h * 0.06
            ly = card_cy + offset
            _rr_fill(lx, ly, col_w, col_h, col_w * 0.35, (30, 38, 65))
            arcade.draw_circle_filled(lx, ly - col_h * 0.26, dot_r, c)

        # ── Botón JUGAR ──
        l, r, b, t = self._start_btn_play
        bw, bh = r - l, t - b
        bcx, bcy = (l + r) / 2, (b + t) / 2
        _rr_fill(bcx, bcy, bw, bh, bh / 2, (240, 185, 40))
        arcade.draw_text("▶   ¡JUGAR!", bcx, bcy,
                         (45, 35, 5), int(max(H * 0.030, 18)),
                         anchor_x="center", anchor_y="center", bold=True)

        # ── Botón SALIR (más pequeño) ──
        l2, r2, b2, t2 = self._start_btn_quit
        bw2 = (r2 - l2) * 0.65
        bh2 = (t2 - b2) * 0.78
        bcx2, bcy2 = (l2 + r2) / 2, (b2 + t2) / 2
        _rr_fill(bcx2, bcy2, bw2, bh2, bh2 / 2, (155, 160, 175))
        arcade.draw_text("→  SALIR", bcx2, bcy2,
                         (255, 255, 255), int(max(H * 0.022, 13)),
                         anchor_x="center", anchor_y="center", bold=True)

    def draw_menu(self):
        W, H = self.width, self.height
        cx = W / 2

        # ── Card blanca grande y centrada ──
        card_w = min(W * 0.82, 920)
        card_h = H * 0.90
        card_cx = cx
        card_cy = H * 0.50

        _rr_fill(card_cx, card_cy, card_w, card_h, 28, (255, 255, 255, 240))

        # ── Título centrado ──
        title_y = card_cy + card_h / 2 - card_h * 0.11
        title_size = int(max(H * 0.055, 28))
        # Medir ancho de "Grammar" para centrar el conjunto
        t1 = arcade.Text("Grammar", 0, 0, (25, 35, 75), title_size, bold=True)
        t2 = arcade.Text("Flow",    0, 0, (70, 145, 215), title_size, bold=True)
        total_w = t1.content_width + t2.content_width
        x_grammar = cx - total_w / 2

        arcade.draw_text("Grammar", x_grammar, title_y,
                         (25, 35, 75), title_size, bold=True)
        arcade.draw_text("Flow", x_grammar + t1.content_width, title_y,
                         (70, 145, 215), title_size, bold=True)

        arcade.draw_text(
            "CONFIGURACIÓN DE PARTIDA",
            cx, title_y - title_size - 6,
            (175, 178, 192), int(max(H * 0.018, 11)),
            anchor_x="center"
        )

        # ── Labels todos en gris ──
        y_diff  = self.menu_y.get("difficulty", H * 0.62)
        y_tense = self.menu_y.get("tense",      H * 0.42)
        y_theme = self.menu_y.get("theme",       H * 0.23)

        lsize = int(max(H * 0.018, 12))
        loff  = int(max(H * 0.044, 28))
        gray  = (110, 113, 130)

        for label, y in [("DIFICULTAD", y_diff), ("TIEMPO GRAMATICAL", y_tense), ("TEMA", y_theme)]:
            arcade.draw_text(label, cx, y + loff, gray, lsize, anchor_x="center", bold=True)

        for btn in self.menu_buttons:
            self._draw_button(btn)

        self._draw_start_button()

        arcade.draw_text(
            "Disponible: Fácil/Normal • Presente • Comida / Separación de residuos",
            cx, card_cy - card_h / 2 + 14,
            (185, 188, 200), int(max(H * 0.015, 10)),
            anchor_x="center"
        )

    def draw_gameplay(self):
        W, H = self.width, self.height
        ox, oy = self.shake_x, self.shake_y

        lane_width = W / LANES

        # ── 0. Efectos visuales de combo tier ──
        if self.combo_tier == 1:
            # Tier 1: tinte cyan suave pulsante
            tint_a = int(30 + 15 * math.sin(self.pulse_t))
            arcade.draw_lrbt_rectangle_filled(0, W, 0, H, (60, 200, 230, tint_a))
        elif self.combo_tier == 2:
            # Tier 2: mismo cyan, pulso más lento
            tint_a = int(32 + 14 * math.sin(self.pulse_t))
            arcade.draw_lrbt_rectangle_filled(0, W, 0, H, (60, 200, 230, tint_a))

        # ── 1. Separadores de carriles + tinte de color por carril ──
        from game.falling_word import LANE_COLORS, LANE_LETTERS
        lane_line_w = 5 if self.combo_tier == 2 else (3 if self.combo_tier == 1 else 1)
        lane_line_alpha = int(180 + 70 * abs(math.sin(self.pulse_t))) if self.combo_tier > 0 else 120
        for i in range(1, LANES):
            x = i * lane_width + ox
            arcade.draw_line(x, oy, x, H + oy, (200, 200, 215, lane_line_alpha), lane_line_w)

        lane_tint = int(18 + 22 * abs(math.sin(self.pulse_t))) if self.combo_tier == 2 else (12 if self.combo_tier == 1 else 18)
        for lane in range(1, LANES + 1):
            color = LANE_COLORS[lane]
            lx0 = (lane - 1) * lane_width + ox
            lx1 = lane * lane_width + ox
            arcade.draw_lrbt_rectangle_filled(lx0, lx1, oy, H + oy, (*color, lane_tint))

        # ── 2. UI superior — textos cacheados ──
        if self.current_sentence_idx < len(self.current_sentences):
            sentence_data = self.current_sentences[self.current_sentence_idx]
            self._txt_spanish.text  = f"Español: {sentence_data['spanish']}"
            self._txt_english.text  = f"Inglés: {self.constructed_sentence} ..."
            self._txt_spanish.x = 20 + ox;  self._txt_spanish.y = H - 40 + oy
            self._txt_english.x = 20 + ox;  self._txt_english.y = H - 70 + oy
            self._txt_spanish.draw()
            self._txt_english.draw()

        self._txt_score.text = f"Puntaje: {self.score}"
        self._txt_score.x = W - 220 + ox
        self._txt_score.y = H - 40 + oy
        self._txt_score.draw()

        if self.combo >= 6:
            combo_color = (210, 90, 60)
            combo_label = f"🔥 COMBO x{self.combo}"
        elif self.combo >= 3:
            combo_color = (70, 130, 200)
            combo_label = f"⚡ COMBO x{self.combo}"
        elif self.combo > 0:
            combo_color = (80, 90, 120)
            combo_label = f"COMBO x{self.combo}"
        else:
            combo_color = (180, 185, 200)
            combo_label = "COMBO x0"

        self._txt_combo.text  = combo_label
        self._txt_combo.color = combo_color
        self._txt_combo.bold  = self.combo >= 3
        self._txt_combo.x = W - 220 + ox
        self._txt_combo.y = H - 70 + oy
        self._txt_combo.draw()

        self._txt_lives.text = "Vidas: " + "❤" * self.lives
        self._txt_lives.x = 20 + ox
        self._txt_lives.y = H - 105 + oy
        self._txt_lives.draw()

        # ── 3. Palabras cayendo ──
        for word in self.word_list:
            word.draw_text()

        # ── 4. Zona hitbox encima de las palabras ──
        hx0 = 10 + ox
        hx1 = W - 10 + ox
        hy0 = HITBOX_Y - self.hitbox_height / 2 + oy
        hy1 = HITBOX_Y + self.hitbox_height / 2 + oy
        hcx = (hx0 + hx1) / 2
        hcy = (hy0 + hy1) / 2
        hw  = hx1 - hx0
        hh  = hy1 - hy0

        # Frosted glass: capas semitransparentes para simular blur
        arcade.draw_lrbt_rectangle_filled(hx0, hx1, hy0, hy1, (255, 255, 255, 30))
        arcade.draw_lrbt_rectangle_filled(hx0 + 4, hx1 - 4, hy0 + 4, hy1 - 4, (255, 255, 255, 35))
        arcade.draw_lrbt_rectangle_filled(hx0 + 8, hx1 - 8, hy0 + 8, hy1 - 8, (255, 255, 255, 40))

        # Sombra superior (borde difuminado arriba)
        for i in range(8):
            alpha = int(18 - i * 2)
            arcade.draw_lrbt_rectangle_filled(
                hx0, hx1,
                hy1 - i, hy1 + 1,
                (180, 190, 220, alpha)
            )

        # Línea punteada (borde de la zona)
        dash_len, gap_len = 12, 7
        # Top
        x = hx0
        while x < hx1:
            arcade.draw_line(x, hy1, min(x + dash_len, hx1), hy1, (160, 170, 200, 160), 2)
            x += dash_len + gap_len
        # Bottom
        x = hx0
        while x < hx1:
            arcade.draw_line(x, hy0, min(x + dash_len, hx1), hy0, (160, 170, 200, 160), 2)
            x += dash_len + gap_len
        # Left
        y = hy0
        while y < hy1:
            arcade.draw_line(hx0, y, hx0, min(y + dash_len, hy1), (160, 170, 200, 160), 2)
            y += dash_len + gap_len
        # Right
        y = hy0
        while y < hy1:
            arcade.draw_line(hx1, y, hx1, min(y + dash_len, hy1), (160, 170, 200, 160), 2)
            y += dash_len + gap_len

        # ── 5. Círculos A/B/X/Y encima de todo ──
        circle_r = 26
        circle_y = hcy
        for lane in range(1, LANES + 1):
            lx = (lane - 0.5) * lane_width + ox
            color = LANE_COLORS[lane]
            arcade.draw_circle_filled(lx, circle_y, circle_r, (*color, 230))
            arcade.draw_circle_outline(lx, circle_y, circle_r, (255, 255, 255, 200), 3)
            arcade.draw_text(
                LANE_LETTERS[lane], lx, circle_y,
                (255, 255, 255), 17,
                anchor_x="center", anchor_y="center", bold=True
            )

        # ── 6. Partículas ──
        self.particle_system.draw()

    def _init_result_buttons(self):
        W, H = self.width, self.height
        cx = W / 2
        bw = max(int(W * 0.13), 155)
        bh = max(int(H * 0.058), 44)
        gap = max(int(W * 0.02), 16)
        y_btn = H * 0.16
        self._result_btn_back  = (cx - gap/2 - bw, cx - gap/2,      y_btn - bh/2, y_btn + bh/2)
        self._result_btn_retry = (cx + gap/2,       cx + gap/2 + bw, y_btn - bh/2, y_btn + bh/2)

    def draw_gameover(self):
        W, H = self.width, self.height
        cx = W / 2

        # ── Título ──
        arcade.draw_text("GRAMMAR FLOW", cx, H * 0.88,
                         (25, 35, 75), int(max(H * 0.045, 26)),
                         anchor_x="center", bold=True)
        arcade.draw_text("¡PARTIDA FINALIZADA!", cx, H * 0.81,
                         (255, 255, 255), int(max(H * 0.022, 13)),
                         anchor_x="center", bold=True)
        # Pill de subtítulo
        pill_w, pill_h = max(int(W * 0.22), 240), max(int(H * 0.038), 28)
        _rr_fill(cx, H * 0.81, pill_w, pill_h, pill_h / 2, (70, 140, 215))
        arcade.draw_text("¡PARTIDA FINALIZADA!", cx, H * 0.81,
                         (255, 255, 255), int(max(H * 0.020, 12)),
                         anchor_x="center", anchor_y="center", bold=True)

        # ── Card blanca central ──
        card_w = min(W * 0.50, 560)
        card_h = H * 0.52
        card_cy = H * 0.48
        _rr_fill(cx, card_cy, card_w, card_h, 22, (255, 255, 255, 240))

        # Puntaje grande
        arcade.draw_text("TU PUNTUACIÓN", cx, card_cy + card_h * 0.36,
                         (130, 135, 155), int(max(H * 0.018, 11)),
                         anchor_x="center", bold=True)
        arcade.draw_text(f"{self.score:,}", cx, card_cy + card_h * 0.18,
                         (50, 190, 100), int(max(H * 0.075, 44)),
                         anchor_x="center", bold=True)

        # ── 3 stats: Aciertos / Errores / Combo máx ──
        stat_y = card_cy - card_h * 0.08
        stat_w = card_w * 0.25
        stat_h = card_h * 0.28
        stat_gap = card_w * 0.05
        positions = [
            cx - stat_w - stat_gap,
            cx,
            cx + stat_w + stat_gap,
        ]
        stat_data = [
            ("ACIERTOS", str(self.hits),      (50, 190, 100)),
            ("ERRORES",  str(self.errors),     (220, 80, 90)),
            ("COMBO MÁX",f"x{self.max_combo}", (70, 140, 215)),
        ]
        for (sx, (label, value, color)) in zip(positions, stat_data):
            _rr_fill(sx, stat_y, stat_w, stat_h, 12, (245, 246, 250))
            arcade.draw_text(label, sx, stat_y + stat_h * 0.22,
                             (150, 155, 170), int(max(H * 0.015, 10)),
                             anchor_x="center", bold=True)
            arcade.draw_text(value, sx, stat_y - stat_h * 0.08,
                             color, int(max(H * 0.038, 22)),
                             anchor_x="center", anchor_y="center", bold=True)

        # ── Botones ──
        self._init_result_buttons()

        # Volver al menú (izquierda, gris)
        if self._result_btn_back:
            l, r, b, t = self._result_btn_back
            bcx, bcy = (l+r)/2, (b+t)/2
            bw, bh2 = r-l, t-b
            _rr_fill(bcx, bcy, bw, bh2, bh2/2, (155, 160, 175))
            arcade.draw_text("◀  Menú", bcx, bcy,
                             (255, 255, 255), 14,
                             anchor_x="center", anchor_y="center", bold=True)

        # Reiniciar (derecha, dorado)
        if self._result_btn_retry:
            l, r, b, t = self._result_btn_retry
            bcx, bcy = (l+r)/2, (b+t)/2
            bw, bh2 = r-l, t-b
            _rr_fill(bcx, bcy, bw, bh2, bh2/2, (240, 185, 40))
            arcade.draw_text("Reiniciar  ▶", bcx, bcy,
                             (40, 30, 10), 14,
                             anchor_x="center", anchor_y="center", bold=True)

    # -------------------------
    # UPDATE / INPUT
    # -------------------------
    def on_update(self, delta_time):
        if self.flash_alpha > 0:
            self.flash_alpha -= 10

        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Pulso oscilante para efectos de tier
        self.pulse_t = (self.pulse_t + 0.14) % (2 * math.pi)

        # Partículas ambientales según tier
        if self.current_state == STATE_GAME and self.combo_tier > 0:
            self.ambient_timer += 1
            spawn_rate = 3 if self.combo_tier == 2 else 5
            if self.ambient_timer >= spawn_rate:
                self.ambient_timer = 0
                self.particle_system.spawn_ambient(self.combo_tier, self.width, self.height)

        self.particle_system.update()

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
            self.errors += 1
            self.combo = self.combo // 2
            self._update_speed_by_combo()
            self._update_combo_tier()
            self.trigger_flash(is_success=False)
            self.trigger_shake()
            if self.lives <= 0:
                self.current_state = STATE_GAMEOVER
                return
            self.advance_wave(word_chosen_text="[MISSED]")

    def on_key_press(self, key, modifiers):
        # Toggle fullscreen
        if key == arcade.key.F11:
            self.set_fullscreen(not self.fullscreen)
            return

        # START -> MENU o SALIR
        if self.current_state == STATE_START:
            if key in (arcade.key.KEY_1, arcade.key.ENTER):
                self.current_state = STATE_MENU
            elif key == arcade.key.ESCAPE:
                arcade.exit()
            return

        if self.current_state == STATE_MENU:
            if key == arcade.key.ENTER:
                self.setup_game(self.selected_tense, self.selected_theme)

        elif self.current_state == STATE_GAMEOVER:
            if key == arcade.key.ENTER:
                self.setup_game(self.selected_tense, self.selected_theme)
            elif key == arcade.key.ESCAPE:
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
        # Pantalla de inicio
        if self.current_state == STATE_START:
            if self._start_btn_play and self._point_in_rect(x, y, self._start_btn_play):
                self.current_state = STATE_MENU
            elif self._start_btn_quit and self._point_in_rect(x, y, self._start_btn_quit):
                arcade.exit()
            return

        # Pantalla de resultados
        if self.current_state == STATE_GAMEOVER:
            if self._result_btn_back and self._point_in_rect(x, y, self._result_btn_back):
                self.current_state = STATE_MENU
            elif self._result_btn_retry and self._point_in_rect(x, y, self._result_btn_retry):
                self.setup_game(self.selected_tense, self.selected_theme)
            return

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

        # Click en menú principal
        if self.menu_back_button and self._point_in_rect(x, y, self.menu_back_button["rect"]):
            self.current_state = STATE_START

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
                        self.hits += 1
                        self.trigger_flash(is_success=True)
                        self.advance_wave(word_chosen_text=word.text)
                    else:
                        self.score -= 50
                        self.lives -= 1
                        self.errors += 1
                        self.combo = self.combo // 2
                        self._update_speed_by_combo()
                        self._update_combo_tier()
                        self.trigger_flash(is_success=False)
                        self.trigger_shake()
                        if self.lives <= 0:
                            self.current_state = STATE_GAMEOVER
                            return
                        self.advance_wave(word_chosen_text=f"({word.text})")
                    break

        if not hit_something:
            self.score -= 10
            self.lives -= 1
            self.errors += 1
            self.combo = self.combo // 2
            self._update_speed_by_combo()
            self._update_combo_tier()
            self.trigger_flash(is_success=False)
            self.trigger_shake()
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
            self._update_combo_tier()
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            # Partículas en umbrales de combo
            if self.combo >= 3:
                self.particle_system.spawn(self.combo, self.width, HITBOX_Y)

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

    def trigger_shake(self):
        """Activa el screen shake por 8 frames."""
        self.shake_frames = 8

    # -------------------------
    # MENU UI HELPERS
    # -------------------------
    def _init_menu_layout(self):
        self.menu_buttons = []
        self.menu_y = {}

        W, H = self.width, self.height
        cx = W / 2

        gap    = max(int(W * 0.016), 12)
        h_pill = max(int(H * 0.038), 30)   # dificultad — pill pequeño
        h_card = max(int(H * 0.055), 40)   # tense / theme — card mediana
        w_diff = max(int(W * 0.11),  95)   # ancho pill dificultad
        w_big  = max(int(W * 0.17), 150)   # ancho card tense/theme

        y_diff  = H * 0.66
        y_tense = H * 0.48
        y_theme = H * 0.31

        self.menu_y["difficulty"] = y_diff
        self.menu_y["tense"]      = y_tense
        self.menu_y["theme"]      = y_theme

        diff_items = [
            {"id": "facil",   "label": "Fácil",   "enabled": True},
            {"id": "normal",  "label": "Normal",  "enabled": True},
            {"id": "dificil", "label": "Difícil", "enabled": False},
        ]
        self._add_row_buttons("difficulty", diff_items, y_diff, w_diff, h_pill, gap,
                              cx - (3 * w_diff + 2 * gap) / 2)

        tense_items = [
            {"id": "presente_simple", "label": "Presente", "enabled": True},
            {"id": "pasado",          "label": "Pasado",   "enabled": False},
            {"id": "futuro",          "label": "Futuro",   "enabled": False},
        ]
        self._add_row_buttons("tense", tense_items, y_tense, w_big, h_card, gap,
                              cx - (3 * w_big + 2 * gap) / 2)

        theme_items = [
            {"id": "comida",             "label": "Comida",                 "enabled": True},
            {"id": "separacion_residuos","label": "Sep. residuos",          "enabled": True},
            {"id": "viajes",             "label": "Viajes",                 "enabled": False},
        ]
        self._add_row_buttons("theme", theme_items, y_theme, w_big, h_card, gap,
                              cx - (3 * w_big + 2 * gap) / 2)

        # Botones inferiores: "Menu Principal" (izq) y "¡EMPEZAR!" (der)
        y_start  = H * 0.14
        h_start  = max(int(H * 0.058), 44)
        w_start  = max(int(W * 0.14), 170)
        btn_gap  = max(int(W * 0.02), 16)

        # Botón izquierdo: Menu Principal
        l_menu = cx - btn_gap / 2 - w_start
        r_menu = cx - btn_gap / 2
        b_menu = y_start - h_start / 2
        t_menu = y_start + h_start / 2
        self.menu_back_button = {"rect": (l_menu, r_menu, b_menu, t_menu)}

        # Botón derecho: Empezar
        l = cx + btn_gap / 2
        r = cx + btn_gap / 2 + w_start
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
        cx = (l + r) / 2
        cy = (b + t) / 2
        w  = r - l
        h  = t - b
        enabled  = btn["enabled"]
        selected = (btn["id"] == self._get_selected_id(btn["group"]))
        group    = btn["group"]

        if group == "difficulty":
            radius = h / 2
            if not enabled:
                _rr_fill(cx, cy, w, h, radius, (235, 236, 240))
                text_color = (190, 192, 200)
            elif selected:
                colors = {"facil": (50, 190, 100), "normal": (70, 140, 215), "dificil": (220, 80, 90)}
                _rr_fill(cx, cy, w, h, radius, colors.get(btn["id"], (70, 140, 215)))
                text_color = (255, 255, 255)
            else:
                colors = {"facil": (50, 190, 100), "normal": (70, 140, 215), "dificil": (220, 80, 90)}
                c = colors.get(btn["id"], (160, 165, 185))
                _rr_border(cx, cy, w, h, radius, c, lw=2)
                text_color = c
        else:
            radius = 12
            if not enabled:
                _rr_fill(cx, cy, w, h, radius, (242, 243, 246))
                text_color = (190, 192, 200)
            elif selected:
                _rr_border(cx, cy, w, h, radius, (70, 140, 215), lw=2)
                text_color = (70, 140, 215)
            else:
                _rr_border(cx, cy, w, h, radius, (210, 213, 222), lw=2)
                text_color = (80, 90, 115)

        label = btn["label"] + ("" if enabled else " 🔒")
        arcade.draw_text(
            label, cx, cy, text_color, 15,
            anchor_x="center", anchor_y="center",
            bold=True
        )

    def _draw_start_button(self):
        # ── Botón izquierdo: Menú Principal (gris, estilo SALIR) ──
        if self.menu_back_button:
            l, r, b, t = self.menu_back_button["rect"]
            cx2 = (l + r) / 2;  cy2 = (b + t) / 2
            w2 = r - l;          h2 = t - b
            _rr_fill(cx2, cy2, w2, h2, h2 / 2, (155, 160, 175))
            arcade.draw_text(
                "◀  Menú", cx2, cy2,
                (255, 255, 255), 15,
                anchor_x="center", anchor_y="center", bold=True
            )

        # ── Botón derecho: ¡EMPEZAR! (dorado) ──
        if self.start_button:
            l, r, b, t = self.start_button["rect"]
            cx = (l + r) / 2;  cy = (b + t) / 2
            w  = r - l;         h  = t - b
            _rr_fill(cx, cy, w, h, h / 2, (240, 185, 40))
            arcade.draw_text(
                "¡EMPEZAR!  ▶", cx, cy,
                (40, 30, 10), 15,
                anchor_x="center", anchor_y="center", bold=True
            )