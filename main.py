import math
import random
import sys

import pygame

# Initialization
pygame.init()
width, height = 1280, 720
levelWidth = 4200
fps = 60
gravity = 2400
jumpForce = 900
coyoteTime = 0.14
jumpBuffer = 0.16
walkSpeed = 240
runSpeed = 340
PLAYER_JUMP = 900
PLAYER_SPEED = 240
PLAYER_RUN_SPEED = 340
# Player sprite size (increased from 42x80 to 60x100)
playerSize = (60, 100)  # Width and height of the player sprite

# Hitbox settings (smaller than the sprite for better gameplay)
# These are the same as before to maintain consistent hitbox size
PLAYER_HITBOX_OFFSET_X = 9  # Pixels from left/right (scaled up proportionally)
PLAYER_HITBOX_OFFSET_TOP = 15  # Pixels from top (scaled up proportionally)
PLAYER_HITBOX_OFFSET_BOTTOM = 6  # Pixels from bottom (scaled up proportionally)

def get_player_hitbox(x, y):
    """Calculate the player's hitbox based on position and offsets."""
    return pygame.Rect(
        x + PLAYER_HITBOX_OFFSET_X,
        y + PLAYER_HITBOX_OFFSET_TOP,
        playerSize[0] - (PLAYER_HITBOX_OFFSET_X * 2),
        playerSize[1] - PLAYER_HITBOX_OFFSET_TOP - PLAYER_HITBOX_OFFSET_BOTTOM
    )

backgroundColor = (8, 14, 22)
playerColor = (150, 230, 255)
playerGlow = (40, 120, 140)
enemyColor = (40, 40, 50)
droneColor = (80, 110, 130)
stealthBarColor = (60, 200, 180)
alertColor = (220, 80, 70)
grassColor = (25, 70, 50)
bushColor = (35, 80, 55)
logColor = (70, 50, 30)
rockColor = (55, 65, 75)
rescueColor = (200, 255, 180)
exitColor = (60, 200, 120)
orbColor = (180, 220, 255)
orbGlowColor = (100, 180, 255)
orbCoreColor = (220, 240, 255)

hidingSpotTemplates = [
    {"size": (110, 70), "strength": 0.3, "color": bushColor, "type": "bush", "solid": False},
    {"size": (120, 80), "strength": 0.2, "color": bushColor, "type": "bush", "solid": False},
    {"size": (140, 80), "strength": 0.18, "color": bushColor, "type": "bush", "solid": False},
    {"size": (150, 80), "strength": 0.2, "color": bushColor, "type": "bush", "solid": False},
]

runFrameCount = 16
attackFrameCount = 7
runAnimFps = 18
attackAnimFps = 16
# Increase attack hitbox size proportionally
attackWidth = 160  # Increased from 110
attackHeight = 100  # Increased from 70
attackCooldown = 0.5
attackActiveFrame = 3
hurtFrameCount = 4
hurtAnimFps = 8
orbCount = 4
enemyTargetCount = 5
bushSheetColumns = 3
bushSheetRows = 3

# Enemy animation constants
enemyWalkingFrameCount = 9
enemyDeathFrameCount = 8
enemyWalkAnimFps = 12
enemyDeathAnimFps = 10
guardSize = (42, 80)
droneSize = (48, 48)

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Whispers of the Canopy")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 26)
bigFont = pygame.font.SysFont("arial", 54)
smallFont = pygame.font.SysFont("arial", 20)


def loadFrames(path, frameCount):
    sheet = pygame.image.load(path).convert_alpha()
    frameWidth = sheet.get_width() // max(1, frameCount)
    frames = []
    targetSize = (playerSize[0], playerSize[1])
    for index in range(frameCount):
        frameSurf = sheet.subsurface(pygame.Rect(index * frameWidth, 0, frameWidth, sheet.get_height()))
        scaledSurf = pygame.transform.smoothscale(frameSurf, targetSize)
        frames.append(scaledSurf)
    return {
        "right": frames,
        "left": [pygame.transform.flip(frame, True, False) for frame in frames],
    }


def loadEnemyFrames(path, frameCount, targetSize):
    """Load enemy frames with custom target size."""
    try:
        sheet = pygame.image.load(path).convert_alpha()
        frameWidth = sheet.get_width() // max(1, frameCount)
        frames = []
        for index in range(frameCount):
            frameSurf = sheet.subsurface(pygame.Rect(index * frameWidth, 0, frameWidth, sheet.get_height()))
            scaledSurf = pygame.transform.smoothscale(frameSurf, targetSize)
            frames.append(scaledSurf)
        return {
            "right": frames,
            "left": [pygame.transform.flip(frame, True, False) for frame in frames],
        }
    except Exception:
        return None


def safeLoadFrames(path, frameCount):
    try:
        return loadFrames(path, frameCount)
    except Exception:
        return None


def removeWhitePixels(surface, tolerance=4):
    cleaned = surface.copy().convert_alpha()
    width, height = cleaned.get_size()
    threshold = 255 - tolerance
    for x in range(width):
        for y in range(height):
            r, g, b, a = cleaned.get_at((x, y))
            if r >= threshold and g >= threshold and b >= threshold:
                cleaned.set_at((x, y), (r, g, b, 0))
    return cleaned


def loadBushSprites(path, columns=3, rows=3):
    try:
        sheet = pygame.image.load(path).convert()
    except Exception:
        return []
    sheet.set_colorkey((255, 255, 255))
    columns = max(1, columns)
    rows = max(1, rows)
    tileWidth = sheet.get_width() // columns
    tileHeight = sheet.get_height() // rows
    offsetX = (sheet.get_width() - tileWidth * columns) // 2
    offsetY = (sheet.get_height() - tileHeight * rows) // 2
    frames = []
    for row in range(rows):
        for col in range(columns):
            rect = pygame.Rect(offsetX + col * tileWidth, offsetY + row * tileHeight, tileWidth, tileHeight)
            frame = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            frames.append(removeWhitePixels(frame))
    return frames


