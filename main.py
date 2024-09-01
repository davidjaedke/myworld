import pygame
import sys
import random
import time
import configparser
import os

# Pygame initialisieren
pygame.init()

# Fenstergröße definieren
window_size = (1024, 768)
screen = pygame.display.set_mode(window_size)
pygame.display.set_caption("Aufbauspiel")

# Schriftart initialisieren
font = pygame.font.SysFont(None, 36)

# Fullscreen-Toggle-Variable
fullscreen = False

# Spielfigur laden
player_image = pygame.image.load("pics/figur.png")
player_rect = player_image.get_rect()

# Baum-, Brunnen-, Reh- und Wolf-Bilder laden
tree_image = pygame.image.load("pics/baum.png")
well_image = pygame.image.load("pics/brunnen.png")
deer_image = pygame.image.load("pics/reh.png")
wolf_image = pygame.image.load("pics/wolf.png")

# Configparser für die INI-Datei
config = configparser.ConfigParser()

# Pfad zur Speicherdatei
save_file = "save.ini"

# Inventar initialisieren
inventory = {
    "Gesundheit": 100,
    "Wasser": 100,
    "Nahrung": 100,
    "Holz": 100
}

# Bäume, Brunnen, Rehe und Wolf zufällig auf der Karte platzieren, oder aus INI-Datei laden
trees = []
wells = []
deer = []
wolf = {"pos": None, "direction": random.choice(["left", "right", "up", "down"]), "avoid_steps": 0}

if os.path.exists(save_file):
    config.read(save_file)
    if config.has_section("Inventory"):
        for key in inventory.keys():
            inventory[key] = int(config.get("Inventory", key))
    if config.has_section("Trees"):
        for key, value in config.items("Trees"):
            x, y = map(int, value.split(","))
            trees.append((x, y))
    if config.has_section("Wells"):
        for key, value in config.items("Wells"):
            x, y = map(int, value.split(","))
            wells.append((x, y))
    if config.has_section("Deer"):
        for key, value in config.items("Deer"):
            x, y = map(int, value.split(","))
            deer.append({"pos": (x, y), "direction": random.choice(["left", "right", "up", "down"])})
    if config.has_section("Wolf") and config.has_option("Wolf", "pos"):
        wolf_pos = config.get("Wolf", "pos")
        wolf["pos"] = tuple(map(int, wolf_pos.split(",")))

# Initialposition des Wolfs setzen, falls noch nicht gesetzt
if wolf["pos"] is None:
    wolf["pos"] = (random.randint(0, 1600 - wolf_image.get_width()), random.randint(0, 1200 - wolf_image.get_height()))

# Startposition der Spielfigur
player_pos = [100, 100]
player_speed = 5

# Map-Größe
map_size = (1600, 1200)

# Kamera-Offset (für die Darstellung des sichtbaren Bereichs)
camera_offset = [0, 0]

# Zoomfaktor initialisieren
zoom_level = 1.0
zoom_increment = 0.1  # wie viel pro Tastendruck gezoomt wird

# Inventar anzeigen oder ausblenden
show_inventory = False

# Variablen zum Anzeigen des "H", "W" und "J"
show_H = False
show_W = False
show_J = False

# Aktueller Baum, Brunnen oder Reh, mit dem die Figur kollidiert
collided_tree_index = -1
collided_well_index = -1
collided_deer_index = -1

# Timer für das Hinzufügen neuer Bäume, Brunnen und Rehe
tree_check_timer = time.time() + 5  # Erste Überprüfung nach 5 Sekunden
well_check_timer = time.time() + 5  # Erste Überprüfung nach 5 Sekunden
deer_check_timer = time.time() + 5  # Erste Überprüfung nach 5 Sekunden

def draw_dashed_rect(surface, color, rect, width=1, dash_length=10):
    """Zeichnet ein gestricheltes Rechteck."""
    x1, y1, x2, y2 = int(rect[0]), int(rect[1]), int(rect[0] + rect[2]), int(rect[1] + rect[3])
    
    for x in range(x1, x2, dash_length * 2):
        pygame.draw.line(surface, color, (x, y1), (x + dash_length, y1), width)
        pygame.draw.line(surface, color, (x, y2), (x + dash_length, y2), width)
    for y in range(y1, y2, dash_length * 2):
        pygame.draw.line(surface, color, (x1, y), (x1, y + dash_length), width)
        pygame.draw.line(surface, color, (x2, y), (x2, y + dash_length), width)

