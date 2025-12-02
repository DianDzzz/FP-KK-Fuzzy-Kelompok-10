# ...existing code...
import pygame
import sys
from collections import deque

# ---------- Konfigurasi ----------
GRID_W, GRID_H = 8, 6
TILE = 80
WIDTH, HEIGHT = GRID_W * TILE, GRID_H * TILE + 120   # beri ruang hasil menu
FPS = 60

MOVE_RANGE = 1
PLAYER_MAX_HP = 20
ENEMY_MAX_HP = 20
PLAYER_ATK = 2
ENEMY_ATK = 1

# Warna
WHITE = (255,255,255)
BLACK = (0,0,0)
GRAY = (200,200,200)
DARK = (40,40,40)
GREEN = (50,180,50)
RED = (200,60,60)
BLUE = (60,120,200)
YELLOW = (230,200,60)
PURPLE = (160, 80, 200)
LIGHT_BLUE = (140, 200, 255)

# ---------- Helper functions ----------
def in_bounds(x,y):
    return 0 <= x < GRID_W and 0 <= y < GRID_H

def manhattan(a,b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def bfs_reachable(start, max_dist, obstacles):
    q = deque()
    q.append((start,0))
    visited = {start}
    results = set()
    while q:
        (x,y), d = q.popleft()
        if d > max_dist:
            continue
        results.add((x,y))
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx,ny = x+dx, y+dy
            if not in_bounds(nx,ny):
                continue
            if (nx,ny) in visited:
                continue
            if (nx,ny) in obstacles:
                continue
            visited.add((nx,ny))
            q.append(((nx,ny), d+1))
    return results

# ---------- Unit & AnimatedSprite (unchanged) ----------
class Unit:
    def __init__(self, x, y, hp, atk, team):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.atk = atk
        self.team = team
        self.alive = True

    def pos(self):
        return (self.x, self.y)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

class AnimatedSprite:
    def __init__(self, image_files, size):
        self.frames = [
            pygame.transform.scale(pygame.image.load(img).convert_alpha(), size)
            for img in image_files
        ]
        self.index = 0
        self.timer = 0
        self.speed = 8

    def update(self):
        self.timer += 1
        if self.timer >= self.speed:
            self.timer = 0
            self.index = (self.index + 1) % len(self.frames)

    def get_frame(self):
        return self.frames[self.index]

# ---------- Game class with Menu ----------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Turn-Based Demo')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 22)
        self.bigfont = pygame.font.SysFont(None, 28)
        idle_frames = [
            "assets/player/idle1.png","assets/player/idle2.png","assets/player/idle3.png",
            "assets/player/idle4.png","assets/player/idle5.png","assets/player/idle6.png",
            "assets/player/idle7.png","assets/player/idle8.png",
        ]
        self.player_idle_anim = AnimatedSprite(idle_frames, (TILE+30, TILE+30))
        self.player_mana = 100

        # Menu / selection state
        self.menu_state = 'MAIN'   # MAIN -> SELECT_INFERENCE -> IN_GAME -> RESULT
        self.enemy_options = ['Zombie','Skeleton','Enderman','Boss']
        self.inference_options = ['mamdani','sugeno','tsukamoto']
        self.menu_sel_enemy = 0
        self.menu_sel_infer = 0
        self.forced_inference = None
        self.selected_enemy_index = 0
        self.result_info = {}   # store result summary

        self.reset(init_from_menu=True)

    def reset(self, init_from_menu=False):
        # Basic units
        self.player = Unit(1, GRID_H//2, PLAYER_MAX_HP, PLAYER_ATK, 'PLAYER')

        # stages fixed but start stage will be set from menu selection
        self.stages = ['Zombie', 'Skeleton', 'Enderman', 'Boss']
        self.stage_index = 0
        self.max_stages = len(self.stages)
        self.victory = False

        if not init_from_menu:
            # spawn first enemy normally
            self.spawn_enemy(self.stage_index)
            self.units = [self.player, self.enemy]
            self.turn = 'PLAYER'
            self.cursor = [0,0]
            self.mode = 'IDLE'
            self.move_targets = set()
            self.selected_target = None
            self.message = f'Starting Stage 1: {self.stages[0]}. Giliran PLAYER. Tekan M untuk move, A untuk attack, E untuk end turn.'
        else:
            # entering from menu, clear gameplay state but don't spawn until selected
            self.units = [self.player]
            self.turn = 'PLAYER'
            self.cursor = [0,0]
            self.mode = 'IDLE'
            self.move_targets = set()
            self.message = 'Menu: pilih lawan dan metode inference. Gunakan UP/DOWN, Enter untuk pilih.'

    def spawn_enemy(self, index):
        etype = self.stages[index]
        ex, ey = GRID_W-2, GRID_H//2
        if etype == 'Zombie':
            ehp, eatk, emana, erange = 20, 1, 0, 1
        elif etype == 'Skeleton':
            ehp, eatk, emana, erange = 18, 1, 0, 3
        elif etype == 'Enderman':
            ehp, eatk, emana, erange = 22, 2, 80, 1
        elif etype == 'Boss':
            ehp, eatk, emana, erange = 35, 3, 100, 2
        else:
            ehp, eatk, emana, erange = ENEMY_MAX_HP, ENEMY_ATK, 50, 1
        self.enemy = Unit(ex, ey, ehp, eatk, 'ENEMY')
        self.enemy.max_hp = ehp
        self.enemy.mana = emana
        self.enemy.range = erange
        self.enemy_type = etype
        if hasattr(self, 'player'):
            self.units = [self.player, self.enemy]
        else:
            self.units = [self.enemy]
        self.turn = 'PLAYER'
        self.mode = 'IDLE'

    def unit_at(self, pos):
        for u in self.units:
            if u.alive and u.pos() == pos:
                return u
        return None

    # --- INPUT HANDLING extended to menu ---
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # Menu input
            if self.menu_state == 'MAIN':
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP,):
                        self.menu_sel_enemy = (self.menu_sel_enemy - 1) % len(self.enemy_options)
                    elif event.key in (pygame.K_DOWN,):
                        self.menu_sel_enemy = (self.menu_sel_enemy + 1) % len(self.enemy_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        # go to inference selection
                        self.selected_enemy_index = self.menu_sel_enemy
                        self.menu_state = 'SELECT_INFER'
                        self.menu_sel_infer = 0
                        self.message = f'Pilih inference untuk {self.enemy_options[self.selected_enemy_index]}.'
                continue

            if self.menu_state == 'SELECT_INFER':
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP,):
                        self.menu_sel_infer = (self.menu_sel_infer - 1) % len(self.inference_options)
                    elif event.key in (pygame.K_DOWN,):
                        self.menu_sel_infer = (self.menu_sel_infer + 1) % len(self.inference_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        # finalize selection, start game
                        self.forced_inference = self.inference_options[self.menu_sel_infer]
                        self.stage_index = self.selected_enemy_index
                        self.spawn_enemy(self.stage_index)
                        self.units = [self.player, self.enemy]
                        self.turn = 'PLAYER'
                        self.cursor = [0,0]
                        self.mode = 'IDLE'
                        self.move_targets = set()
                        self.selected_target = None
                        self.menu_state = 'IN_GAME'
                        self.message = f'Mulai battle vs {self.enemy_type} menggunakan inference {self.forced_inference}.'
                continue

            # Gameplay input (existing behavior)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_r,):
                    # return to main menu
                    self.menu_state = 'MAIN'
                    self.reset(init_from_menu=True)
                    continue
                if event.key in (pygame.K_SPACE, pygame.K_e):
                    self.end_turn()
                if event.key in (pygame.K_m,):
                    if self.turn == 'PLAYER' and self.menu_state == 'IN_GAME':
                        self.mode = 'MOVE'
                        self.move_targets = bfs_reachable(self.player.pos(), MOVE_RANGE, {self.enemy.pos()})
                        self.message = 'Mode MOVE. Klik tile tujuan untuk memindahkan.'
                if event.key in (pygame.K_a,):
                    if self.turn == 'PLAYER' and self.menu_state == 'IN_GAME':
                        self.mode = 'ATTACK'
                        self.message = 'Mode ATTACK. Pilih petak bersebelahan untuk menyerang.'
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.confirm_action()
                dx = dy = 0
                if event.key in (pygame.K_RIGHT, pygame.K_d): dx = 1
                if event.key in (pygame.K_LEFT, pygame.K_a) and not pygame.key.get_mods() & pygame.KMOD_CTRL: dx = -1
                if event.key in (pygame.K_UP, pygame.K_w): dy = -1
                if event.key in (pygame.K_DOWN, pygame.K_s): dy = 1
                if dx or dy:
                    nx = max(0, min(GRID_W-1, self.cursor[0]+dx))
                    ny = max(0, min(GRID_H-1, self.cursor[1]+dy))
                    self.cursor = [nx, ny]

            if event.type == pygame.MOUSEBUTTONDOWN and self.menu_state == 'IN_GAME':
                mx, my = event.pos
                if event.button == 1:
                    if my < GRID_H * TILE:
                        gx = mx // TILE
                        gy = my // TILE
                        self.cursor = [gx, gy]
                        if self.turn == 'PLAYER' and self.mode in ('MOVE', 'ATTACK'):
                            self.confirm_action()
                elif event.button == 3:
                    if self.turn == 'PLAYER' and my < GRID_H * TILE:
                        gx = mx // TILE
                        gy = my // TILE
                        self.cursor = [gx, gy]
                        # right-click immediate action (attack or move)
                        if manhattan(self.player.pos(), (gx,gy)) == 1:
                            target = self.unit_at((gx,gy))
                            if target and target.team == 'ENEMY':
                                target.take_damage(self.player.atk)
                                if not target.alive:
                                    self.message = 'Serang berhasil! Musuh dikalahkan.'
                                else:
                                    self.message = f'Serang! Musuh HP: {max(0,target.hp)}.'
                                self.end_turn()
                            else:
                                self.message = 'Tidak ada musuh di petak bersebelahan untuk menyerang.'
                        elif manhattan(self.player.pos(), (gx,gy)) <= MOVE_RANGE and self.unit_at((gx,gy)) is None:
                            self.player.x, self.player.y = gx, gy
                            self.message = f'Player moved to {gx},{gy}.'
                            self.end_turn()
                        else:
                            self.message = 'Aksi tidak valid.'

    def confirm_action(self):
        if self.menu_state != 'IN_GAME': return
        cx,cy = self.cursor
        if self.turn != 'PLAYER': return
        if self.mode == 'MOVE':
            if (cx,cy) in self.move_targets and self.unit_at((cx,cy)) is None:
                self.player.x, self.player.y = cx, cy
                self.mode = 'IDLE'
                self.move_targets = set()
                self.message = f'Player moved to {cx},{cy}.'
                self.end_turn()
            else:
                self.message = 'Lokasi tidak valid untuk MOVE.'
        elif self.mode == 'ATTACK':
            target = self.unit_at((cx,cy))
            if target and target.team == 'ENEMY' and manhattan(self.player.pos(), target.pos()) == 1:
                target.take_damage(self.player.atk)
                if not target.alive:
                    self.message = f'Serang! Musuh kalah!'
                else:
                    self.message = f'Serang! Musuh HP tersisa {max(0,target.hp)}.'
                self.mode = 'IDLE'
                self.end_turn()
            else:
                self.message = 'Target tidak valid untuk ATTACK (harus bersebelahan dan musuh).'
        else:
            self.message = 'Tidak ada aksi dipilih. Tekan M atau A.'

    def end_turn(self):
        if self.menu_state != 'IN_GAME': return
        if self.turn == 'PLAYER':
            self.turn = 'ENEMY'
            self.mode = 'IDLE'
            self.move_targets = set()
            self.message = 'Giliran ENEMY.'
            # immediate enemy action
            self.enemy_action()
            # after enemy action, check results
            if not self.player.alive or not self.enemy.alive:
                # prepare result info (scores etc.)
                self.prepare_result()
                self.menu_state = 'RESULT'
            else:
                self.turn = 'PLAYER'
                self.message = 'Giliran PLAYER. Tekan M untuk move, A untuk attack, E untuk end turn.'
        else:
            self.turn = 'PLAYER'

    # --- enemy_action: now honors forced_inference if set (menu choice) ---
    def enemy_action(self):
        if not self.enemy.alive or not self.player.alive:
            return
        import fuzzy
        occupied = {u.pos() for u in self.units if u.alive}
        occupied.discard(self.enemy.pos())
        etype = getattr(self, 'enemy_type', 'Zombie')

        # 1) heal-priority
        heal_act, do_heal = getattr(fuzzy, 'heal_priority_check')(etype, self.enemy.hp, getattr(self.enemy,'mana',0))
        if do_heal:
            tgt = getattr(fuzzy, 'pick_adjacent_for_farther')(self.enemy.pos(), self.player.pos(), occupied, GRID_W, GRID_H)
            # perform heal
            if tgt and self.unit_at(tgt) is None:
                self.enemy.x, self.enemy.y = tgt
            heal_amt = max(1, int(self.enemy.max_hp * 0.25))
            self.enemy.hp = min(self.enemy.max_hp, self.enemy.hp + heal_amt)
            if hasattr(self.enemy, 'mana'):
                self.enemy.mana = max(0, getattr(self.enemy,'mana',0) - 20)
            self.message = f'{etype} melakukan HEAL (+{heal_amt}). HP sekarang {self.enemy.hp}.'
            return

        # 2) if adjacent prefer melee
        if manhattan(self.enemy.pos(), self.player.pos()) == 1:
            self.player.take_damage(self.enemy.atk)
            self.message = f'{etype} menyerang! Player HP: {max(0,self.player.hp)}.'
            return

        # 3) compute scores and pick inference
        scores = getattr(fuzzy, 'get_all_scores')(etype, self.player.hp, self.enemy.hp, 0, getattr(self.enemy,'mana',0), 5)
        # choose inference: forced menu selection wins; otherwise default mapping per-type (keeps previous behavior)
        infer_choice = self.forced_inference or ('mamdani' if etype in ('Enderman','Boss') else 'mamdani')
        # ensure valid key
        infer_choice = infer_choice if infer_choice in scores else 'mamdani'
        score = scores[infer_choice]

        # map to behavior and execute (reuse fuzzy helpers for picking tiles)
        behavior = getattr(fuzzy, 'map_fuzzy_score_to_behavior')(score, etype)

        if behavior == "RANGED_ATTACK":
            rng = getattr(self.enemy, 'range', 2)
            if manhattan(self.enemy.pos(), self.player.pos()) <= rng:
                self.player.take_damage(self.enemy.atk)
                self.message = f'{etype} melakukan serangan jarak jauh! Player HP: {max(0,self.player.hp)}.'
            else:
                # move closer
                tgt = getattr(fuzzy, 'pick_adjacent_for_closer')(self.enemy.pos(), self.player.pos(), occupied, GRID_W, GRID_H)
                if tgt:
                    self.enemy.x, self.enemy.y = tgt
                    self.message = f'{etype} bergerak mendekat ke {tgt}.'
                else:
                    self.message = f'{etype} ingin serang jarak jauh tapi target terlalu jauh.'
            return

        if behavior == "TELEPORT_CLOSE":
            # use fuzzy helper to find adjacent free tile near player
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                tx,ty = self.player.x+dx, self.player.y+dy
                if 0 <= tx < GRID_W and 0 <= ty < GRID_H and (tx,ty) not in occupied:
                    self.enemy.x, self.enemy.y = tx, ty
                    self.message = f'{etype} teleport dekat ke {(tx,ty)}.'
                    return
            self.message = f'{etype} ingin teleport dekat tapi tidak ada ruang.'
            return

        if behavior == "TELEPORT_FAR":
            tgt = getattr(fuzzy, 'pick_adjacent_for_farther')(self.enemy.pos(), self.player.pos(), occupied, GRID_W, GRID_H)
            if tgt:
                self.enemy.x, self.enemy.y = tgt
                self.message = f'{etype} teleport jauh ke {tgt}.'
            else:
                self.message = f'{etype} ingin teleport jauh tapi tidak ada ruang.'
            return

        if behavior == "MOVE_CLOSE":
            tgt = getattr(fuzzy, 'pick_adjacent_for_closer')(self.enemy.pos(), self.player.pos(), occupied, GRID_W, GRID_H)
            if tgt:
                self.enemy.x, self.enemy.y = tgt
                self.message = f'{etype} bergerak mendekat ke {tgt}.'
            else:
                self.message = f'{etype} ingin mendekat tapi tidak menemukan petak.'
            return

        if behavior == "MOVE_RETREAT":
            tgt = getattr(fuzzy, 'pick_adjacent_for_farther')(self.enemy.pos(), self.player.pos(), occupied, GRID_W, GRID_H)
            if tgt:
                self.enemy.x, self.enemy.y = tgt
                self.message = f'{etype} mundur ke {tgt}.'
            else:
                self.message = f'{etype} ingin mundur tapi tidak menemukan petak.'
            return

        self.message = f'{etype} menunggu.'


    # prepare result: gather inference scores and basic stats
    def prepare_result(self):
        import fuzzy
        etype = getattr(self, 'enemy_type', 'Unknown')
        scores = getattr(fuzzy, 'get_all_scores')(etype,
                                                  self.player.hp if self.player else 0,
                                                  self.enemy.hp if self.enemy else 0,
                                                  0, getattr(self.enemy,'mana',0), 5)
        # choose the inference that was forced in menu; default to mamdani
        selected = self.forced_inference if self.forced_inference in scores else 'mamdani'
        selected_score = float(scores.get(selected, 0.0))
        self.result_info = {
            'enemy': etype,
            'selected_inference': selected,
            'score': selected_score,
            'player_hp': self.player.hp,
            'enemy_hp': self.enemy.hp,
            'winner': 'PLAYER' if self.enemy and not self.enemy.alive else ('ENEMY' if self.player and not self.player.alive else 'DRAW')
        }

    # --- Drawing functions: menu + game + result ---
    def draw_main_menu(self):
        self.screen.fill(BLACK)
        title = self.bigfont.render('MAIN MENU - Pilih Lawan (UP/DOWN, Enter)', True, WHITE)
        self.screen.blit(title, (WIDTH//2 - 220, 20))
        for i, opt in enumerate(self.enemy_options):
            color = YELLOW if i == self.menu_sel_enemy else WHITE
            txt = self.bigfont.render(opt, True, color)
            self.screen.blit(txt, (WIDTH//2 - 60, 80 + i*36))
        hint = self.font.render('Tekan R untuk kembali kapan saja.', True, GRAY)
        self.screen.blit(hint, (8, HEIGHT-28))

    def draw_infer_menu(self):
        self.screen.fill(BLACK)
        title = self.bigfont.render(f'Pilih Inference untuk {self.enemy_options[self.selected_enemy_index]}', True, WHITE)
        self.screen.blit(title, (WIDTH//2 - 260, 20))
        for i, opt in enumerate(self.inference_options):
            color = YELLOW if i == self.menu_sel_infer else WHITE
            txt = self.bigfont.render(opt, True, color)
            self.screen.blit(txt, (WIDTH//2 - 80, 100 + i*36))
        hint = self.font.render('Enter untuk mulai. R untuk kembali.', True, GRAY)
        self.screen.blit(hint, (8, HEIGHT-28))

    def draw_result(self):
        self.screen.fill(BLACK)
        title = self.bigfont.render('Hasil Pertarungan', True, WHITE)
        self.screen.blit(title, (WIDTH//2 - 120, 16))
        if not self.result_info:
            return
        y = 72
        # show selected inference name + single numeric score
        sel = self.result_info.get('selected_inference', 'mamdani')
        sc = self.result_info.get('score', 0.0)
        txt = self.font.render(f'Inference selected: {sel}  |  Score: {sc:.1f}', True, YELLOW)
        self.screen.blit(txt, (40, y)); y += 28
        # other summary fields
        other_keys = ['enemy','player_hp','enemy_hp','winner']
        for k in other_keys:
            if k in self.result_info:
                txt = self.font.render(f'{k}: {self.result_info[k]}', True, WHITE)
                self.screen.blit(txt, (40, y)); y += 24
        hint = self.font.render('Tekan R untuk kembali ke menu utama.', True, GRAY)
        self.screen.blit(hint, (8, HEIGHT-28))

    # draw_grid, draw_units, draw_cursor, draw_ui (unchanged except small adapt)
    def draw_grid(self):
        for x in range(GRID_W):
            for y in range(GRID_H):
                rect = pygame.Rect(x*TILE, y*TILE, TILE, TILE)
                pygame.draw.rect(self.screen, GRAY, rect, 1)

    def draw_units(self):
        for u in self.units:
            if not u.alive:
                continue
            cx = u.x * TILE + TILE//2
            cy = u.y * TILE + TILE//2
            if u.team == 'PLAYER':
                self.player_idle_anim.update()
                img = self.player_idle_anim.get_frame()
                rect = img.get_rect(center=(cx, cy))
                self.screen.blit(img, rect)
            else:
                etype = getattr(self, 'enemy_type', None)
                if etype == 'Zombie':
                    ecolor = GREEN
                elif etype == 'Skeleton':
                    ecolor = WHITE
                elif etype == 'Enderman':
                    ecolor = PURPLE
                elif etype == 'Boss':
                    ecolor = LIGHT_BLUE
                else:
                    ecolor = RED
                pygame.draw.rect(self.screen, ecolor, (u.x*TILE+12, u.y*TILE+12, TILE-24, TILE-24))
            hp_ratio = max(0, u.hp) / u.max_hp
            bar_w = int(TILE * 0.8)
            bx = u.x*TILE + (TILE-bar_w)//2
            by = u.y*TILE + TILE - 12
            pygame.draw.rect(self.screen, DARK, (bx,by,bar_w,6))
            pygame.draw.rect(self.screen, GREEN, (bx,by,int(bar_w*hp_ratio),6))

    def draw_cursor(self):
        cx,cy = self.cursor
        rect = pygame.Rect(cx*TILE, cy*TILE, TILE, TILE)
        pygame.draw.rect(self.screen, YELLOW, rect, 3)
        if self.mode == 'MOVE':
            for (mx,my) in self.move_targets:
                r = pygame.Rect(mx*TILE+6, my*TILE+6, TILE-12, TILE-12)
                pygame.draw.rect(self.screen, (180,240,180), r, 2)
        if self.mode == 'ATTACK':
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx,ny = self.player.x+dx, self.player.y+dy
                if in_bounds(nx,ny) and self.unit_at((nx,ny)) and self.unit_at((nx,ny)).team == 'ENEMY':
                    r = pygame.Rect(nx*TILE+6, ny*TILE+6, TILE-12, TILE-12)
                    pygame.draw.rect(self.screen, (255,180,180), r, 2)

    def draw_ui(self):
        panel = pygame.Rect(0, GRID_H*TILE, WIDTH, 120)
        pygame.draw.rect(self.screen, DARK, panel)
        info = f'State: {self.menu_state} | Turn: {self.turn} | Mode: {self.mode} | Cursor: {self.cursor[0]},{self.cursor[1]}'
        txt = self.font.render(info, True, WHITE)
        self.screen.blit(txt, (8, GRID_H*TILE+6))
        msg = self.bigfont.render(self.message, True, YELLOW)
        self.screen.blit(msg, (8, GRID_H*TILE+30))
        if self.menu_state == 'IN_GAME' and hasattr(self, 'enemy'):
            inf = self.font.render(f'Enemy: {self.enemy_type} | Inference: {self.forced_inference}', True, WHITE)
            self.screen.blit(inf, (WIDTH-320, GRID_H*TILE+8))

    def update(self):
        if self.menu_state == 'IN_GAME':
            if not getattr(self, 'victory', False) and hasattr(self, 'enemy') and not self.enemy.alive:
                if self.stage_index < self.max_stages - 1:
                    self.stage_index += 1
                    self.spawn_enemy(self.stage_index)
                    if hasattr(self, 'player'):
                        self.player.hp = self.player.max_hp
                        self.player.alive = True
                    self.message = f'Musuh dikalahkan! Melanjutkan ke Stage {self.stage_index+1}: {self.stages[self.stage_index]}. Player HP dipulihkan.'
                else:
                    self.victory = True
                    self.message = 'SEMUA MUSUH DIKALAHKAN! Tekan R untuk restart.'
            self.player_idle_anim.update()

    def run(self):
        while True:
            self.handle_input()
            self.update()
            if self.menu_state == 'MAIN':
                self.draw_main_menu()
            elif self.menu_state == 'SELECT_INFER':
                self.draw_infer_menu()
            elif self.menu_state == 'RESULT':
                self.draw_result()
            else:
                # in-game
                self.screen.fill(BLACK)
                self.draw_grid()
                self.draw_units()
                self.draw_cursor()
                self.draw_ui()
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == '__main__':
    Game().run()