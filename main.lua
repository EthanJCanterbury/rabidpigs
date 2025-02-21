-- Constants
local TILE_SIZE = 32
local CHUNK_SIZE = 16
local MAP_HEIGHT = 20
local MAP_WIDTH = 1000
local CLOUD_COUNT = 5
local TREE_CHANCE = 0.2  -- Chance of tree spawning
local TREE_HEIGHT = 5    -- Height of trees in tiles

-- Cloud system
local clouds = {}
local function createCloud(minX, maxX)
    return {
        x = love.math.random(minX, maxX),
        y = love.math.random(0, 100),
        speed = love.math.random(10, 30),
        width = love.math.random(3, 6) * TILE_SIZE
    }
end

for i = 1, CLOUD_COUNT do
    clouds[i] = createCloud(0, 1000)
end

-- Font for coordinates
local pixelFont = love.graphics.newFont(16)
local PLAYER_SPEED = 200
local GRAVITY = 800
local JUMP_POWER = -400

-- Game state
local terrain = {}
local player = {
    x = 100,
    y = 0,  -- Will be set after initial terrain generation
    width = 32,
    height = 32,
    velocityX = 0,
    velocityY = 0,
    isGrounded = false
}

local camera = {
    x = 0,
    y = 0
}
local colors = {
    dirt = {0.6, 0.4, 0.2},
    grass = {0.2, 0.8, 0.2},
    player = {0.8, 0.2, 0.2},
    trunk = {0.5, 0.3, 0.1},
    leaves = {0.1, 0.5, 0.1},
    pig = {1, 0.8, 0.8}
}

local pigs = {}
local xp = 0
local PIG_SPEED = 100
local SUPER_HARD_MODE = false
local PIG_SPAWN_CHANCE = 0.01
local RED_PIG_SPAWN_CHANCE = 0.02   -- Higher chance for red pigs (1%)
local MAX_HEALTH = 5
local health = MAX_HEALTH
local INVINCIBILITY_TIME = 1
local invincibilityTimer = 0
local gameOver = false
local gameState = "intro"  -- "intro", "playing", "paused", "dead"
local survivalTime = 0
local highScore = 0
local trees = {}  -- Store tree positions and seeds: {x = x, y = y, seed = seed}

function drawButton(text, x, y, w, h)
    love.graphics.setColor(0.3, 0.3, 0.3)
    love.graphics.rectangle("fill", x, y, w, h)
    love.graphics.setColor(1, 1, 1)
    love.graphics.printf(text, x, y + h/4, w, "center")
    return x <= love.mouse.getX() and love.mouse.getX() <= x + w and
           y <= love.mouse.getY() and love.mouse.getY() <= y + h
end

-- Initialize game
function love.load()
    generateChunk(0) -- Generate initial chunk
    -- Initialize fire particle system prototype
    local particleCanvas = love.graphics.newCanvas(4, 4)
    love.graphics.setCanvas(particleCanvas)
    love.graphics.setColor(1, 0.5, 0)
    love.graphics.rectangle("fill", 0, 0, 4, 4)
    love.graphics.setCanvas()
end

function generateChunk(chunkX)
    if not terrain[chunkX] then
        terrain[chunkX] = {}
        local height = MAP_HEIGHT / 2
        if chunkX > 0 and terrain[chunkX-1] then
            local lastX = (chunkX-1) * CHUNK_SIZE + CHUNK_SIZE
            height = terrain[chunkX-1][CHUNK_SIZE].height
        end

        for x = 1, CHUNK_SIZE do
            if love.math.random() < 0.2 then  -- 20% chance to change height
                height = height + love.math.random(-1, 1)
            end
            height = math.floor(height)  -- Ensure height is a whole number
            height = math.min(math.max(height, MAP_HEIGHT/4), MAP_HEIGHT-5)

            terrain[chunkX][x] = {height = height}
            if chunkX == 0 and x == 1 then
                player.y = (height - 2) * TILE_SIZE
            end
            -- Generate trees only on grass blocks
            if x > 1 and love.math.random() < TREE_CHANCE then
                local treeX = (chunkX * CHUNK_SIZE + x - 1) * TILE_SIZE
                local treeY = (height - 1) * TILE_SIZE
                -- Check if there's enough space between trees
                local tooClose = false
                for _, tree in ipairs(trees) do
                    if math.abs(tree.x - treeX) < TILE_SIZE * 4 then
                        tooClose = true
                        break
                    end
                end
                if not tooClose then
                    table.insert(trees, {
                        x = treeX, 
                        y = treeY, 
                        seed = love.math.random(1, 10000)
                    })
                end
            end
        end
    end