def apply_zoom(image, zoom):
    """Wendet den Zoom auf ein Bild an und gibt das skalierte Bild zurück."""
    size = image.get_size()
    scaled_size = (int(size[0] * zoom), int(size[1] * zoom))
    return pygame.transform.scale(image, scaled_size)

def draw_inventory(surface, inventory, show_all=False):
    """Zeichnet das Inventar oben auf den Bildschirm."""
    y_offset = 10
    if show_all:
        items_to_display = inventory.items()
    else:
        items_to_display = []

    for key, value in items_to_display:
        text = f"{key}: {value}"
        text_surface = font.render(text, True, (0, 0, 0))
        surface.blit(text_surface, (10, y_offset))
        y_offset += 40

    # "Inventar [i]" Text hinzufügen, wenn das Inventar ausgeblendet ist
    if not show_all:
        text_surface = font.render("Inventar [i]", True, (0, 0, 0))
        surface.blit(text_surface, (10, y_offset))

def check_collision(rect, objects, object_image):
    """Überprüft, ob ein Objekt mit einem anderen Objekt (Baum, Brunnen, Reh oder Wolf) kollidiert."""
    for index, obj in enumerate(objects):
        obj_rect = pygame.Rect(obj[0], obj[1], object_image.get_width(), object_image.get_height())
        if rect.colliderect(obj_rect):
            return index
    return -1

def move_deer(deer):
    """Bewegt die Rehe auf der Karte basierend auf ihrer aktuellen Richtung."""
    speed = 1  # Langsame Bewegung
    for d in deer:
        x, y = d["pos"]
        direction = d["direction"]

        if direction == "left":
            x -= speed
        elif direction == "right":
            x += speed
        elif direction == "up":
            y -= speed
        elif direction == "down":
            y += speed

        # Rehe bleiben innerhalb der Kartenbegrenzung
        x = max(0, min(x, map_size[0] - deer_image.get_width()))
        y = max(0, min(y, map_size[1] - deer_image.get_height()))

        # Kollision mit Bäumen, Brunnen und der Spielfigur vermeiden
        deer_rect = pygame.Rect(x, y, deer_image.get_width(), deer_image.get_height())
        if any(deer_rect.colliderect(pygame.Rect(tree[0], tree[1], tree_image.get_width(), tree_image.get_height())) for tree in trees) or \
           any(deer_rect.colliderect(pygame.Rect(well[0], well[1], well_image.get_width(), well_image.get_height())) for well in wells) or \
           deer_rect.colliderect(player_rect):
            d["direction"] = random.choice(["left", "right", "up", "down"])  # Richtung ändern
        else:
            d["pos"] = (x, y)  # Position aktualisieren

        # Zufällig die Richtung ändern
        if random.random() < 0.01:  # 1% Chance pro Frame
            d["direction"] = random.choice(["left", "right", "up", "down"])

