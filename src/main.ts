import * as w4 from "./wasm4";

// sprite
const spriteWidth = 8;
const spriteHeight = 8;
const spriteFlags = 1; // BLIT_2BPP
const sprite = memory.data<u8>([0xa5, 0x6a, 0xa4, 0x2a, 0xa5, 0x68, 0x55, 0xa2, 0xa5, 0x4a, 0xa5, 0xaa, 0x9a, 0x6a, 0x6a, 0x6a]);

let t = 0;
let started = true; // for development, start game immediately

class Player {
    constructor(
        public gamepad: usize,
        public x: i32,
        public y: i32,
        public vx: i32,
        public vy: i32,
        public facing: Facing,
        public stance: Stance,
        public health: i32,
        public lungeTimer: i32,
        public stunTimer: i32,
    ) {
    }
}

enum Facing {
    Left = -1,
    Right = 1,
}

enum Stance {
    High = -1,
    Mid = 0,
    Low = 1,
}



let player1 = new Player(w4.GAMEPAD1, 80, 80, 0, 0, Facing.Right, Stance.Mid, 100, 0, 0);
let player2 = new Player(w4.GAMEPAD2, 80, 80, 0, 0, Facing.Right, Stance.Mid, 100, 0, 0);

function updatePlayer(player: Player): void {
    const gamepad = load<u8>(player.gamepad);
    player.vx = 0;
    if (gamepad & w4.BUTTON_LEFT) {
        player.vx -= 1;
        player.facing = Facing.Left;
    }
    if (gamepad & w4.BUTTON_RIGHT) {
        player.vx += 1;
        player.facing = Facing.Right;
    }
    player.vy = 0;
    if (gamepad & w4.BUTTON_UP) {
        player.vy -= 1;
    }
    if (gamepad & w4.BUTTON_DOWN) {
        player.vy += 1;
    }

    player.x += player.vx;
    player.y += player.vy;
}

function drawPlayer(player: Player): void {
    w4.blit(sprite, player.x, player.y, spriteWidth, spriteHeight, spriteFlags  | (w4.BLIT_FLIP_X * (player.facing == Facing.Left ? 1 : 0)));
}

export function start(): void {
    // palette by Polyphrog - appropriate for a game called "Polywogg"
    // https://lospec.com/palette-list/black-tar
    store<u32>(w4.PALETTE, 0x843c35, 0 * sizeof<u32>());
    store<u32>(w4.PALETTE, 0xffeb94, 1 * sizeof<u32>());
    store<u32>(w4.PALETTE, 0x398a75, 2 * sizeof<u32>());
    store<u32>(w4.PALETTE, 0x26153a, 3 * sizeof<u32>());
    // https://lospec.com/palette-list/lava-level
    // store<u32>(w4.PALETTE, 0x726059, 0 * sizeof<u32>());
    // store<u32>(w4.PALETTE, 0x301922, 1 * sizeof<u32>());
    // store<u32>(w4.PALETTE, 0xcf331e, 2 * sizeof<u32>());
    // store<u32>(w4.PALETTE, 0xf29d2c, 3 * sizeof<u32>());
}

export function update(): void {
    store<u16>(w4.DRAW_COLORS, 2);
    w4.text("Welcome to\n\n    Polywogg!", 10, 10);

    const gamepad = load<u8>(w4.GAMEPAD1);
    if (gamepad & w4.BUTTON_1) {
        if (!started) {
            started = true;
            t = 0;
        }
        store<u16>(w4.DRAW_COLORS, 3);
    }

    if (started) {
        t += 1;
        const x = 64 + i32(Math.sin(f32(t) / 10) * 64);
        const y = 64 + i32(Math.cos(f32(t) / 10) * 64);
        // w4.blit(sprite, spriteWidth, spriteHeight, spriteFlags, x, y);
        store<u16>(w4.DRAW_COLORS, 0x42);
        w4.blit(sprite, x, y, spriteFlags, x, y);
        updatePlayer(player1);
        updatePlayer(player2);
        drawPlayer(player1);
        drawPlayer(player2);
    } else {
        w4.text("Press X to start", 16, 90);
    }

    t++;
    // w4.blit(sprite, 36, 76, spriteWidth, spriteHeight, spriteFlags);
}