end

function drawTile(type, x, y)
    if type == "dirt" then
        love.graphics.setColor(colors.dirt)
        love.graphics.rectangle("fill", x, y, TILE_SIZE, TILE_SIZE)
        -- Add some pixel details
        love.graphics.setColor(0.5, 0.3, 0.1)
        for i = 0, 3 do
            love.graphics.rectangle("fill", x + i*8, y + (i%2)*8, 4, 4)
        end
    elseif type == "grass" then
        -- Dirt base
        love.graphics.setColor(colors.dirt)
        love.graphics.rectangle("fill", x, y, TILE_SIZE, TILE_SIZE)
        -- Grass top
        love.graphics.setColor(colors.grass)
        love.graphics.rectangle("fill", x, y, TILE_SIZE, 8)
        -- Grass details
        love.graphics.setColor(0.1, 0.6, 0.1)
        for i = 0, 3 do
            love.graphics.rectangle("fill", x + i*8, y, 4, 12)
        end
    end
end

function drawPlayer(x, y)
    -- Main body
    love.graphics.setColor(colors.player)
    love.graphics.rectangle("fill", x, y, player.width, player.height)
    -- Details
    love.graphics.setColor(0.9, 0.3, 0.3)
    love.graphics.rectangle("fill", x + 8, y + 8, 16, 16)
    love.graphics.setColor(1, 1, 1)
    love.graphics.rectangle("fill", x + 12, y + 12, 4, 4)
end

function love.mousepressed(x, y, button)
    if button == 1 then  -- Left click
        if gameState == "intro" then
            local w, h = 200, 50
            local bx = love.graphics.getWidth()/2 - w/2
            local by = love.graphics.getHeight()/2 - h/2
            if drawButton("Play", bx, by, w, h) then
                gameState = "playing"
                survivalTime = 0
                health = MAX_HEALTH
                xp = 0
                pigs = {}
                player.x = 100
                player.y = 0
            end
            return
        end
        local worldX = x + camera.x
        local worldY = y
        
        -- Check for pig collision
        for i = #pigs, 1, -1 do
            local pig = pigs[i]
            if worldX >= pig.x and worldX <= pig.x + pig.width and
               worldY >= pig.y and worldY <= pig.y + pig.height then
                table.remove(pigs, i)
                xp = xp + 10
                break
            end
        end
        
        -- Check for tree collision
        for i = #trees, 1, -1 do
            local tree = trees[i]
            if worldX >= tree.x and worldX <= tree.x + TILE_SIZE * 3 and
               worldY >= tree.y - TILE_SIZE * 3 and worldY <= tree.y + TILE_SIZE * 3 then
                table.remove(trees, i)
                break
            end
        end
    end
end

function checkTreeCollision(x, y, width, height)
    for _, tree in ipairs(trees) do
        if x + width > tree.x and x < tree.x + TILE_SIZE and
           y + height > tree.y and y < tree.y + TILE_SIZE * 3 then
            return true
        end
    end
    return false
end

