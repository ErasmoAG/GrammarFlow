# game/particles.py
import arcade
import random
import math


class ParticleSystem:
    """
    Sistema de partículas independiente.
    Se instancia en GrammarGame y se llama desde on_update y draw_gameplay.
    """

    def __init__(self):
        self.particles = []     # lista de dicts {x,y,vx,vy,alpha,color,radius}

    def spawn(self, combo: int, screen_width: int, hitbox_y: float):
        """
        Spawnea partículas en la zona de hitbox según el nivel de combo.
        Combo 3-5 → 18 partículas leves (cyan/blanco)
        Combo 6+  → 36 partículas intensas (naranja/amarillo/cyan)
        """
        count = 36 if combo >= 6 else 18
        colors = (
            [arcade.color.ORANGE, arcade.color.YELLOW, arcade.color.CYAN]
            if combo >= 6
            else [arcade.color.CYAN, arcade.color.WHITE]
        )

        for _ in range(count):
            angle = random.uniform(0, 360)
            speed = random.uniform(2, 7 if combo >= 6 else 4)
            vx = math.cos(math.radians(angle)) * speed
            vy = math.sin(math.radians(angle)) * speed
            self.particles.append({
                "x": random.uniform(screen_width * 0.2, screen_width * 0.8),
                "y": hitbox_y,
                "vx": vx,
                "vy": vy,
                "alpha": 255,
                "color": random.choice(colors),
                "radius": random.uniform(3, 7 if combo >= 6 else 5),
            })

    def update(self):
        """Mueve, aplica gravedad y decae el alpha de cada partícula."""
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] -= 0.2      # gravedad leve
            p["alpha"] -= 8     # desvanecimiento
        self.particles = [p for p in self.particles if p["alpha"] > 0]

    def draw(self):
        """Dibuja todas las partículas activas."""
        for p in self.particles:
            color = (*p["color"][:3], int(p["alpha"]))
            arcade.draw_circle_filled(p["x"], p["y"], p["radius"], color)

    def clear(self):
        """Limpia todas las partículas (útil al resetear la partida)."""
        self.particles = []