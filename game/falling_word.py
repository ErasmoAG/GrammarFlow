import arcade
from config import BASE_FALL_SPEED, LANES

LANE_COLORS = {
    1: (50, 200, 100),    # verde puro
    2: (230, 80, 100),    # coral/rojo
    3: (70, 160, 220),    # azul
    4: (230, 175, 45),    # amarillo
}
LANE_LETTERS = {1: "A", 2: "B", 3: "X", 4: "Y"}


def draw_rounded_rect_filled(cx, cy, w, h, radius, color):
    """Rectángulo redondeado SIN borde, solo relleno."""
    r = min(radius, w / 2, h / 2)
    hw, hh = w / 2, h / 2
    arcade.draw_lrbt_rectangle_filled(cx - hw + r, cx + hw - r, cy - hh, cy + hh, color)
    arcade.draw_lrbt_rectangle_filled(cx - hw, cx + hw, cy - hh + r, cy + hh - r, color)
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
        self.center_x = (lane - 0.5) * lane_width
        self.center_y = H + 50
        self.change_y = -BASE_FALL_SPEED

    def update(self, delta_time: float = 0):
        self.center_y += self.change_y * delta_time * 60

    def draw_text(self):
        window = arcade.get_window()
        W = window.width
        lane_width = W / LANES
        cx = (self.lane - 0.5) * lane_width

        font_size = 20  # más pequeño
        max_text_width = lane_width * 0.72

        while font_size > 11:
            test_text = arcade.Text(self.text, 0, 0, (30, 40, 80), font_size, bold=True)
            if test_text.content_width <= max_text_width:
                break
            font_size -= 1

        card_w = max(test_text.content_width + 36, lane_width * 0.74)
        card_h = font_size + 22
        radius = 12

        # Sombra (desplazada, sin borde)
        draw_rounded_rect_filled(cx + 2, self.center_y - 3,
                                 card_w + 4, card_h + 4, radius,
                                 (160, 170, 200, 45))

        # Card blanca sin borde
        draw_rounded_rect_filled(cx, self.center_y,
                                 card_w, card_h, radius,
                                 (255, 255, 255, 230))

        # Texto navy
        arcade.draw_text(
            self.text, cx, self.center_y,
            (30, 40, 80), font_size,
            anchor_x="center", anchor_y="center",
            bold=True,
        )