function spawnPig(x, y, isRed)
    local width = isRed and 96 or 32  -- 3x size for red pigs
    local height = isRed and 96 or 32
    table.insert(pigs, {
        x = x,
        y = y,
        width = width,
        height = height,
        particles = isRed and love.graphics.newParticleSystem(love.graphics.newCanvas(4, 4), 100) or nil,
        velocityX = 0,
        velocityY = 0,
        isGrounded = false,
        direction = love.math.random() < 0.5 and -1 or 1,
        moveTimer = love.math.random(1, 3),
        isRed = isRed
    })
end

function updatePig(pig, dt)
    if pig.particles then
        pig.particles:setParticleLifetime(0.2, 0.8)
        pig.particles:setLinearAcceleration(-50, -100, 50, -200)
        pig.particles:setColors(1, 0.5, 0, 1, 1, 0, 0, 0)
        pig.particles:setEmissionRate(50)
        pig.particles:update(dt)
    end
    pig.moveTimer = pig.moveTimer - dt
    if pig.moveTimer <= 0 then
        pig.direction = love.math.random() < 0.5 and -1 or 1
        pig.moveTimer = love.math.random(1, 3)
    end
    
    pig.velocityX = (SUPER_HARD_MODE and 700 or PIG_SPEED) * pig.direction
    pig.velocityY = pig.velocityY + GRAVITY * dt
    
    local newX = pig.x + pig.velocityX * dt
    local newY = pig.y + pig.velocityY * dt
    
    -- Ground collision
    local tileX = math.floor(newX / TILE_SIZE)
    local chunkX = math.floor(tileX / CHUNK_SIZE)
    local localX = (tileX % CHUNK_SIZE) + 1
    
    if terrain[chunkX] and terrain[chunkX][localX] then
        local groundHeight = terrain[chunkX][localX].height * TILE_SIZE
        if newY + pig.height > groundHeight then
            newY = groundHeight - pig.height
            pig.velocityY = 0
            pig.isGrounded = true
        else
            pig.isGrounded = false
        end
    end
    
    pig.x = newX
    pig.y = newY
end