def move_wolf(wolf):
    """Bewegt den Wolf auf der Karte, jagt Rehe und verfolgt die Spielfigur."""
    speed = 2  # Der Wolf ist schneller als die Rehe
    x, y = wolf["pos"]
    direction = wolf["direction"]

    # Wenn der Wolf im Ausweichmodus ist, setze die Schritte zum Ausweichen fort
    if wolf["avoid_steps"] > 0:
        wolf["avoid_steps"] -= 1
    else:
        # Jagd nach Rehen, wenn der Wolf nicht ausweicht
        if deer:
            target_deer = min(deer, key=lambda d: (d["pos"][0] - x) ** 2 + (d["pos"][1] - y) ** 2)
            if target_deer["pos"][0] > x:
                x += speed
                direction = "right"
            elif target_deer["pos"][0] < x:
                x -= speed
                direction = "left"
            if target_deer["pos"][1] > y:
                y += speed
                direction = "down"
            elif target_deer["pos"][1] < y:
                y -= speed
                direction = "up"

    # Wolf bleibt innerhalb der Kartenbegrenzung
    x = max(0, min(x, map_size[0] - wolf_image.get_width()))
    y = max(0, min(y, map_size[1] - wolf_image.get_height()))

    wolf_rect = pygame.Rect(x, y, wolf_image.get_width(), wolf_image.get_height())

    # Kollision mit Bäumen, Brunnen oder der Spielfigur vermeiden
    if any(wolf_rect.colliderect(pygame.Rect(tree[0], tree[1], tree_image.get_width(), tree_image.get_height())) for tree in trees) or \
       any(wolf_rect.colliderect(pygame.Rect(well[0], well[1], well_image.get_width(), well_image.get_height())) for well in wells) or \
       wolf_rect.colliderect(player_rect):

        # Wolf geht rückwärts zur vorherigen Position
        x, y = wolf["pos"]

        # Versuche, einen Weg um das Hindernis herum zu finden, indem die Richtung geändert wird
        if direction in ["left", "right"]:
            # Wenn in horizontaler Richtung blockiert, versuche vertikal zu gehen
            direction = random.choice(["up", "down"])
        elif direction in ["up", "down"]:
            # Wenn in vertikaler Richtung blockiert, versuche horizontal zu gehen
            direction = random.choice(["left", "right"])

        # Setze die Schritte für das großräumige Ausweichen
        wolf["avoid_steps"] = random.randint(30, 50)

        # Aktualisiere die Position
        if direction == "left":
            x -= speed
        elif direction == "right":
            x += speed
        elif direction == "up":
            y -= speed
        elif direction == "down":
            y += speed

        # Stelle sicher, dass der Wolf innerhalb der Kartenbegrenzung bleibt
        x = max(0, min(x, map_size[0] - wolf_image.get_width()))
        y = max(0, min(y, map_size[1] - wolf_image.get_height()))

    # Kollision mit Reh prüfen
    wolf["pos"] = (x, y)
    wolf["direction"] = direction

    collided_deer_index = check_collision(wolf_rect, [d["pos"] for d in deer], deer_image)
    if collided_deer_index != -1:
        del deer[collided_deer_index]  # Reh verschwindet

    # Kollision mit der Spielfigur prüfen
    if wolf_rect.colliderect(player_rect):
        inventory["Gesundheit"] -= 1  # Gesundheit verringern

def add_new_tree(trees):
    """Fügt einen neuen Baum zufällig auf der Karte hinzu."""
    while len(trees) < 10:
        x = random.randint(0, 1600 - tree_image.get_width())
        y = random.randint(0, 1200 - tree_image.get_height())
        new_tree_rect = pygame.Rect(x, y, tree_image.get_width(), tree_image.get_height())
        if not any(new_tree_rect.colliderect(pygame.Rect(tree[0], tree[1], tree_image.get_width(), tree_image.get_height())) for tree in trees):
            trees.append((x, y))
            break

def add_new_well(wells):
    """Fügt einen neuen Brunnen zufällig auf der Karte hinzu."""
    while len(wells) < 5:  # Maximal 5 Brunnen
        x = random.randint(0, 1600 - well_image.get_width())
        y = random.randint(0, 1200 - well_image.get_height())
        new_well_rect = pygame.Rect(x, y, well_image.get_width(), well_image.get_height())
        if not any(new_well_rect.colliderect(pygame.Rect(well[0], well[1], well_image.get_width(), well_image.get_height())) for well in wells):
            wells.append((x, y))
            break

def add_new_deer(deer):
    """Fügt ein neues Reh zufällig auf der Karte hinzu."""
    while len(deer) < 5:  # Maximal 5 Rehe
        x = random.randint(0, 1600 - deer_image.get_width())
        y = random.randint(0, 1200 - deer_image.get_height())
        deer.append({"pos": (x, y), "direction": random.choice(["left", "right", "up", "down"])})

def save_game():
    """Speichert das Inventar und die Positionen der Bäume, Brunnen, Rehe und des Wolfs in einer INI-Datei."""
    config["Inventory"] = {key: str(value) for key, value in inventory.items()}
    config["Trees"] = {f"Tree{i}": f"{x},{y}" for i, (x, y) in enumerate(trees)}
    config["Wells"] = {f"Well{i}": f"{x},{y}" for i, (x, y) in enumerate(wells)}
    config["Deer"] = {f"Deer{i}": f"{x},{y}" for i, (x, y) in enumerate([d["pos"] for d in deer])}
    config["Wolf"] = {"pos": f"{wolf['pos'][0]},{wolf['pos'][1]}"}
    with open(save_file, "w") as configfile:
        config.write(configfile)

