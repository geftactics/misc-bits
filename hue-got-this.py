import pygame
import random
import math

# needs 'pip3 install pygame'

pygame.init()


window_width = 400
window_height = 300
window = pygame.display.set_mode((window_width, window_height))
pygame.display.set_caption('Hue Got This!') 


white = (255, 255, 255)
black = (0, 0, 0)

def generate_random_color():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return (r, g, b)

def hex_to_rgb(hex_value):
    hex_value = hex_value.lstrip('#')
    return tuple(int(hex_value[i:i+2], 16) for i in (0, 2, 4))

def calculate_distance(color1, color2):
    return math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)))

def display_color(color):
    window.fill(color)
    pygame.display.update()

def draw_text(text, font, color, surface, x, y, bg_color=None):
    textobj = font.render(text, True, color, bg_color)
    textrect = textobj.get_rect()
    textrect.center = (x, y)
    surface.blit(textobj, textrect)

def main():
    font = pygame.font.Font(None, 36)
    clock = pygame.time.Clock()

    player1_score = 0
    player2_score = 0

    running = True
    while running:
        actual_color = generate_random_color()
        display_color(actual_color)

        player1_guess = ""
        player2_guess = ""
        input_phase = True
        player_turn = 1

        while input_phase:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    input_phase = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if player_turn == 1 and len(player1_guess) == 6:
                            player_turn = 2
                        elif player_turn == 2 and len(player2_guess) == 6:
                            input_phase = False
                    elif event.key == pygame.K_BACKSPACE:
                        if player_turn == 1:
                            player1_guess = player1_guess[:-1]
                        else:
                            player2_guess = player2_guess[:-1]
                    else:
                        char = event.unicode.upper()
                        if char in "0123456789ABCDEF":
                            if player_turn == 1 and len(player1_guess) < 6:
                                player1_guess += char
                            elif player_turn == 2 and len(player2_guess) < 6:
                                player2_guess += char

            window.fill(white)
            display_color(actual_color)
            draw_text(f"Player {player_turn}, enter your HEX guess:", font, black, window, window_width // 2, 50)
            if player_turn == 1:
                draw_text(player1_guess, font, black, window, window_width // 2, 100)
            else:
                draw_text(player2_guess, font, black, window, window_width // 2, 100)
            
            pygame.display.update()
            clock.tick(30)

        if not running:
            break

        player1_rgb = hex_to_rgb(player1_guess)
        player2_rgb = hex_to_rgb(player2_guess)

        distance_player1 = calculate_distance(actual_color, player1_rgb)
        distance_player2 = calculate_distance(actual_color, player2_rgb)

        if distance_player1 < distance_player2:
            player1_score += 1
            winner_text = "Player 1 wins!"
        elif distance_player2 < distance_player1:
            player2_score += 1
            winner_text = "Player 2 wins!"
        else:
            winner_text = "It's a tie!"

        window.fill(white)
        draw_text(f"Actual color was: #{''.join(f'{c:02X}' for c in actual_color)}", font, black, window, window_width // 2, 50, actual_color)
        draw_text(f"Player 1: {player1_guess} (Dist: {distance_player1:.2f})", font, black, window, window_width // 2, 100, player1_rgb)
        draw_text(f"Player 2: {player2_guess} (Dist: {distance_player2:.2f})", font, black, window, window_width // 2, 150, player2_rgb)
        draw_text(winner_text, font, black, window, window_width // 2, 200)
        draw_text(f"Score - Player 1: {player1_score} | Player 2: {player2_score}", font, black, window, window_width // 2, 250)
        draw_text("Press ENTER for next round", font, black, window, window_width // 2, 275)
        pygame.display.update()

        result_phase = True
        while result_phase:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    result_phase = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        result_phase = False

        if not running:
            break

    pygame.quit()

if __name__ == "__main__":
    main()