function love.update(dt)
    if love.keyboard.isDown('escape') and gameState == "playing" then
        gameState = "paused"
    end

    if gameState ~= "playing" then
        return
    end

    survivalTime = survivalTime + dt

    if health <= 0 then
        gameState = "dead"
        if survivalTime > highScore then
            highScore = survivalTime
        end
        return
    end

    if love.keyboard.isDown('r') then
        -- Reset game
        health = MAX_HEALTH
        gameOver = false
        xp = 0
        player.x = 100
        player.y = 0
        pigs = {}
        return
    end

    if invincibilityTimer > 0 then
        invincibilityTimer = invincibilityTimer - dt
    end

    -- Check pig collision with player
    if invincibilityTimer <= 0 then
        for i = #pigs, 1, -1 do
            local pig = pigs[i]
            if pig.x < player.x + player.width and
               pig.x + pig.width > player.x and
               pig.y < player.y + player.height and
               pig.y + pig.height > player.y then
                if pig.isRed then
                    health = 0
                    gameOver = true
                else
                    health = health - 1
                    invincibilityTimer = INVINCIBILITY_TIME
                end
                table.remove(pigs, i)
                if health <= 0 then
                    gameOver = true
                end
                break
            end
        end
    end

    if love.keyboard.isDown('left') or love.keyboard.isDown('a') then
        player.velocityX = -PLAYER_SPEED
    elseif love.keyboard.isDown('right') or love.keyboard.isDown('d') then
        player.velocityX = PLAYER_SPEED
    else
        player.velocityX = 0
    end

    if (love.keyboard.isDown('space') or love.keyboard.isDown('w')) and player.isGrounded then
        player.velocityY = JUMP_POWER
        player.isGrounded = false
    end

    player.velocityY = player.velocityY + GRAVITY * dt

    local newX = player.x + player.velocityX * dt
    local newY = player.y + player.velocityY * dt

    -- Check collisions
    local function checkCollision(x, y)
        local tileX = math.floor(x / TILE_SIZE)
        local tileY = math.floor(y / TILE_SIZE)
        local chunkX = math.floor(tileX / CHUNK_SIZE)
        local localX = (tileX % CHUNK_SIZE) + 1
        
        if terrain[chunkX] and terrain[chunkX][localX] then
            local groundHeight = terrain[chunkX][localX].height * TILE_SIZE
            return y >= groundHeight
        end
        return false
    end

    player.isGrounded = false

    -- Check multiple points for vertical collision
    local checkPoints = {
        {newX + 2, newY + player.height},             -- Left foot
        {newX + player.width - 2, newY + player.height}, -- Right foot
        {newX + player.width/2, newY + player.height},   -- Middle foot
        {newX + 2, newY},                               -- Left head
        {newX + player.width - 2, newY}                 -- Right head
    }

    for _, point in ipairs(checkPoints) do
        if checkCollision(point[1], point[2]) then
            local tileX = math.floor(point[1] / TILE_SIZE)
            local chunkX = math.floor(tileX / CHUNK_SIZE)
            local localX = (tileX % CHUNK_SIZE) + 1
            if terrain[chunkX] and terrain[chunkX][localX] then
                newY = terrain[chunkX][localX].height * TILE_SIZE - player.height
                player.velocityY = 0
                player.isGrounded = true
                break
            end
        end
    end

    -- Horizontal collision with some vertical tolerance
    if checkCollision(newX, newY + player.height - 4) or 
       checkCollision(newX + player.width, newY + player.height - 4) or
       checkTreeCollision(newX, newY, player.width, player.height) then
        newX = player.x
        player.velocityX = 0
    end

    -- Keep player within map bounds
    newY = math.min(newY, (MAP_HEIGHT-1) * TILE_SIZE - player.height)
    newY = math.max(newY, 0)

    player.x = newX
    player.y = newY

    camera.x = player.x - love.graphics.getWidth() / 2
    
    -- Random pig spawning
    if love.math.random() < PIG_SPAWN_CHANCE then
        local spawnX = camera.x + love.math.random(0, love.graphics.getWidth())
        local chunkX = math.floor(spawnX / TILE_SIZE / CHUNK_SIZE)
        local localX = (math.floor(spawnX / TILE_SIZE) % CHUNK_SIZE) + 1
        
        if terrain[chunkX] and terrain[chunkX][localX] then
            local groundHeight = terrain[chunkX][localX].height * TILE_SIZE
            local isRed = love.math.random() < RED_PIG_SPAWN_CHANCE
            spawnPig(spawnX, groundHeight - 32, isRed)
        end
    end
    
    -- Update pigs
    for i = #pigs, 1, -1 do
        updatePig(pigs[i], dt)
        -- Remove pigs that are too far from the camera
        if math.abs(pigs[i].x - camera.x - love.graphics.getWidth()/2) > love.graphics.getWidth() then
            table.remove(pigs, i)
        end
    end

    -- Update clouds
    for i, cloud in ipairs(clouds) do
        cloud.x = cloud.x + cloud.speed * dt
        -- If cloud is too far behind camera, move it ahead
        if cloud.x < camera.x - cloud.width * 2 then
            cloud.x = camera.x + love.graphics.getWidth() + love.math.random(0, 200)
            cloud.y = love.math.random(0, 100)
        end
        -- If cloud is too far ahead of camera, move it behind
        if cloud.x > camera.x + love.graphics.getWidth() * 2 then
            cloud.x = camera.x - cloud.width - love.math.random(0, 200)
            cloud.y = love.math.random(0, 100)
        end
    end
end