# Spiel-Loop
running = True
while running:
    # Ereignisse abfragen
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game()  # Spielstand speichern, wenn das Spiel geschlossen wird
            running = False
        elif event.type == pygame.KEYDOWN:
            # Fullscreen umschalten
            if event.key == pygame.K_f:
                fullscreen = not fullscreen
                if fullscreen:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    window_size = screen.get_size()
                else:
                    screen = pygame.display.set_mode((1024, 768))
                    window_size = (1024, 768)
            # Zoom steuern
            elif event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                zoom_level += zoom_increment
            elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                zoom_level = max(0.1, zoom_level - zoom_increment)  # Minimum-Zoomfaktor, um Invertierung zu verhindern
            # Inventar ein-/ausblenden
            elif event.key == pygame.K_i:
                show_inventory = not show_inventory
            # Baum fällen
            elif event.key == pygame.K_h and show_H and collided_tree_index != -1:
                del trees[collided_tree_index]
                inventory["Holz"] += 10
                show_H = False
                collided_tree_index = -1
            # Wasser holen und Brunnen entfernen
            elif event.key == pygame.K_w and show_W and collided_well_index != -1:
                del wells[collided_well_index]
                inventory["Wasser"] += 10
                show_W = False
                collided_well_index = -1
            # Nahrung sammeln und Reh entfernen
            elif event.key == pygame.K_j and show_J and collided_deer_index != -1:
                del deer[collided_deer_index]
                inventory["Nahrung"] += 10
                show_J = False
                collided_deer_index = -1
            # Spiel mit ESC-Taste beenden
            elif event.key == pygame.K_ESCAPE:
                save_game()  # Spielstand speichern
                pygame.quit()  # Pygame beenden
                sys.exit()  # Das Programm beenden

    # Alte Position speichern, um bei Kollision zurücksetzen zu können
    old_pos = player_pos.copy()

    # Tasten abfragen
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player_pos[0] -= player_speed
    if keys[pygame.K_RIGHT]:
        player_pos[0] += player_speed
    if keys[pygame.K_UP]:
        player_pos[1] -= player_speed
    if keys[pygame.K_DOWN]:
        player_pos[1] += player_speed

    # Begrenzung der Spielfigur an den Map-Rändern
    player_pos[0] = max(0, min(player_pos[0], map_size[0] - player_rect.width))
    player_pos[1] = max(0, min(player_pos[1], map_size[1] - player_rect.height))

    # Spielfigur-Rechteck aktualisieren
    player_rect.topleft = player_pos

    # Kollision mit Bäumen prüfen
    collided_tree_index = check_collision(player_rect, trees, tree_image)
    if collided_tree_index != -1:
        show_H = True
        # Wenn Kollision erkannt wird, setze die Position auf die alte zurück
        player_pos = old_pos
        player_rect.topleft = player_pos
    else:
        show_H = False

    # Kollision mit Brunnen prüfen
    collided_well_index = check_collision(player_rect, wells, well_image)
    if collided_well_index != -1:
        show_W = True
        # Wenn Kollision erkannt wird, setze die Position auf die alte zurück
        player_pos = old_pos
        player_rect.topleft = player_pos
    else:
        show_W = False

    # Kollision mit Rehen prüfen
    collided_deer_index = check_collision(player_rect, [d["pos"] for d in deer], deer_image)
    if collided_deer_index != -1:
        show_J = True
        # Wenn Kollision erkannt wird, setze die Position auf die alte zurück
        player_pos = old_pos
        player_rect.topleft = player_pos
    else:
        show_J = False

    # Rehe bewegen
    move_deer(deer)

    # Wolf bewegen
    move_wolf(wolf)

    # Alle 5 Sekunden überprüfen, ob neue Bäume, Brunnen oder Rehe hinzugefügt werden müssen
    if time.time() >= tree_check_timer:
        if len(trees) < 10:
            add_new_tree(trees)
        tree_check_timer = time.time() + 5  # Nächste Überprüfung in 5 Sekunden

    if time.time() >= well_check_timer:
        if len(wells) < 5:
            add_new_well(wells)
        well_check_timer = time.time() + 5  # Nächste Überprüfung in 5 Sekunden

    if time.time() >= deer_check_timer:
        if len(deer) < 5:
            add_new_deer(deer)
        deer_check_timer = time.time() + 5  # Nächste Überprüfung in 5 Sekunden

    # Kamera-Offset anpassen, damit die Spielfigur immer in der Mitte bleibt
    camera_offset[0] = player_pos[0] - window_size[0] // 2 / zoom_level
    camera_offset[1] = player_pos[1] - window_size[1] // 2 / zoom_level

    # Bildschirm füllen
    screen.fill((255, 255, 255))

    # Map zeichnen und zoomen
    zoomed_map_size = (int(map_size[0] * zoom_level), int(map_size[1] * zoom_level))
    zoomed_map = pygame.Surface(zoomed_map_size)
    zoomed_map.fill((0, 255, 0))
    screen.blit(zoomed_map, (-int(camera_offset[0] * zoom_level), -int(camera_offset[1] * zoom_level)))

    # Gestrichelten Map-Rahmen zeichnen
    draw_dashed_rect(screen, (0, 0, 0), (-int(camera_offset[0] * zoom_level), -int(camera_offset[1] * zoom_level), zoomed_map_size[0], zoomed_map_size[1]), 5, 10)

    # Bäume zeichnen und zoomen
    for tree in trees:
        zoomed_tree_image = apply_zoom(tree_image, zoom_level)
        screen.blit(zoomed_tree_image, (int(tree[0] * zoom_level - camera_offset[0] * zoom_level), int(tree[1] * zoom_level - camera_offset[1] * zoom_level)))

    # Brunnen zeichnen und zoomen
    for well in wells:
        zoomed_well_image = apply_zoom(well_image, zoom_level)
        screen.blit(zoomed_well_image, (int(well[0] * zoom_level - camera_offset[0] * zoom_level), int(well[1] * zoom_level - camera_offset[1] * zoom_level)))

    # Rehe zeichnen und zoomen
    for d in deer:
        zoomed_deer_image = apply_zoom(deer_image, zoom_level)
        screen.blit(zoomed_deer_image, (int(d["pos"][0] * zoom_level - camera_offset[0] * zoom_level), int(d["pos"][1] * zoom_level - camera_offset[1] * zoom_level)))

    # Wolf zeichnen und zoomen
    zoomed_wolf_image = apply_zoom(wolf_image, zoom_level)
    screen.blit(zoomed_wolf_image, (int(wolf["pos"][0] * zoom_level - camera_offset[0] * zoom_level), int(wolf["pos"][1] * zoom_level - camera_offset[1] * zoom_level)))

    # Spielfigur zeichnen und zoomen
    zoomed_player_image = apply_zoom(player_image, zoom_level)
    screen.blit(zoomed_player_image, (int(player_pos[0] * zoom_level - camera_offset[0] * zoom_level), int(player_pos[1] * zoom_level - camera_offset[1] * zoom_level)))

    # "H" anzeigen, wenn die Spielfigur mit einem Baum kollidiert
    if show_H:
        text_surface = font.render("H", True, (255, 0, 0))
        screen.blit(text_surface, (int(player_pos[0] * zoom_level - camera_offset[0] * zoom_level), int(player_pos[1] * zoom_level - 50 - camera_offset[1] * zoom_level)))

    # "W" anzeigen, wenn die Spielfigur mit einem Brunnen kollidiert
    if show_W:
        text_surface = font.render("W", True, (0, 0, 255))
        screen.blit(text_surface, (int(player_pos[0] * zoom_level - camera_offset[0] * zoom_level), int(player_pos[1] * zoom_level - 50 - camera_offset[1] * zoom_level)))

    # "J" anzeigen, wenn die Spielfigur mit einem Reh kollidiert
    if show_J:
        text_surface = font.render("J", True, (0, 128, 0))
        screen.blit(text_surface, (int(player_pos[0] * zoom_level - camera_offset[0] * zoom_level), int(player_pos[1] * zoom_level - 50 - camera_offset[1] * zoom_level)))

    # Inventar zeichnen
    draw_inventory(screen, inventory, show_all=show_inventory)

    # Bildschirm aktualisieren
    pygame.display.flip()

    # Frame-Rate setzen
    pygame.time.Clock().tick(60)

# Pygame beenden
pygame.quit()
sys.exit()
