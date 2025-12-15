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
# Road background (generated once)
# -------------------------------------------------
def create_road_background(width, height):
    bg = pygame.Surface((width, height))
    field_color = (40, 120, 40)
    road_color = (50, 50, 50)
    stripe_color = (220, 220, 220)

    bg.fill(field_color)

    road_width = int(width * 0.55)
    road_x = (width - road_width) // 2
    pygame.draw.rect(bg, road_color, (road_x, 0, road_width, height))

    stripe_width = 6
    stripe_height = 30
    stripe_gap = 30
    center_x = width // 2 - stripe_width // 2

    for y in range(0, height, stripe_height + stripe_gap):
        pygame.draw.rect(bg, stripe_color, (center_x, y, stripe_width, stripe_height))

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
        self.room_code = None
        self.connection_status = "SEARCHING"

    def connect(self, host):
        self.connection_status = "CONNECTING"
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
                        self.room_code = msg.get("room_code", self.room_code)
                        self.connection_status = "CONNECTED"

                    elif msg["type"] == "state":
                        self.players = msg["players"]
            except:
                break

    def send_input(self, dx, dy):
        if self.connection_status != "CONNECTED":
            return
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
background = create_road_background(WIDTH, HEIGHT)

# -------------------------------------------------
# Networking setup
# -------------------------------------------------
client = Client()

rooms = discover_rooms()
if rooms:
    client.room_code = rooms[0].get("room_code")
    client.connect(rooms[0]["host"])
else:
    client.connection_status = "SEARCHING"

# -------------------------------------------------
# Main loop
# -------------------------------------------------
running = True
while running:
    clock.tick(60)
    dx = dy = 0

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

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

    # ---------------- DRAW ----------------
    screen.blit(background, (0, 0))

    # Cars
    CAR_W, CAR_H = 40, 60
    for p in client.players:
        rect = pygame.Rect(p["x"], p["y"], CAR_W, CAR_H)
        if p["id"] == client.id:
            pygame.draw.rect(screen, (255, 255, 0), rect.inflate(8, 8))
            pygame.draw.rect(screen, (255, 255, 255), rect, 3)
            color = (0, 200, 255)
        else:
            color = (0, 255, 0)
        pygame.draw.rect(screen, color, rect)

    # HUD
    fps = int(clock.get_fps())
    screen.blit(fps_font.render(f"FPS: {fps}", False, (255, 255, 0)), (10, 10))

    status_map = {
        "SEARCHING": "Searching for rooms...",
        "CONNECTING": "Connecting...",
        "CONNECTED": "Connected!"
    }
    screen.blit(
        fps_font.render(status_map[client.connection_status], False, (255, 255, 255)),
        (10, 35)
    )

    if client.room_code:
        screen.blit(
            fps_font.render(f"ROOM: {client.room_code}", False, (255, 255, 255)),
            (WIDTH - 150, 10)
        )

    pygame.display.flip()

# -------------------------------------------------
# Cleanup
# -------------------------------------------------
client.running = False
pygame.quit()