import arcade
from config import BASE_FALL_SPEED, LANES


class FallingWord(arcade.Sprite):
    def __init__(self, text, lane, is_correct):
        super().__init__()

        self.text = text
        self.is_correct = is_correct
        self.lane = lane

        # Obtener tamaño actual de ventana (fullscreen compatible)
        window = arcade.get_window()
        W = window.width
        H = window.height

        # Calcular ancho real del carril
        lane_width = W / LANES

        # Centro del carril dinámico
        self.center_x = (lane - 0.5) * lane_width
        self.center_y = H + 50

        # Velocidad base (normalizada con delta_time)
        self.change_y = -BASE_FALL_SPEED

    def update(self, delta_time: float = 0):
        # Movimiento normalizado para 60fps
        self.center_y += self.change_y * delta_time * 60

    def draw_text(self):
        # Obtener tamaño actual de ventana
        window = arcade.get_window()
        W = window.width

        # Recalcular centro dinámico del carril
        lane_width = W / LANES
        cx = (self.lane - 0.5) * lane_width

        # Tamaño base más grande
        font_size = 28

        # Máximo ancho permitido dentro del carril
        max_text_width = lane_width * 0.85

        # Ajuste automático si el texto es muy largo
        while font_size > 14:
            test_text = arcade.Text(
                self.text,
                0,
                0,
                arcade.color.WHITE,
                font_size,
                bold=True
            )
            if test_text.content_width <= max_text_width:
                break
            font_size -= 1

        # Dibujar centrado
        arcade.draw_text(
            self.text,
            cx,
            self.center_y,
            arcade.color.WHITE,
            font_size,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
