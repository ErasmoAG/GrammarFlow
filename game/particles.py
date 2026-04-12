# game/particles.py
import arcade
import random
import math


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.ambient   = []

    def spawn(self, combo: int, screen_width: int, hitbox_y: float):
        count = 36 if combo >= 6 else 18
        colors = (
            [arcade.color.ORANGE, arcade.color.YELLOW, arcade.color.CYAN]
            if combo >= 6
            else [arcade.color.CYAN, arcade.color.WHITE]
        )
        for _ in range(count):
            angle = random.uniform(0, 360)
            speed = random.uniform(2, 7 if combo >= 6 else 4)
            self.particles.append({
                "x":  random.uniform(screen_width * 0.2, screen_width * 0.8),
                "y":  hitbox_y,
                "vx": math.cos(math.radians(angle)) * speed,
                "vy": math.sin(math.radians(angle)) * speed,
                "alpha": 255,
                "color": random.choice(colors),
                "radius": random.uniform(3, 7 if combo >= 6 else 5),
            })

    def spawn_ambient(self, tier: int, W: int, H: int):
        MAX_AMBIENT = 30 if tier == 2 else 18
        if len(self.ambient) >= MAX_AMBIENT:
            return

        if tier == 1:
            count       = 2
            colors      = [(80, 220, 240), (140, 240, 255), (200, 255, 255)]
            speed_range = (0.6, 1.5)
            size_range  = (2.0, 4.0)
            life        = 160
        else:
            count       = 3
            colors      = [(255, 220, 60), (255, 180, 30), (255, 250, 120), (200, 240, 255)]
            speed_range = (0.8, 2.0)
            size_range  = (2.5, 5.0)
            life        = 180

        for _ in range(count):
            # Solo desde bordes laterales — nunca desde center
            side = random.choice(["left", "right", "bottom", "top"])
            if side == "left":
                x, y = random.uniform(0, W * 0.08), random.uniform(H * 0.1, H * 0.9)
            elif side == "right":
                x, y = random.uniform(W * 0.92, W), random.uniform(H * 0.1, H * 0.9)
            elif side == "bottom":
                x, y = random.uniform(W * 0.1, W * 0.9), random.uniform(0, H * 0.08)
            else:
                x, y = random.uniform(W * 0.1, W * 0.9), random.uniform(H * 0.92, H)

            speed = random.uniform(*speed_range)
            angle = random.uniform(0, 360)
            self.ambient.append({
                "x": x, "y": y,
                "vx": math.cos(math.radians(angle)) * speed,
                "vy": math.sin(math.radians(angle)) * speed,
                "alpha": 0,                          # fade in suave desde 0
                "life":     life,
                "max_life": life,
                "color": random.choice(colors),
                "radius": random.uniform(*size_range),
            })

    def update(self):
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] -= 0.2
            p["alpha"] -= 8
        self.particles = [p for p in self.particles if p["alpha"] > 0]

        for p in self.ambient:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            ratio = p["life"] / p["max_life"]
            # Fade in primero 30%, estable en medio, fade out último 30%
            if ratio > 0.7:
                fade = (1.0 - ratio) / 0.3
            elif ratio < 0.3:
                fade = ratio / 0.3
            else:
                fade = 1.0
            p["alpha"] = int(190 * fade)
        self.ambient = [p for p in self.ambient if p["life"] > 0]

    def draw(self):
        for p in self.ambient:
            color = (*p["color"][:3], max(0, int(p["alpha"])))
            arcade.draw_circle_filled(p["x"], p["y"], p["radius"], color)
        for p in self.particles:
            color = (*p["color"][:3], int(p["alpha"]))
            arcade.draw_circle_filled(p["x"], p["y"], p["radius"], color)

    def clear(self):
        self.particles = []
        self.ambient   = []