def scaleBushSprite(width, height, rng):
    if not bushSprites:
        return None
    baseSprite = rng.choice(bushSprites)
    return pygame.transform.scale(baseSprite, (width, height)).convert_alpha()


def loadAnimalSprites(path, targetSize=(24, 24)):
    """Load animal sprites from a sprite sheet or single image."""
    try:
        sheet = pygame.image.load(path).convert_alpha()
        sheetWidth = sheet.get_width()
        sheetHeight = sheet.get_height()
        
        # For 128x128, check if it looks like a sprite sheet (has visible content in grid cells)
        # Otherwise treat as single image
        if sheetWidth == 128 and sheetHeight == 128:
            # Try extracting as 4x4 sprite sheet first
            columns = 4
            rows = 4
            tileWidth = 32
            tileHeight = 32
            sprites = []
            spritesWithContent = 0
            
            # Extract all sprites from the grid
            for row in range(rows):
                for col in range(columns):
                    x = col * tileWidth
                    y = row * tileHeight
                    # Extract this tile from the sheet
                    tileRect = pygame.Rect(x, y, tileWidth, tileHeight)
                    tileSurface = pygame.Surface((tileWidth, tileHeight), pygame.SRCALPHA)
                    tileSurface.blit(sheet, (0, 0), tileRect)
                    
                    # Quick check: sample a few pixels to see if there's content
                    hasContent = False
                    for sx in [tileWidth // 4, tileWidth // 2, 3 * tileWidth // 4]:
                        for sy in [tileHeight // 4, tileHeight // 2, 3 * tileHeight // 4]:
                            if sx < tileWidth and sy < tileHeight:
                                r, g, b, a = tileSurface.get_at((sx, sy))
                                if a > 50:  # Has substantial opacity
                                    hasContent = True
                                    spritesWithContent += 1
                                    break
                        if hasContent:
                            break
                    
                    # Scale to target size and add to list
                    scaled = pygame.transform.smoothscale(tileSurface, targetSize)
                    sprites.append(scaled)
            
            # If we found content in multiple tiles (at least 4), it's likely a sprite sheet
            # Otherwise, treat the whole image as a single sprite
            if spritesWithContent >= 4:
                return sprites
            else:
                # Treat as single image - scale the whole thing
                scaled = pygame.transform.smoothscale(sheet, targetSize)
                return [scaled]
        
        # For any other size, treat as single image
        scaled = pygame.transform.smoothscale(sheet, targetSize)
        return [scaled]
    except Exception:
        # If loading fails, return empty list (fallback to circle will be used)
        return []


playerRunFrames = safeLoadFrames("assets/RUN.png", runFrameCount)
playerAttackFrames = safeLoadFrames("assets/ATTACK.png", attackFrameCount)
playerHurtFrames = safeLoadFrames("assets/HURT.png", hurtFrameCount)
bushSprites = loadBushSprites("assets/BUSH.png", bushSheetColumns, bushSheetRows)

# Enemy sprites
enemyWalkingFrames = loadEnemyFrames("assets/EnemyWalking.png", enemyWalkingFrameCount, guardSize)
enemyDeathFrames = loadEnemyFrames("assets/EnemyDeath.png", enemyDeathFrameCount, guardSize)

# Orb settings
orbSize = 20
orbGlowSize = 35
orbPulseSpeed = 3.0


def computePlayerHitbox():
    offsets = {"right": (0, 0), "left": (0, 0)}
    hitboxWidth, hitboxHeight = playerSize
    baseFrames = playerRunFrames or playerAttackFrames or playerHurtFrames
    if baseFrames:
        sample = baseFrames.get("right") or baseFrames.get("left")
        if sample:
            rect = sample[0].get_bounding_rect()
            if rect.width > 0 and rect.height > 0:
                hitboxWidth, hitboxHeight = rect.width, rect.height
            offsets["right"] = (rect.x, rect.y)
        mirror = baseFrames.get("left")
        if mirror:
            rect = mirror[0].get_bounding_rect()
            offsets["left"] = (rect.x, rect.y)
        elif baseFrames.get("right"):
            rightSample = baseFrames["right"][0]
            rect = rightSample.get_bounding_rect()
            offsets["left"] = (rightSample.get_width() - rect.right, rect.y)
    return (hitboxWidth, hitboxHeight), offsets


playerHitboxSize, playerSpriteOffsets = computePlayerHitbox()


def makePlatforms(rng):
    floorRect = pygame.Rect(0, 640, levelWidth, 120)
    mainPlatforms = [floorRect]

    currentX = 140
    currentY = rng.randint(480, 560)
    maxX = levelWidth - 420

    while currentX < maxX:
        width = rng.randint(170, 260)
        mainPlatforms.append(pygame.Rect(int(currentX), int(currentY), width, 18))
        gap = rng.randint(90, 150)
        currentX += width + gap
        currentY = max(380, min(600, currentY + rng.randint(-60, 60)))

    landingWidth = 280
    landingY = max(380, min(580, currentY))
    landingX = levelWidth - landingWidth - 120
    mainPlatforms.append(pygame.Rect(landingX, landingY, landingWidth, 18))

    for _ in range(3):
        base = rng.choice(mainPlatforms[1:])  # skip floor
        width = rng.randint(130, 190)
        x = base.centerx + rng.randint(-120, 120) - width // 2
        x = max(80, min(levelWidth - width - 80, x))
        y = max(300, base.top - rng.randint(70, 130))
        mainPlatforms.append(pygame.Rect(int(x), int(y), width, 18))

    return mainPlatforms


def makeHidingSpots(rng, platforms):
    spots = []
    count = rng.randint(8, 12)

    def placeBushOnSurface(width, height):
        candidates = [p for p in platforms if p.width >= width + 20]
        if not candidates:
            candidates = platforms[:]
        for _ in range(10):
            base = rng.choice(candidates)
            minX = base.left + 5
            maxX = base.right - width - 5
            if maxX <= minX:
                continue
            x = rng.randint(int(minX), int(maxX))
            y = base.top - height
            return pygame.Rect(x, y, width, height)
        floorRect = platforms[0]
        fallbackX = floorRect.left + 10
        return pygame.Rect(fallbackX, floorRect.top - height, width, height)

    for _ in range(count):
        template = rng.choice(hidingSpotTemplates)
        width, height = template["size"]
        rect = None
        if template["type"] == "bush":
            rect = placeBushOnSurface(width, height)
            rect.y = min(rect.y, 640 - height)
        if rect is None:
            maxY = max(520, 640 - height)
            rect = pygame.Rect(
                rng.randint(60, levelWidth - width - 60),
                rng.randint(520, maxY),
                width,
                height,
            )
        sprite = scaleBushSprite(rect.width, rect.height, rng) if template["type"] == "bush" else None
        spots.append(
            {
                "rect": rect,
                "strength": template["strength"],
                "color": template["color"],
                "type": template["type"],
                "solid": template["solid"],
                "sprite": sprite,
            }
        )
    return spots


def makeOrbs(rng, platforms):
    orbs = []
    perches = [p for p in platforms if p.height <= 20 and p.width > 40 and p.top <= 620]
    perches = perches or [platforms[0]]
    attempts = 0

    while len(orbs) < orbCount and attempts < orbCount * 4:
        attempts += 1
        platform = rng.choice(perches)
        left = platform.left + 10
        right = platform.right - 40
        if right <= left:
            continue
        x = rng.randint(left, right)
        y = platform.top - orbSize - 5
        orbs.append({
            "rect": pygame.Rect(x, y, orbSize * 2, orbSize * 2),
            "rescued": False,
            "pulsePhase": rng.uniform(0, math.tau),
        })

    return orbs


def makeEnemies(rng, platforms):
    enemies = []
    perches = [p for p in platforms if p.height <= 20 and p.width > 80]
    attempts = 0

    while len(enemies) < enemyTargetCount and attempts < enemyTargetCount * 6:
        attempts += 1
        isGuard = rng.random() < 0.65
        if isGuard and perches:
            platform = rng.choice(perches)
            width, height = 42, 80
            minX = platform.left
            maxX = platform.right - width
            if maxX <= minX:
                continue
            x = rng.randint(minX, maxX)
            y = platform.top - height
            roam = rng.randint(140, min(420, platform.width + 200))
            pathLeft = max(0, x - roam // 2)
            pathRight = min(levelWidth, pathLeft + roam)
            pathLeft = max(0, pathRight - roam)
            maxPos = pathRight - width
            if maxPos <= pathLeft:
                continue
            x = max(pathLeft, min(x, maxPos))
            speed = rng.randint(60, 110)
            vision = (rng.randint(260, 330), rng.randint(150, 200))
            enemyType = "guard"
        else:
            width, height = 48, 48
            x = rng.randint(100, levelWidth - width - 100)
            y = rng.randint(320, 460)
            roam = rng.randint(220, 420)
            pathLeft = max(0, x - roam // 2)
            pathRight = min(levelWidth, pathLeft + roam)
            pathLeft = max(0, pathRight - roam)
            maxPos = pathRight - width
            if maxPos <= pathLeft:
                continue
            x = max(pathLeft, min(x, maxPos))
            speed = rng.randint(110, 160)
            vision = (rng.randint(200, 280), rng.randint(130, 180))
            enemyType = "drone"

        enemies.append(
            {
                "rect": pygame.Rect(x, y, width, height),
                "path": (pathLeft, pathRight),
                "speed": speed,
                "dir": 1 if rng.random() < 0.5 else -1,
                "vision": vision,
                "type": enemyType,
                "active": True,
                "animTime": rng.uniform(0, 1.0 / enemyWalkAnimFps),
                "animFrame": 0,
                "deathAnimTime": 0.0,
                "deathAnimFrame": 0,
            }
        )

    return enemies


def makeTutorialLevel(rng):
    floorRect = pygame.Rect(0, 640, levelWidth, 120)
    platforms = [
        floorRect,
        pygame.Rect(200, 560, 180, 18),
        pygame.Rect(520, 520, 200, 18),
        pygame.Rect(860, 500, 220, 18),
        pygame.Rect(1180, 470, 220, 18),
        pygame.Rect(1500, 520, 220, 18),
    ]

    def bush(rect, strength=0.25):
        return {
            "rect": rect,
            "strength": strength,
            "color": bushColor,
            "type": "bush",
            "solid": False,
            "sprite": scaleBushSprite(rect.width, rect.height, rng),
        }

    hidingSpots = [
        bush(pygame.Rect(120, 580, 140, 70), 0.25),
        bush(pygame.Rect(460, 540, 150, 70), 0.3),
        bush(pygame.Rect(1020, 500, 150, 70), 0.28),
    ]

    orbs = [
        {"rect": pygame.Rect(580, 460, orbSize * 2, orbSize * 2), "rescued": False, "pulsePhase": 0.0},
        {"rect": pygame.Rect(1250, 410, orbSize * 2, orbSize * 2), "rescued": False, "pulsePhase": math.pi},
    ]
    
    enemies = [
        {
            "rect": pygame.Rect(900, 440, 42, 80),
            "path": (850, 1150),
            "speed": 70,
            "dir": 1,
            "vision": (260, 150),
            "type": "guard",
            "active": True,
            "animTime": 0.0,
            "animFrame": 0,
            "deathAnimTime": 0.0,
            "deathAnimFrame": 0,
        }
    ]

    exitRect = pygame.Rect(1650, 380, 90, 220)
    tutorialHints = [
        {"text": "Use A/D to move and SPACE to jump", "pos": (50, 90)},
        {"text": "Press S to crouch in bushes to stay hidden", "pos": (320, 180)},
        {"text": "Collect the glowing orbs, then head to the exit", "pos": (520, 120)},
        {"text": "Left click to attack if you need to fight", "pos": (760, 60)},
    ]

    return {
        "platforms": platforms,
        "hidingSpots": hidingSpots,
        "orbs": orbs,
        "enemies": enemies,
        "exitRect": exitRect,
        "tutorialHints": tutorialHints,
    }


def resetWorld(seed=None, tutorial=False):
    rng = random.Random(seed)
    # Position player on the ground
    playerX = 80
    # The floor is at y=640, and we want the player's feet to be at this position
    # Set player Y position to place their feet at y=640
    playerY = 640 - playerSize[1]  # This positions the bottom of the sprite at y=640
    playerRect = get_player_hitbox(playerX, playerY)
    
    # Adjust for any remaining offset to ensure the player is exactly on the ground
    ground_level = 640
    player_bottom = playerRect.bottom
    playerY -= (player_bottom - ground_level)
    playerRect = get_player_hitbox(playerX, playerY)

    if tutorial:
        levelData = makeTutorialLevel(rng)
    else:
        platforms = makePlatforms(rng)
        hidingSpots = makeHidingSpots(rng, platforms)
        orbs = makeOrbs(rng, platforms)
        enemies = makeEnemies(rng, platforms)
        levelData = {
            "platforms": platforms,
            "hidingSpots": hidingSpots,
            "orbs": orbs,
            "enemies": enemies,
            "exitRect": pygame.Rect(levelWidth - 160, 420, 90, 220),
            "tutorialHints": [],
        }

    return {
        "playerRect": playerRect,
        "playerPos": pygame.Vector2(playerRect.x, playerRect.y),
        "playerVel": pygame.Vector2(0, 0),
        "platforms": levelData["platforms"],
        "hidingSpots": levelData["hidingSpots"],
        "orbs": levelData["orbs"],
        "enemies": levelData["enemies"],
        "exitRect": levelData["exitRect"],
        "visibility": 35.0,
        "alertMeter": 0.0,
        "rescued": 0,
        "cameraX": 0.0,
        "onGround": False,
        "coyoteTimer": 0.0,
        "jumpBuffer": 0.0,
        "animFrame": 0,
        "animTime": 0.0,
        "facing": 1,
        "attacking": False,
        "attackCooldown": 0.0,
        "attackRect": None,
        "attackAnimFrame": 0,
        "attackAnimTime": 0.0,
        "caught": False,
        "win": False,
        "flashAmount": 0.0,
        "particles": [],
        "tutorialHints": levelData.get("tutorialHints", []),
        "isTutorial": tutorial,
    }


def lineBlocked(start, end, blockers):
    return any(block.clipline(start, end) for block in blockers)


def pointInPoly(point, polygon):
    px, py = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        ix, iy = polygon[i]
        jx, jy = polygon[j]
        intersect = ((iy > py) != (jy > py)) and (
            px < (jx - ix) * (py - iy) / (jy - iy + 0.0001) + ix
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def buildVisionCone(enemy):
    rect = enemy["rect"]
    facing = 1 if enemy["dir"] >= 0 else -1
    eyeX = rect.centerx
    eyeY = rect.top + 20 if enemy["type"] == "guard" else rect.centery
    reach, spread = enemy["vision"]
    tip = (eyeX + facing * reach, eyeY - 30)
    upper = (eyeX + facing * (reach * 0.6), eyeY - spread * 0.4)
    lower = (eyeX + facing * (reach * 0.6), eyeY + spread * 0.4)
    return [(eyeX, eyeY), upper, tip, lower]


def updateParticles(world, dt):
    for particle in world["particles"]:
        particle["pos"][0] += particle["dir"][0] * 60 * dt
        particle["pos"][1] += particle["dir"][1] * 60 * dt
        particle["life"] -= dt
    world["particles"] = [p for p in world["particles"] if p["life"] > 0]


def spawnParticles(world, rect):
    for _ in range(8):
        angle = random.uniform(0, math.tau)
        world["particles"].append(
            {
                "pos": [rect.centerx, rect.centery],
                "dir": [math.cos(angle), math.sin(angle)],
                "life": random.uniform(0.4, 0.8),
            }
        )


def updatePlayState(world, keys, events, dt):
    # Input handling
    world["jumpBuffer"] = max(0.0, world["jumpBuffer"] - dt)
    world["coyoteTimer"] = max(0.0, world["coyoteTimer"] - dt)
    world["attackCooldown"] = max(0.0, world["attackCooldown"] - dt)
    world["attackRect"] = None

    moveDir = 0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        moveDir -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        moveDir += 1
    crouching = keys[pygame.K_s] or keys[pygame.K_DOWN]
    running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
    jumpPressed = any(evt.type == pygame.KEYDOWN and evt.key == pygame.K_SPACE for evt in events)
    attackPressed = any(evt.type == pygame.MOUSEBUTTONDOWN and evt.button == 1 for evt in events)
    if jumpPressed:
        world["jumpBuffer"] = jumpBuffer

    # Physics / movement
    moveSpeed = runSpeed if running else walkSpeed
    if crouching:
        moveSpeed *= 0.6
    world["playerVel"].x = moveDir * moveSpeed
    if moveDir == 0:
        world["playerVel"].x *= 0.7
    if moveDir > 0:
        world["facing"] = 1
    elif moveDir < 0:
        world["facing"] = -1

    if world["jumpBuffer"] > 0 and (world["onGround"] or world["coyoteTimer"] > 0):
        world["playerVel"].y = -jumpForce
        world["onGround"] = False
        world["coyoteTimer"] = 0
        world["jumpBuffer"] = 0

    world["playerVel"].y += gravity * dt
    world["playerPos"].x += world["playerVel"].x * dt
    world["playerRect"].x = int(world["playerPos"].x)

    for platform in world["platforms"]:
        if world["playerRect"].colliderect(platform):
            if world["playerVel"].x > 0:
                world["playerRect"].right = platform.left
            elif world["playerVel"].x < 0:
                world["playerRect"].left = platform.right
            world["playerPos"].x = world["playerRect"].x

    world["playerPos"].y += world["playerVel"].y * dt
    world["playerRect"].y = int(world["playerPos"].y)
    world["onGround"] = False

    for platform in world["platforms"]:
        if world["playerRect"].colliderect(platform):
            if world["playerVel"].y > 0:
                world["playerRect"].bottom = platform.top
                world["onGround"] = True
                world["playerVel"].y = 0
            elif world["playerVel"].y < 0:
                world["playerRect"].top = platform.bottom
                world["playerVel"].y = 0
            world["playerPos"].y = world["playerRect"].y

    if world["onGround"]:
        world["coyoteTimer"] = coyoteTime

    # Handle attack input and animation
    if attackPressed and not world["attacking"] and world["attackCooldown"] <= 0:
        world["attacking"] = True
        world["attackCooldown"] = attackCooldown
        world["attackAnimTime"] = 0.0
        world["attackAnimFrame"] = 0
        
    # Update attack animation if attacking
    if world["attacking"]:
        world["attackAnimTime"] += dt
        world["attackAnimFrame"] = int(world["attackAnimTime"] * attackAnimFps)
        
        # Create attack hitbox when on the active frame
        if world["attackAnimFrame"] == attackActiveFrame and world["attackCooldown"] > attackCooldown * 0.8:
            attackX = world["playerRect"].x + (world["playerRect"].width if world["facing"] > 0 else -attackWidth)
            world["attackRect"] = pygame.Rect(
                attackX,
                world["playerRect"].y + (world["playerRect"].height - attackHeight) // 2,
                attackWidth,
                attackHeight
            )
        else:
            world["attackRect"] = None
            
        # End attack animation when complete
        if world["attackAnimTime"] >= attackFrameCount / attackAnimFps:
            world["attacking"] = False
            world["attackAnimTime"] = 0
            world["attackAnimFrame"] = 0
            world["attackRect"] = None

    horizontalSpeed = abs(world["playerVel"].x)
    movingHorizontally = horizontalSpeed > 60

    if playerRunFrames:
        totalFrames = len(playerRunFrames["right"]) or 1
        if movingHorizontally:
            world["animTime"] += dt
            world["animFrame"] = int(world["animTime"] * runAnimFps) % totalFrames
        else:
            world["animTime"] = 0.0
            world["animFrame"] = 0
    else:
        world["animTime"] = 0.0
        world["animFrame"] = 0

    if world["attacking"]:
        totalAttackFrames = len(playerAttackFrames["right"]) if playerAttackFrames else attackFrameCount
        world["attackAnimTime"] += dt
        currentFrame = int(world["attackAnimTime"] * attackAnimFps)
        if currentFrame >= totalAttackFrames:
            world["attacking"] = False
            world["attackAnimTime"] = 0.0
            world["attackAnimFrame"] = 0
        else:
            world["attackAnimFrame"] = currentFrame
    else:
        world["attackAnimTime"] = 0.0
        world["attackAnimFrame"] = 0

    # Stealth and detection logic - ONLY BUSHES work for hiding
    playerHidden = False
    hidingStrength = 1.0
    for spot in world["hidingSpots"]:
        if spot.get("type") == "bush" and world["playerRect"].colliderect(spot["rect"]):
            playerHidden = True
            hidingStrength = min(hidingStrength, spot["strength"])

    targetVisibility = 85
    if crouching:
        targetVisibility = 60
    if playerHidden:
        targetVisibility = 20 + 60 * hidingStrength

    speedBonus = min(abs(world["playerVel"].x) / runSpeed * 30, 30)
    if not world["onGround"]:
        speedBonus += 10
    if moveDir == 0:
        speedBonus *= 0.4
    targetVisibility += speedBonus

    world["visibility"] += (targetVisibility - world["visibility"]) * 4 * dt
    world["visibility"] = max(5, min(100, world["visibility"]))

    playerCenter = world["playerRect"].center
    cameraGoal = world["playerRect"].centerx - width // 2
    cameraGoal = max(0, min(levelWidth - width, cameraGoal))
    world["cameraX"] += (cameraGoal - world["cameraX"]) * 2.5 * dt

    attackActive = world["attacking"] and world["attackAnimFrame"] >= attackActiveFrame
    if attackActive:
        slashRect = pygame.Rect(0, 0, attackWidth, attackHeight)
        offset = playerHitboxSize[0] // 2 + attackWidth // 2
        slashRect.center = (world["playerRect"].centerx + world["facing"] * offset, world["playerRect"].centery)
        world["attackRect"] = slashRect

    if attackActive and world["attackRect"]:
        for enemy in world["enemies"]:
            if not enemy.get("active", True):
                continue
            if world["attackRect"].colliderect(enemy["rect"]):
                enemy["active"] = False
                enemy["cone"] = []
                enemy["deathAnimTime"] = 0.0
                enemy["deathAnimFrame"] = 0
                spawnParticles(world, enemy["rect"])

    spotted = False
    for enemy in world["enemies"]:
        if world["caught"]:
            break
        if not enemy.get("active", True):
            enemy["cone"] = []
            # Update death animation
            if enemyDeathFrames:
                enemy["deathAnimTime"] += dt
                enemy["deathAnimFrame"] = min(int(enemy["deathAnimTime"] * enemyDeathAnimFps), enemyDeathFrameCount - 1)
            continue

        # Update walking animation
        if enemyWalkingFrames:
            enemy["animTime"] += dt
            totalFrames = len(enemyWalkingFrames.get("right", [])) or 1
            enemy["animFrame"] = int(enemy["animTime"] * enemyWalkAnimFps) % totalFrames

        enemyRect = enemy["rect"]
        enemyRect.x += enemy["speed"] * enemy["dir"] * dt
        if enemyRect.left < enemy["path"][0] or enemyRect.right > enemy["path"][1]:
            enemy["dir"] *= -1
            enemyRect.x = max(enemy["path"][0], min(enemyRect.x, enemy["path"][1] - enemyRect.width))

        conePoints = buildVisionCone(enemy)
        shiftedCone = [(x, y) for x, y in conePoints]
        enemy["cone"] = shiftedCone
        inside = pointInPoly(playerCenter, shiftedCone)
        detectionRate = 0

        if inside:
            if not playerHidden:
                world["caught"] = True
                world["flashAmount"] = 1.0
                spotted = True
                break
            visibilityFactor = world["visibility"] / 100
            detectionRate += 30 * visibilityFactor
            detectionRate *= 0.4
            if crouching:
                detectionRate *= 0.6

        distance = math.hypot(enemyRect.centerx - playerCenter[0], enemyRect.centery - playerCenter[1])
        if abs(world["playerVel"].x) > walkSpeed * 0.9 and distance < 220:
            detectionRate += 20

        if detectionRate > 0:
            spotted = True
        world["alertMeter"] += detectionRate * dt

    if world["caught"]:
        world["alertMeter"] = 100
    else:
        if not spotted:
            world["alertMeter"] = max(0, world["alertMeter"] - 25 * dt)
        world["alertMeter"] = min(120, world["alertMeter"])
        if world["alertMeter"] >= 100:
            world["caught"] = True
            world["flashAmount"] = 1.0

    # Orb collection logic
    if not world["caught"]:
        for orb in world["orbs"]:
            if not orb["rescued"] and world["playerRect"].colliderect(orb["rect"]):
                orb["rescued"] = True
                world["rescued"] += 1
                spawnParticles(world, orb["rect"])

    updateParticles(world, dt)

    # Win check
    if not world["caught"] and world["rescued"] == len(world["orbs"]) and world["playerRect"].colliderect(world["exitRect"]):
        world["win"] = True

    world["flashAmount"] = max(0.0, world["flashAmount"] - dt)


def drawBackground(surface, cameraX):
    surface.fill(backgroundColor)
    for layer in range(3):
        layerColor = (10 + layer * 10, 25 + layer * 20, 20 + layer * 10)
        offset = cameraX * (0.15 * layer)
        for x in range(-200, levelWidth, 220):
            trunkX = x - offset
            pygame.draw.rect(surface, layerColor, (trunkX - cameraX, 260 + layer * 60, 30, 460))


def blitPlayerSprite(surface, sprite, world, orientation, cam):
    """Blit player sprite with safe error handling."""
    try:
        if sprite is None:
            return False
        offsetX, offsetY = playerSpriteOffsets.get(orientation, playerSpriteOffsets.get("right", (0, 0)))
        drawX = world["playerRect"].x - cam - offsetX
        drawY = world["playerRect"].y - offsetY
        # Ensure sprite is valid and coordinates are reasonable
        if sprite.get_width() > 0 and sprite.get_height() > 0:
            spriteRect = sprite.get_rect(topleft=(drawX, drawY))
            surface.blit(sprite, spriteRect)
            return True
    except (AttributeError, TypeError, pygame.error):
        pass
    return False


def drawOrb(surface, orb, cam, time):
    """Draw an orb with pulsing glow effect and visual marker."""
    if orb["rescued"]:
        return
    
    centerX = int(orb["rect"].centerx - cam)
    centerY = int(orb["rect"].centery)
    
    # Calculate pulse based on time and phase
    pulse = 0.5 + 0.5 * math.sin(time * orbPulseSpeed + orb.get("pulsePhase", 0))
    currentGlowSize = orbGlowSize * (0.8 + 0.2 * pulse)
    currentOrbSize = orbSize * (0.9 + 0.1 * pulse)
    
    # Draw outer glow (multiple layers for smooth glow effect)
    glowAlpha = int(80 + 40 * pulse)
    for i in range(3, 0, -1):
        glowRadius = int(currentGlowSize * (i / 3))
        if glowRadius > 0:
            glowSurface = pygame.Surface((glowRadius * 2 + 4, glowRadius * 2 + 4), pygame.SRCALPHA)
            alpha = int(glowAlpha * (i / 3) * 0.6)
            glowCenter = glowRadius + 2
            pygame.draw.circle(glowSurface, (*orbGlowColor, alpha), (glowCenter, glowCenter), glowRadius)
            surface.blit(glowSurface, (centerX - glowCenter, centerY - glowCenter))
    
    # Draw orb core (bright center)
    coreRadius = max(3, int(currentOrbSize * 0.6))
    pygame.draw.circle(surface, orbCoreColor, (centerX, centerY), coreRadius)
    
    # Draw orb outer ring
    ringRadius = int(currentOrbSize)
    if ringRadius > 0:
        pygame.draw.circle(surface, orbColor, (centerX, centerY), ringRadius, 2)
    
    # Draw visual marker (arrow pointing up above orb)
    markerOffset = int(currentGlowSize * 0.7) + 20
    markerY = centerY - markerOffset
    markerAlpha = int(180 + 75 * pulse)
    
    # Draw arrow marker using a small surface
    markerSize = 30
    markerSurface = pygame.Surface((markerSize, markerSize), pygame.SRCALPHA)
    markerCenterX = markerSize // 2
    markerCenterY = markerSize // 2
    
    # Draw arrow pointing up
    arrowPoints = [
        (markerCenterX, markerCenterY - 10),
        (markerCenterX - 6, markerCenterY - 2),
        (markerCenterX + 6, markerCenterY - 2),
    ]
    pygame.draw.polygon(markerSurface, (*orbGlowColor, markerAlpha), arrowPoints)
    
    # Draw small circle at arrow base
    pygame.draw.circle(markerSurface, (*orbGlowColor, markerAlpha), (markerCenterX, markerCenterY + 2), 4)
    
    # Blit marker above the orb
    surface.blit(markerSurface, (centerX - markerCenterX, markerY - markerCenterY))


def drawGame(surface, world):
    # Rendering
    drawBackground(surface, world["cameraX"])
    cam = world["cameraX"]

    for platform in world["platforms"]:
        pygame.draw.rect(surface, (30, 40, 35), (platform.x - cam, platform.y, platform.width, platform.height))

    for spot in world["hidingSpots"]:
        sprite = spot.get("sprite")
        if sprite:
            surface.blit(sprite, (spot["rect"].x - cam, spot["rect"].y))
        else:
            pygame.draw.rect(surface, spot["color"], (spot["rect"].x - cam, spot["rect"].y, spot["rect"].width, spot["rect"].height))

    pygame.draw.rect(surface, exitColor, (world["exitRect"].x - cam, world["exitRect"].y, world["exitRect"].width, world["exitRect"].height))

    visionSurface = pygame.Surface((width, height), pygame.SRCALPHA)

    for enemy in world["enemies"]:
        rect = enemy["rect"]
        enemyActive = enemy.get("active", True)
        enemyType = enemy.get("type", "guard")
        
        # Draw enemy sprite
        spriteDrawn = False
        if not enemyActive and enemyDeathFrames:
            # Draw death animation
            deathFrames = enemyDeathFrames.get("right", []) or enemyDeathFrames.get("left", [])
            if deathFrames:
                deathFrame = min(enemy.get("deathAnimFrame", 0), len(deathFrames) - 1)
                sprite = deathFrames[deathFrame]
                orientation = "right" if enemy.get("dir", 1) >= 0 else "left"
                if orientation == "left" and "left" in enemyDeathFrames:
                    sprite = enemyDeathFrames["left"][deathFrame]
                surface.blit(sprite, (rect.x - cam, rect.y))
                spriteDrawn = True
        elif enemyActive and enemyWalkingFrames and enemyType == "guard":
            # Draw walking animation for guards
            orientation = "right" if enemy.get("dir", 1) >= 0 else "left"
            walkFrames = enemyWalkingFrames.get(orientation, [])
            if walkFrames:
                animFrame = enemy.get("animFrame", 0) % len(walkFrames)
                sprite = walkFrames[animFrame]
                surface.blit(sprite, (rect.x - cam, rect.y))
                spriteDrawn = True
        
        # Fallback to rectangle if sprite not drawn
        if not spriteDrawn:
            color = enemyColor if enemyType == "guard" else droneColor
            if not enemyActive:
                color = tuple(min(255, c + 60) for c in color)
            pygame.draw.rect(surface, color, (rect.x - cam, rect.y, rect.width, rect.height), border_radius=6)
        
        # Draw vision cone for active enemies
        if enemyActive:
            cone = enemy.get("cone")
            if cone:
                conePoints = [(x - cam, y) for x, y in cone]
                coneColor = (255, 210, 90, 60) if enemyType == "guard" else (120, 200, 255, 60)
                pygame.draw.polygon(visionSurface, coneColor, conePoints)

    surface.blit(visionSurface, (0, 0))

    # Draw orbs with pulsing glow and visual markers
    currentTime = pygame.time.get_ticks() / 1000.0
    for orb in world["orbs"]:
        drawOrb(surface, orb, cam, currentTime)

    # Draw player sprite (always draw, even if sprites fail to load)
    spriteDrawn = False
    orientation = "right" if world["facing"] >= 0 else "left"
    
    # Try to draw player sprite based on state
    try:
        if world["caught"] and playerHurtFrames:
            hurtFrames = playerHurtFrames.get(orientation, [])
            if hurtFrames and len(hurtFrames) > 0:
                animIndex = (pygame.time.get_ticks() * hurtAnimFps // 1000) % len(hurtFrames)
                sprite = hurtFrames[animIndex]
                if blitPlayerSprite(surface, sprite, world, orientation, cam):
                    spriteDrawn = True

        if not spriteDrawn and world["attacking"] and playerAttackFrames:
            attackFrames = playerAttackFrames.get(orientation, [])
            if attackFrames and len(attackFrames) > 0:
                idx = min(world["attackAnimFrame"], len(attackFrames) - 1)
                sprite = attackFrames[idx]
                if blitPlayerSprite(surface, sprite, world, orientation, cam):
                    spriteDrawn = True

        if not spriteDrawn and playerRunFrames:
            runFrames = playerRunFrames.get(orientation, [])
            if runFrames and len(runFrames) > 0:
                animFrame = world.get("animFrame", 0) % len(runFrames)
                sprite = runFrames[animFrame]
                if blitPlayerSprite(surface, sprite, world, orientation, cam):
                    spriteDrawn = True
    except (KeyError, IndexError, AttributeError, TypeError):
        # If sprite rendering fails, fall back to rectangle
        spriteDrawn = False

    # Always draw player fallback (rectangle) if sprites didn't render
    # This ensures the player is always visible, even if sprites fail
    if not spriteDrawn:
        playerX = int(world["playerRect"].x - cam)
        playerY = int(world["playerRect"].y)
        # Always draw the player rectangle, even if off-screen (pygame handles clipping)
        try:
            pygame.draw.rect(surface, playerColor, (playerX, playerY, world["playerRect"].width, world["playerRect"].height), border_radius=12)
        except (TypeError, ValueError):
            # If coordinates are invalid, draw at a safe fallback position
            pygame.draw.rect(surface, playerColor, (width // 2 - 20, height // 2 - 20, 40, 40), border_radius=12)

    for particle in world["particles"]:
        alpha = int(255 * (particle["life"]))
        pygame.draw.circle(surface, (*orbGlowColor, alpha), (int(particle["pos"][0] - cam), int(particle["pos"][1])), 3)

    stealthRect = pygame.Rect(30, 30, 280, 22)
    pygame.draw.rect(surface, (40, 50, 60), stealthRect)
    stealthFill = int(stealthRect.width * (world["visibility"] / 100))
    pygame.draw.rect(surface, stealthBarColor, (stealthRect.x, stealthRect.y, stealthFill, stealthRect.height))
    pygame.draw.rect(surface, (200, 200, 200), stealthRect, 2)

    alertRect = pygame.Rect(width - 340, 30, 300, 20)
    pygame.draw.rect(surface, (40, 30, 30), alertRect)
    alertFill = int(alertRect.width * (world["alertMeter"] / 100))
    pygame.draw.rect(surface, alertColor, (alertRect.x, alertRect.y, alertFill, alertRect.height))
    pygame.draw.rect(surface, (200, 200, 200), alertRect, 2)

    orbsText = font.render(f"Orbs collected: {world['rescued']}/{len(world['orbs'])}", True, (220, 230, 230))
    surface.blit(orbsText, (30, 65))

    hintText = smallFont.render("A/D move | SPACE jump | S hide | Left click attack | R retry", True, (170, 180, 190))
    surface.blit(hintText, (30, height - 40))

    if world["alertMeter"] > 85:
        warningSurface = pygame.Surface((width, height), pygame.SRCALPHA)
        warningSurface.fill((200, 50, 50, 50))
        surface.blit(warningSurface, (0, 0))

    if world["flashAmount"] > 0:
        flashSurface = pygame.Surface((width, height), pygame.SRCALPHA)
        flashSurface.fill((255, 80, 80, int(120 * world["flashAmount"])))
        surface.blit(flashSurface, (0, 0))

    if world.get("isTutorial"):
        for hint in world.get("tutorialHints", []):
            text = hint.get("text", "")
            pos = hint.get("pos", (40, 80))
            if not text:
                continue
            label = smallFont.render(text, True, (240, 240, 240))
            padding = 8
            bgRect = pygame.Rect(pos[0] - padding, pos[1] - padding, label.get_width() + padding * 2, label.get_height() + padding * 2)
            pygame.draw.rect(surface, (15, 25, 35), bgRect, border_radius=6)
            surface.blit(label, pos)


def drawTitle(surface):
    drawBackground(surface, 0)
    titleText = bigFont.render("Whispers of the Canopy", True, (220, 240, 230))
    promptText = font.render("Press ENTER to start", True, (180, 190, 190))
    surface.blit(titleText, (width // 2 - titleText.get_width() // 2, height // 2 - 80))
    surface.blit(promptText, (width // 2 - promptText.get_width() // 2, height // 2))


def drawCaught(surface):
    caughtText = bigFont.render("Caught!", True, (240, 120, 120))
    promptText = font.render("Press R to retry or wait for restart...", True, (230, 230, 230))
    noteText = smallFont.render("Visibility blew your cover.", True, (210, 210, 210))
    surface.blit(caughtText, (width // 2 - caughtText.get_width() // 2, height // 2 - 60))
    surface.blit(promptText, (width // 2 - promptText.get_width() // 2, height // 2))
    surface.blit(noteText, (width // 2 - noteText.get_width() // 2, height // 2 + 40))


def drawWin(surface, world):
    if world and world.get("isTutorial"):
        winText = bigFont.render("Tutorial complete!", True, (200, 255, 200))
        promptText = font.render("Press ENTER to begin the real mission", True, (230, 230, 230))
        noteText = smallFont.render("Remember: collect every orb and stay hidden.", True, (210, 220, 210))
        surface.blit(winText, (width // 2 - winText.get_width() // 2, height // 2 - 80))
        surface.blit(promptText, (width // 2 - promptText.get_width() // 2, height // 2 - 20))
        surface.blit(noteText, (width // 2 - noteText.get_width() // 2, height // 2 + 20))
    else:
        winText = bigFont.render("The forest is safe... for now", True, (200, 255, 200))
        promptText = font.render("Press ENTER to play again", True, (230, 230, 230))
        surface.blit(winText, (width // 2 - winText.get_width() // 2, height // 2 - 60))
        surface.blit(promptText, (width // 2 - promptText.get_width() // 2, height // 2))


tutorialCompleted = False
worldState = None
gameState = "title"
stateTimer = 0.0

# Game loop
while True:
    dt_raw = clock.tick(fps) / 1000.0
    # Cap delta time aggressively to prevent large jumps when window loses/gains focus
    # Maximum of 2 frames worth of time (prevents issues when clicking)
    max_dt = (1.0 / fps) * 2
    dt = min(dt_raw, max_dt)
    
    eventList = pygame.event.get()
    for event in eventList:
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keyState = pygame.key.get_pressed()

    if gameState == "title":
        if any(evt.type == pygame.KEYDOWN and evt.key == pygame.K_RETURN for evt in eventList):
            worldState = resetWorld(tutorial=not tutorialCompleted)
            gameState = "playing"
            stateTimer = 0.0
    elif gameState == "playing":
        if worldState is not None:
            updatePlayState(worldState, keyState, eventList, dt)
            if worldState["caught"]:
                gameState = "caught"
                stateTimer = 0.0
            if worldState["win"]:
                gameState = "win"
                stateTimer = 0.0
    elif gameState == "caught":
        stateTimer += dt
        restartPressed = any(evt.type == pygame.KEYDOWN and evt.key == pygame.K_r for evt in eventList)
        if restartPressed or stateTimer >= 1.8:
            worldState = resetWorld(tutorial=worldState.get("isTutorial") if worldState else False)
            gameState = "playing"
            stateTimer = 0.0
    elif gameState == "win":
        if any(evt.type == pygame.KEYDOWN and evt.key == pygame.K_RETURN for evt in eventList):
            if worldState and worldState.get("isTutorial") and not tutorialCompleted:
                tutorialCompleted = True
                worldState = resetWorld()
            else:
                worldState = resetWorld(tutorial=not tutorialCompleted)
            gameState = "playing"
            stateTimer = 0.0

    # Rendering - always render to ensure player is visible
    if gameState == "title":
        drawTitle(screen)
    else:
        if worldState is not None:
            drawGame(screen, worldState)
            if gameState == "caught":
                drawCaught(screen)
            if gameState == "win":
                drawWin(screen, worldState)
        else:
            # Fallback if worldState is None
            drawTitle(screen)

    pygame.display.flip()