function drawTree(x, y, seed)
    local rng = love.math.newRandomGenerator(seed)
    
    -- Randomize trunk properties
    local trunkWidth = TILE_SIZE/3 + rng:random(-5, 5)
    local trunkHeight = TILE_SIZE * (2.5 + rng:random(0, 1))
    local trunkOffset = TILE_SIZE/3 + rng:random(-5, 5)
    
    -- Draw trunk
    love.graphics.setColor(colors.trunk)
    love.graphics.rectangle("fill", x + trunkOffset, y, trunkWidth, trunkHeight)
    
    -- Randomize leaf properties
    local leafWidth = TILE_SIZE * (0.8 + rng:random(-0.2, 0.2))
    local leafHeight = TILE_SIZE * (2.2 + rng:random(-0.2, 0.2))
    local leafOffset = rng:random(-5, 5)
    
    -- Draw leaves in pixel art style
    love.graphics.setColor(colors.leaves)
    -- Bottom layer (wider)
    love.graphics.rectangle("fill", x + leafOffset, y - TILE_SIZE, leafWidth, TILE_SIZE)
    -- Middle layer
    love.graphics.rectangle("fill", x + leafOffset + TILE_SIZE/4, y - TILE_SIZE * 2, leafWidth * 0.7, TILE_SIZE)
    -- Top point
    love.graphics.rectangle("fill", x + leafOffset + TILE_SIZE/3, y - TILE_SIZE * 2.5, leafWidth * 0.4, TILE_SIZE/2)
    
    -- Add random darker pixel details
    love.graphics.setColor(0.05, 0.4, 0.05)
    for i = 1, 3 do
        local detailX = x + leafOffset + rng:random(0, leafWidth)
        local detailY = y - TILE_SIZE * rng:random(1, 2)
        love.graphics.rectangle("fill", detailX, detailY, TILE_SIZE/4, TILE_SIZE/3)
    end
end

