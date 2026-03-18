import arcade
from config import BASE_FALL_SPEED, LANES

LANE_COLORS = {
    1: (50, 200, 100),
    2: (230, 80, 100),
    3: (70, 160, 220),
    4: (230, 175, 45),
}
LANE_LETTERS = {1: "A", 2: "B", 3: "X", 4: "Y"}


def draw_rounded_rect_filled(cx, cy, w, h, radius, color):
    r = min(radius, w / 2, h / 2)
    hw, hh = w / 2, h / 2
    arcade.draw_lrbt_rectangle_filled(cx - hw, cx + hw, cy - hh + r, cy + hh - r, color)
    arcade.draw_lrbt_rectangle_filled(cx - hw + r, cx + hw - r, cy - hh, cy + hh, color)
    arcade.draw_circle_filled(cx - hw + r, cy - hh + r, r, color)
    arcade.draw_circle_filled(cx + hw - r, cy - hh + r, r, color)
    arcade.draw_circle_filled(cx - hw + r, cy + hh - r, r, color)
    arcade.draw_circle_filled(cx + hw - r, cy + hh - r, r, color)


class FallingWord(arcade.Sprite):
    def __init__(self, text, lane, is_correct):
        super().__init__()
        self.text = text
        self.is_correct = is_correct
        self.lane = lane

        window = arcade.get_window()
        W = window.width
        H = window.height

        lane_width = W / LANES
        self.cx = (lane - 0.5) * lane_width
        self.center_x = self.cx
        self.center_y = H + 50
        self.change_y = -BASE_FALL_SPEED

        # ── Cachear medidas una sola vez ──
        font_size = 20
        max_text_width = lane_width * 0.72
        while font_size > 11:
            t = arcade.Text(text, 0, 0, (30, 40, 80), font_size, bold=True)
            if t.content_width <= max_text_width:
                break
            font_size -= 1

        self._font_size = font_size
        self._card_w = max(t.content_width + 36, lane_width * 0.74)
        self._card_h = font_size + 22
        self._radius  = 12

        # ── arcade.Text cacheado (solo se actualiza center_y) ──
        self._label = arcade.Text(
            text,
            self.cx, self.center_y,
            (30, 40, 80), font_size,
            anchor_x="center", anchor_y="center",
            bold=True,
        )

    def update(self, delta_time: float = 0):
        self.center_y += self.change_y * delta_time * 60

    def draw_text(self):
        cy = self.center_y
        cx = self.cx

        # Sombra
        draw_rounded_rect_filled(cx + 2, cy - 3,
                                 self._card_w + 4, self._card_h + 4,
                                 self._radius, (160, 170, 200, 45))
        # Card blanca
        draw_rounded_rect_filled(cx, cy,
                                 self._card_w, self._card_h,
                                 self._radius, (255, 255, 255, 230))

        # Texto: actualizar posición y dibujar
        self._label.x = cx
        self._label.y = cy
        self._label.draw()