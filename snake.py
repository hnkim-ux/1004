"""간단한 뱀 게임 (tkinter 사용, 별도 설치 불필요)

조작법:
  방향키 / WASD : 이동
  Space        : 일시정지 / 재개
  R            : 게임 오버 후 다시 시작
"""

import random
import tkinter as tk

CELL = 20          # 한 칸 크기(px)
COLS = 30          # 가로 칸 수
ROWS = 20          # 세로 칸 수
SPEED = 100        # 이동 간격(ms), 작을수록 빠름

DIRECTIONS = {
    "Up": (0, -1), "w": (0, -1),
    "Down": (0, 1), "s": (0, 1),
    "Left": (-1, 0), "a": (-1, 0),
    "Right": (1, 0), "d": (1, 0),
}


class SnakeGame:
    def __init__(self, root):
        self.root = root
        root.title("Snake")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                bg="black", highlightthickness=0)
        self.canvas.pack()
        self.label = tk.Label(root, font=("Consolas", 14))
        self.label.pack(fill="x")

        root.bind("<Key>", self.on_key)
        self.after_id = None
        self.reset()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.paused = False
        self.game_over = False
        self.place_food()
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.tick()

    def place_food(self):
        empty = [(x, y) for x in range(COLS) for y in range(ROWS)
                 if (x, y) not in self.snake]
        self.food = random.choice(empty) if empty else None

    def on_key(self, event):
        key = event.keysym
        if key in DIRECTIONS or key.lower() in DIRECTIONS:
            new = DIRECTIONS.get(key) or DIRECTIONS[key.lower()]
            # 반대 방향으로는 바로 꺾을 수 없음
            if (new[0] + self.direction[0], new[1] + self.direction[1]) != (0, 0):
                self.next_direction = new
        elif key == "space" and not self.game_over:
            self.paused = not self.paused
            self.draw()
        elif key.lower() == "r" and self.game_over:
            self.reset()

    def tick(self):
        if not self.paused and not self.game_over:
            self.step()
        self.draw()
        if not self.game_over:
            self.after_id = self.root.after(SPEED, self.tick)

    def step(self):
        self.direction = self.next_direction
        hx, hy = self.snake[0]
        head = (hx + self.direction[0], hy + self.direction[1])

        # 벽 또는 자기 몸에 부딪히면 게임 오버 (꼬리는 이번 턴에 비켜나므로 제외)
        hit_wall = not (0 <= head[0] < COLS and 0 <= head[1] < ROWS)
        body = self.snake if head == self.food else self.snake[:-1]
        if hit_wall or head in body:
            self.game_over = True
            return

        self.snake.insert(0, head)
        if head == self.food:
            self.score += 10
            self.place_food()
            if self.food is None:  # 화면을 가득 채우면 승리
                self.game_over = True
        else:
            self.snake.pop()

    def draw(self):
        c = self.canvas
        c.delete("all")
        if self.food:
            fx, fy = self.food
            c.create_oval(fx * CELL + 2, fy * CELL + 2,
                          (fx + 1) * CELL - 2, (fy + 1) * CELL - 2, fill="red", outline="")
        for i, (x, y) in enumerate(self.snake):
            color = "#7CFC00" if i == 0 else "#228B22"
            c.create_rectangle(x * CELL + 1, y * CELL + 1,
                               (x + 1) * CELL - 1, (y + 1) * CELL - 1, fill=color, outline="")

        status = f"점수: {self.score}"
        if self.game_over:
            msg = "승리!" if self.food is None else "게임 오버"
            c.create_text(COLS * CELL // 2, ROWS * CELL // 2, fill="white",
                          font=("Consolas", 24, "bold"), text=f"{msg}\nR: 다시 시작",
                          justify="center")
        elif self.paused:
            status += "   (일시정지)"
        self.label.config(text=status)


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