function love.draw()
    -- Draw sky
    love.graphics.setColor(0.4, 0.6, 1)
    love.graphics.rectangle("fill", 0, 0, love.graphics.getWidth(), love.graphics.getHeight())

    -- Draw clouds
    love.graphics.setColor(1, 1, 1)
    for _, cloud in ipairs(clouds) do
        local screenX = cloud.x - camera.x
        love.graphics.rectangle("fill", screenX, cloud.y, cloud.width, TILE_SIZE)
        love.graphics.rectangle("fill", screenX + TILE_SIZE/2, cloud.y - TILE_SIZE/2, cloud.width - TILE_SIZE, TILE_SIZE)
    end

    love.graphics.push()
    love.graphics.translate(-camera.x, 0)

    local startChunk = math.floor(camera.x / (TILE_SIZE * CHUNK_SIZE))
    local endChunk = math.floor((camera.x + love.graphics.getWidth()) / (TILE_SIZE * CHUNK_SIZE)) + 1

    for chunk = startChunk-1, endChunk do
        generateChunk(chunk)
        if terrain[chunk] then
            for x = chunk * CHUNK_SIZE, (chunk + 1) * CHUNK_SIZE - 1 do
                local localX = (x % CHUNK_SIZE) + 1
                if terrain[chunk][localX] then
                    local height = terrain[chunk][localX].height
                    for y = math.floor(height), MAP_HEIGHT do
                        local tileType = y == math.floor(height) and "grass" or "dirt"
                        drawTile(tileType, x * TILE_SIZE, y * TILE_SIZE)
                    end
                end
            end
        end
    end

    -- Draw trees
    for _, tree in ipairs(trees) do
        drawTree(tree.x, tree.y, tree.seed)
    end
    
    -- Draw pigs
    for _, pig in ipairs(pigs) do
        -- Draw fire particles for red pigs
        if pig.particles then
            love.graphics.setColor(1, 1, 1)
            pig.particles:setPosition(pig.x + pig.width/2, pig.y + pig.height/2)
            love.graphics.draw(pig.particles)
        end
        
        if pig.isRed then
            love.graphics.setColor(1, 0, 0)  -- Red pig
        else
            love.graphics.setColor(colors.pig)
        end
        love.graphics.rectangle("fill", pig.x, pig.y, pig.width, pig.height)
        -- Draw pig details
        if pig.isRed then
            love.graphics.setColor(0.8, 0, 0)
        else
            love.graphics.setColor(0.8, 0.6, 0.6)
        end
        love.graphics.rectangle("fill", pig.x + 24, pig.y + 8, 8, 8) -- Nose
        love.graphics.setColor(0, 0, 0)
        love.graphics.rectangle("fill", pig.x + 8, pig.y + 8, 4, 4) -- Eye
    end
    
    drawPlayer(player.x, player.y)

    love.graphics.pop()
    
    -- Draw XP counter and health
    love.graphics.setColor(1, 1, 1)
    love.graphics.print("XP: " .. xp, love.graphics.getWidth() - 100, 10)
    
    -- Draw hearts
    for i = 1, MAX_HEALTH do
        if i <= health then
            love.graphics.setColor(1, 0, 0)
        else
            love.graphics.setColor(0.3, 0.3, 0.3)
        end
        love.graphics.rectangle("fill", 10 + (i-1) * 30, 40, 20, 20)
    end

    -- Draw menus
    if gameState == "intro" then
        love.graphics.setColor(0, 0, 0, 0.7)
        love.graphics.rectangle("fill", 0, 0, love.graphics.getWidth(), love.graphics.getHeight())
        love.graphics.setColor(1, 1, 1)
        love.graphics.printf("Rabid Pigs. 100% Lua game!!!!", 0, love.graphics.getHeight()/3, love.graphics.getWidth(), "center")
        if drawButton("Play", love.graphics.getWidth()/2 - 100, love.graphics.getHeight()/2 - 25, 200, 50) and love.mouse.isDown(1) then
            SUPER_HARD_MODE = false
            gameState = "playing"
            survivalTime = 0
            health = MAX_HEALTH
            xp = 0
            pigs = {}
            player.x = 100
            player.y = 0
        end
        if drawButton("SUPER HARD MODE!!!!!", love.graphics.getWidth()/2 - 100, love.graphics.getHeight()/2 + 50, 200, 50) and love.mouse.isDown(1) then
            SUPER_HARD_MODE = true
            gameState = "playing"
            survivalTime = 0
            health = MAX_HEALTH
            xp = 0
            pigs = {}
            player.x = 100
            player.y = 0
        end
    elseif gameState == "paused" then
        love.graphics.setColor(0, 0, 0, 0.7)
        love.graphics.rectangle("fill", 0, 0, love.graphics.getWidth(), love.graphics.getHeight())
        love.graphics.setColor(1, 1, 1)
        love.graphics.printf("PAUSED", 0, love.graphics.getHeight()/3, love.graphics.getWidth(), "center")
        if drawButton("Resume", love.graphics.getWidth()/2 - 100, love.graphics.getHeight()/2 - 25, 200, 50) and
           love.mouse.isDown(1) then
            gameState = "playing"
        end
    elseif gameState == "dead" then
        love.graphics.setColor(0, 0, 0, 0.7)
        love.graphics.rectangle("fill", 0, 0, love.graphics.getWidth(), love.graphics.getHeight())
        love.graphics.setColor(1, 0, 0)
        love.graphics.printf("YOU DIED", 0, love.graphics.getHeight()/3, love.graphics.getWidth(), "center")
        love.graphics.setColor(1, 1, 1)
        love.graphics.printf(string.format("Time Survived: %.1f seconds\nHighscore: %.1f seconds", 
            survivalTime, highScore), 0, love.graphics.getHeight()/2, love.graphics.getWidth(), "center")
        if drawButton("Play Again", love.graphics.getWidth()/2 - 100, love.graphics.getHeight()*2/3 - 25, 200, 50) and
           love.mouse.isDown(1) then
            gameState = "playing"
            survivalTime = 0
            health = MAX_HEALTH
            xp = 0
            pigs = {}
            player.x = 100
            player.y = 0
        end
    end
    -- Draw coordinates (after pop to keep them fixed on screen)
    love.graphics.setFont(pixelFont)
    love.graphics.setColor(1, 1, 1)
    love.graphics.print(string.format("X: %d Y: %d", math.floor(player.x), math.floor(player.y)), 10, 10)
end
