# game/tutorial.py
import arcade
import json
import os

TUTORIAL_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tutorial_done.json")

# ── Helpers de dibujo (copiados de grammar_game para no importar circularmente) ──
def _rr_fill(cx, cy, w, h, r, color):
    r = min(r, w / 2, h / 2)
    hw, hh = w / 2, h / 2
    arcade.draw_lrbt_rectangle_filled(cx - hw, cx + hw, cy - hh + r, cy + hh - r, color)
    arcade.draw_lrbt_rectangle_filled(cx - hw + r, cx + hw - r, cy - hh, cy + hh, color)
    arcade.draw_circle_filled(cx - hw + r, cy - hh + r, r, color)
    arcade.draw_circle_filled(cx + hw - r, cy - hh + r, r, color)
    arcade.draw_circle_filled(cx - hw + r, cy + hh - r, r, color)
    arcade.draw_circle_filled(cx + hw - r, cy + hh - r, r, color)


LANE_COLORS  = {1: (50,200,100), 2: (230,80,100), 3: (70,160,220), 4: (230,175,45)}
LANE_LETTERS = {1: "1", 2: "2", 3: "3", 4: "4"}

STEPS = [
    {
        "title": "Welcome to GrammarFlow!",
        "body": (
            "In this game you will practice\n"
            "English grammar by building\n"
            "sentences word by word."
        ),
        "highlight": None,
    },
    {
        "title": "Read the sentence",
        "body": (
            "Each round shows you a sentence\n"
            "in Spanish at the top.\n"
            "You have 2 seconds to read it\n"
            "before the words start falling."
        ),
        "highlight": "spanish",
    },
    {
        "title": "4 Lanes — 4 Keys",
        "body": (
            "The screen is divided into 4 lanes.\n"
            "Press  1  2  3  4  on your keyboard\n"
            "to select the word in that lane\n"
            "when it reaches the zone below."
        ),
        "highlight": "lanes",
    },
    {
        "title": "The Hit Zone",
        "body": (
            "The dashed rectangle at the bottom\n"
            "is the hit zone.\n"
            "Press the key ONLY when the correct\n"
            "word is inside this zone."
        ),
        "highlight": "hitbox",
    },
    {
        "title": "Build the sentence",
        "body": (
            "Each sentence has 3 phases:\n"
            "Subject → Verb → Complement\n"
            "Choose the right word each time\n"
            "to complete the full sentence."
        ),
        "highlight": "english",
    },
    {
        "title": "Lives & Errors",
        "body": (
            "You start with several lives (❤).\n"
            "You lose one if you:\n"
            "• Press the wrong word\n"
            "• Press when nothing is in the zone\n"
            "• Let the correct word fall past"
        ),
        "highlight": "lives",
    },
    {
        "title": "Combo & Score",
        "body": (
            "Complete sentences in a row to\n"
            "build your COMBO multiplier.\n"
            "Higher combo = more points + faster speed.\n"
            "Making an error halves your combo."
        ),
        "highlight": "combo",
    },
    {
        "title": "Ready to play!",
        "body": (
            "That's everything you need to know.\n"
            "Good luck and have fun!\n\n"
            "Press  NEXT  to start your first game."
        ),
        "highlight": None,
    },
]


