import socket
import threading
import json
import pygame
import time

DISCOVERY_PORT = 50001
TCP_PORT = 50000

# -------------------------------------------------
# Discover rooms
# -------------------------------------------------
def discover_rooms(timeout=1.5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.4)

    found = []
    start = time.time()

    while time.time() - start < timeout:
        sock.sendto(b"DISCOVER_ROOM", ("<broadcast>", DISCOVERY_PORT))
        try:
            data, addr = sock.recvfrom(1024)
            info = json.loads(data.decode())
            found.append(info)
        except:
            pass

    return found


# -------------------------------------------------
# Road background (generated ONCE)
# -------------------------------------------------
def create_road_background(width, height):
    bg = pygame.Surface((width, height))

    # Colors
    field_color = (40, 120, 40)
    road_color = (50, 50, 50)
    stripe_color = (220, 220, 220)

    # Fill fields
    bg.fill(field_color)

    # Road dimensions
    road_width = int(width * 0.55)
    road_x = (width - road_width) // 2

    # Draw road
    pygame.draw.rect(bg, road_color, (road_x, 0, road_width, height))

    # Lane stripes
    stripe_width = 6
    stripe_height = 30
    stripe_gap = 30

    center_x = width // 2 - stripe_width // 2

    for y in range(0, height, stripe_height + stripe_gap):
        pygame.draw.rect(
            bg,
            stripe_color,
            (center_x, y, stripe_width, stripe_height)
        )

    return bg.convert()


# -------------------------------------------------
# Client networking
# -------------------------------------------------
class Client:
    def __init__(self):
        self.sock = None
        self.players = []
        self.running = True
        self.id = None

    def connect(self, host):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, TCP_PORT))
        threading.Thread(target=self.recv_loop, daemon=True).start()

    def recv_loop(self):
        buf = b""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    msg = json.loads(line.decode())
                    if msg["type"] == "welcome":
                        self.id = msg["id"]
                    elif msg["type"] == "state":
                        self.players = msg["players"]
            except:
                break

    def send_input(self, dx, dy):
        msg = json.dumps({"dx": dx, "dy": dy}) + "\n"
        try:
            self.sock.sendall(msg.encode())
        except:
            pass


# -------------------------------------------------
# Pygame initialization
# -------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((1000, 700))
pygame.display.set_caption("PatchFest Multiplayer Racer")

clock = pygame.time.Clock()

font = pygame.font.Font(None, 40)
fps_font = pygame.font.Font(None, 24)

WIDTH, HEIGHT = screen.get_size()

# Create road background ONCE
background = create_road_background(WIDTH, HEIGHT)


# -------------------------------------------------
# Networking setup
# -------------------------------------------------
client = Client()

rooms = discover_rooms()
if rooms:
    print("Found rooms:", rooms)
    client.connect(rooms[0]["host"])
else:
    print("No rooms found.")


# -------------------------------------------------
# Main game loop
# -------------------------------------------------
running = True
while running:
    clock.tick(60)

    dx = dy = 0

    # ---- Events ----
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    # ---- Input ----
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        dx = -5
    if keys[pygame.K_RIGHT]:
        dx = 5
    if keys[pygame.K_UP]:
        dy = -5
    if keys[pygame.K_DOWN]:
        dy = 5

    client.send_input(dx, dy)

    # ---- Draw ----
    screen.blit(background, (0, 0))

    instruction_text = font.render(
        "Use Arrow Keys to Move",
        True,
        (255, 255, 255)
    )
    screen.blit(instruction_text, (650, 30))

    for p in client.players:
        pygame.draw.rect(
            screen,
            (0, 255, 0),
            (p["x"], p["y"], 40, 40)
        )

    fps = int(clock.get_fps())
    fps_text = fps_font.render(
        f"FPS: {fps}",
        False,   # AA disabled for crisp HUD text
        (255, 255, 0)
    )
    screen.blit(fps_text, (10, 10))

    pygame.display.flip()


# -------------------------------------------------
# Cleanup
# -------------------------------------------------
client.running = False
pygame.quit()