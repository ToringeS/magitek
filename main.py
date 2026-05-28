"""Entry point: pygame init, top-level loop, scene switching."""

import sys

import pygame

import config
from battle import BattleScene


def main() -> int:
    pygame.init()
    pygame.mixer.init()
    try:
        screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H))
        pygame.display.set_caption(config.TITLE)
        pygame.mixer.music.load(config.MUSIC_FILE)
        pygame.mixer.music.set_volume(config.MUSIC_VOLUME)
        pygame.mixer.music.play(-1)
        clock = pygame.time.Clock()

        scene = BattleScene()
        running = True
        while running:
            dt = clock.tick(config.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    scene.handle_event(event)

            scene.update(dt)
            scene.draw(screen)
            pygame.display.flip()

            if scene.done:
                running = False
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