class TutorialManager:
    def __init__(self):
        self.active    = False
        self.step      = 0
        self.completed = self._load()

        # Botones
        self._btn_next = None
        self._btn_skip = None

    # ── Persistencia ────────────────────────────────────────────
    def _load(self) -> bool:
        try:
            with open(TUTORIAL_FILE, "r") as f:
                return json.load(f).get("completed", False)
        except Exception:
            return False

    def _save(self):
        try:
            with open(TUTORIAL_FILE, "w") as f:
                json.dump({"completed": True}, f)
        except Exception:
            pass

    # ── Control ─────────────────────────────────────────────────
    def should_show(self) -> bool:
        return not self.completed

    def start(self):
        self.active = True
        self.step   = 0

    def _advance(self):
        self.step += 1
        if self.step >= len(STEPS):
            self._finish()

    def _finish(self):
        self.active    = False
        self.completed = True
        self._save()

    def skip(self):
        self._finish()

    # ── Input ────────────────────────────────────────────────────
    def on_key_press(self, key):
        if not self.active:
            return
        if key in (arcade.key.ENTER, arcade.key.RIGHT, arcade.key.SPACE):
            self._advance()
        elif key == arcade.key.ESCAPE:
            self.skip()

    def on_mouse_press(self, x, y):
        if not self.active:
            return
        if self._btn_next and self._point_in(x, y, self._btn_next):
            self._advance()
        elif self._btn_skip and self._point_in(x, y, self._btn_skip):
            self.skip()

    def _point_in(self, x, y, rect):
        l, r, b, t = rect
        return l <= x <= r and b <= y <= t

    # ── Draw ─────────────────────────────────────────────────────
    def draw(self, W: int, H: int, hitbox_y: float, hitbox_h: float):
        if not self.active:
            return

        step_data = STEPS[self.step]
        cx = W / 2

        # Overlay oscuro sobre la pantalla
        arcade.draw_lrbt_rectangle_filled(0, W, 0, H, (15, 20, 45, 175))

        # Dibujar highlight según el paso
        self._draw_highlight(step_data["highlight"], W, H, hitbox_y, hitbox_h)

        # Card principal con instrucciones
        card_w = min(W * 0.55, 620)
        card_h = max(int(H * 0.46), 300)
        card_cy = H * 0.44
        _rr_fill(cx, card_cy, card_w, card_h, 22, (255, 255, 255, 245))

        # Paso actual
        step_label = f"Step {self.step + 1} of {len(STEPS)}"
        arcade.draw_text(
            step_label, cx, card_cy + card_h * 0.42,
            (150, 155, 175), int(max(H * 0.016, 11)),
            anchor_x="center", bold=True
        )

        # Título
        arcade.draw_text(
            step_data["title"], cx, card_cy + card_h * 0.27,
            (25, 35, 75), int(max(H * 0.038, 22)),
            anchor_x="center", bold=True
        )

        # Separador
        arcade.draw_line(
            cx - card_w * 0.38, card_cy + card_h * 0.15,
            cx + card_w * 0.38, card_cy + card_h * 0.15,
            (210, 215, 225), 2
        )

        # Cuerpo — línea por línea
        lines = step_data["body"].split("\n")
        line_h = int(max(H * 0.036, 22))
        start_y = card_cy + card_h * 0.05
        for i, line in enumerate(lines):
            arcade.draw_text(
                line, cx, start_y - i * line_h,
                (60, 70, 100), int(max(H * 0.024, 15)),
                anchor_x="center"
            )

        # Botones
        btn_y    = card_cy - card_h * 0.38
        btn_w    = max(int(W * 0.13), 150)
        btn_h    = max(int(H * 0.058), 42)
        gap      = max(int(W * 0.02), 16)

        # NEXT / FINISH
        is_last  = (self.step == len(STEPS) - 1)
        next_lbl = "LET'S GO! ▶" if is_last else "NEXT →"
        nx = cx + gap / 2
        self._btn_next = (nx, nx + btn_w, btn_y - btn_h/2, btn_y + btn_h/2)
        _rr_fill(nx + btn_w/2, btn_y, btn_w, btn_h, btn_h/2, (240, 185, 40))
        arcade.draw_text(
            next_lbl, nx + btn_w/2, btn_y,
            (40, 30, 5), int(max(H * 0.022, 13)),
            anchor_x="center", anchor_y="center", bold=True
        )

        # SKIP (solo si no es el último paso)
        if not is_last:
            sx = cx - gap / 2 - btn_w
            self._btn_skip = (sx, sx + btn_w, btn_y - btn_h/2, btn_y + btn_h/2)
            _rr_fill(sx + btn_w/2, btn_y, btn_w, btn_h, btn_h/2, (155, 160, 175))
            arcade.draw_text(
                "SKIP", sx + btn_w/2, btn_y,
                (255, 255, 255), int(max(H * 0.022, 13)),
                anchor_x="center", anchor_y="center", bold=True
            )
        else:
            self._btn_skip = None

    def _draw_highlight(self, highlight, W, H, hitbox_y, hitbox_h):
        """Dibuja elementos de gameplay resaltados según el paso."""
        if highlight is None:
            return

        LANES = 4
        lane_width = W / LANES

        if highlight == "lanes":
            # Mostrar los 4 carriles con sus teclas
            for i in range(1, LANES):
                arcade.draw_line(i * lane_width, 0, i * lane_width, H,
                                 (200, 210, 230, 180), 2)
            for lane in range(1, LANES + 1):
                c = LANE_COLORS[lane]
                lx = (lane - 0.5) * lane_width
                # Tinte de carril
                arcade.draw_lrbt_rectangle_filled(
                    (lane-1)*lane_width, lane*lane_width, 0, H, (*c, 35))
                # Círculo grande con número de tecla
                arcade.draw_circle_filled(lx, H * 0.5, 50, (*c, 220))
                arcade.draw_circle_outline(lx, H * 0.5, 50, (255,255,255,200), 4)
                arcade.draw_text(
                    str(lane), lx, H * 0.5,
                    (255,255,255), 32,
                    anchor_x="center", anchor_y="center", bold=True
                )

        elif highlight == "hitbox":
            hy0 = hitbox_y - hitbox_h / 2
            hy1 = hitbox_y + hitbox_h / 2
            # Resaltar la zona con brillo
            arcade.draw_lrbt_rectangle_filled(0, W, hy0, hy1, (60, 200, 230, 60))
            # Borde pulsante
            arcade.draw_lrbt_rectangle_outline(10, W-10, hy0, hy1, (60, 200, 230), 4)
            # Flechas indicando la zona
            arcade.draw_text("▼  HIT ZONE  ▼", W/2, hy1 + 20,
                             (60, 200, 230), 18,
                             anchor_x="center", bold=True)

        elif highlight == "spanish":
            # Resaltar zona superior donde aparece la oración
            arcade.draw_lrbt_rectangle_filled(0, W, H*0.82, H, (60, 200, 230, 50))
            arcade.draw_text("← Spanish sentence appears here →",
                             W/2, H*0.90,
                             (255,255,255), 16,
                             anchor_x="center", bold=True)

        elif highlight == "english":
            # Resaltar zona de construcción
            arcade.draw_lrbt_rectangle_filled(0, W, H*0.76, H*0.82, (70, 130, 200, 60))
            arcade.draw_text("← Your English sentence builds here →",
                             W/2, H*0.79,
                             (255,255,255), 16,
                             anchor_x="center", bold=True)

        elif highlight == "lives":
            # Resaltar corazones
            arcade.draw_lrbt_rectangle_filled(0, W*0.35, H*0.82, H, (220, 80, 90, 50))
            arcade.draw_text("❤ ❤ ❤  Lives are here",
                             W*0.17, H*0.90,
                             (255,255,255), 16,
                             anchor_x="center", bold=True)

        elif highlight == "combo":
            # Resaltar zona de combo/score
            arcade.draw_lrbt_rectangle_filled(W*0.65, W, H*0.82, H, (240, 185, 40, 60))
            arcade.draw_text("Score & Combo →",
                             W*0.83, H*0.90,
                             (255,255,255), 16,
                             anchor_x="center", bold=True)