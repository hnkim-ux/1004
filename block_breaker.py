import tkinter as tk


class BlockBreaker:
    WIDTH = 800
    HEIGHT = 600
    BALL_RADIUS = 8
    PADDLE_WIDTH = 120
    PADDLE_HEIGHT = 14
    PADDLE_SPEED = 9

    def __init__(self, root):
        self.root = root
        self.root.title("블록깨기")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg="#101820",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.root.bind("<Left>", lambda event: self.move_paddle(-1))
        self.root.bind("<Right>", lambda event: self.move_paddle(1))
        self.root.bind("<Key-a>", lambda event: self.move_paddle(-1))
        self.root.bind("<Key-d>", lambda event: self.move_paddle(1))
        self.root.bind("<space>", self.handle_space)
        self.root.bind("<Key-p>", self.toggle_pause)
        self.root.bind("<Key-r>", self.restart)

        self.after_id = None
        self.reset_game()

    def reset_game(self, event=None):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.score = 0
        self.lives = 3
        self.state = "ready"
        self.ball_dx = 4
        self.ball_dy = -5
        self.paddle = (self.WIDTH / 2 - self.PADDLE_WIDTH / 2, 550,
                       self.WIDTH / 2 + self.PADDLE_WIDTH / 2, 550 + self.PADDLE_HEIGHT)
        self.ball_x = self.WIDTH / 2
        self.ball_y = 530
        self.bricks = []

        colors = ["#ff6b6b", "#ff9f43", "#feca57", "#1dd1a1", "#54a0ff"]
        brick_width = 70
        brick_height = 22
        gap = 8
        left_margin = (self.WIDTH - (10 * brick_width + 9 * gap)) / 2
        for row in range(5):
            for column in range(10):
                x1 = left_margin + column * (brick_width + gap)
                y1 = 78 + row * (brick_height + gap)
                brick_id = self.canvas.create_rectangle(
                    x1, y1, x1 + brick_width, y1 + brick_height,
                    fill=colors[row], outline="",
                )
                self.bricks.append((brick_id, x1, y1, x1 + brick_width, y1 + brick_height))

        self.draw()

    def move_paddle(self, direction):
        left, top, right, bottom = self.paddle
        shift = direction * self.PADDLE_SPEED
        shift = max(-left, min(self.WIDTH - right, shift))
        self.paddle = (left + shift, top, right + shift, bottom)
        if self.state == "ready":
            self.ball_x += shift
        self.draw()

    def handle_space(self, event=None):
        if self.state == "ready":
            self.state = "playing"
            self.schedule_update()
        elif self.state == "paused":
            self.state = "playing"
            self.schedule_update()
        self.draw()

    def toggle_pause(self, event=None):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"
            self.schedule_update()
        self.draw()

    def restart(self, event=None):
        self.reset_game()

    def schedule_update(self):
        if self.after_id is None:
            self.after_id = self.root.after(16, self.update_game)

    def update_game(self):
        self.after_id = None
        if self.state != "playing":
            return

        radius = self.BALL_RADIUS
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        if self.ball_x - radius <= 0 or self.ball_x + radius >= self.WIDTH:
            self.ball_dx *= -1
        if self.ball_y - radius <= 0:
            self.ball_dy = abs(self.ball_dy)

        paddle_left, paddle_top, paddle_right, _ = self.paddle
        if (
            self.ball_dy > 0
            and self.ball_y + radius >= paddle_top
            and self.ball_y - radius <= paddle_top + self.PADDLE_HEIGHT
            and paddle_left - radius <= self.ball_x <= paddle_right + radius
        ):
            self.ball_dy = -abs(self.ball_dy)
            offset = (self.ball_x - (paddle_left + paddle_right) / 2) / (self.PADDLE_WIDTH / 2)
            self.ball_dx = max(-7, min(7, offset * 6))
            if abs(self.ball_dx) < 1.5:
                self.ball_dx = 1.5 if self.ball_dx >= 0 else -1.5

        ball_left = self.ball_x - radius
        ball_right = self.ball_x + radius
        ball_top = self.ball_y - radius
        ball_bottom = self.ball_y + radius
        for brick in self.bricks[:]:
            brick_id, left, top, right, bottom = brick
            if ball_right >= left and ball_left <= right and ball_bottom >= top and ball_top <= bottom:
                self.canvas.delete(brick_id)
                self.bricks.remove(brick)
                self.score += 10
                self.ball_dy *= -1
                break

        if self.ball_y - radius > self.HEIGHT:
            self.lives -= 1
            if self.lives <= 0:
                self.state = "game_over"
            else:
                self.state = "ready"
                self.ball_x = (self.paddle[0] + self.paddle[2]) / 2
                self.ball_y = 530
                self.ball_dx = 4
                self.ball_dy = -5

        if not self.bricks and self.state == "playing":
            self.state = "won"

        self.draw()
        if self.state == "playing":
            self.schedule_update()

    def draw(self):
        self.canvas.delete("hud", "ball", "paddle", "overlay")
        self.canvas.create_text(
            20, 24, anchor="w", text=f"점수  {self.score}",
            fill="#f5f7fa", font=("맑은 고딕", 14, "bold"), tag="hud",
        )
        self.canvas.create_text(
            self.WIDTH - 20, 24, anchor="e", text=f"생명  {self.lives}",
            fill="#f5f7fa", font=("맑은 고딕", 14, "bold"), tag="hud",
        )
        self.canvas.create_line(16, 48, self.WIDTH - 16, 48, fill="#34495e", tag="hud")

        self.canvas.create_rectangle(*self.paddle, fill="#f5f7fa", outline="", tag="paddle")
        radius = self.BALL_RADIUS
        self.canvas.create_oval(
            self.ball_x - radius, self.ball_y - radius,
            self.ball_x + radius, self.ball_y + radius,
            fill="#7bed9f", outline="", tag="ball",
        )

        messages = {
            "ready": "스페이스를 눌러 시작",
            "paused": "일시정지  ·  스페이스 또는 P로 계속",
            "game_over": "게임 오버  ·  R을 눌러 다시 시작",
            "won": "모든 블록을 깼어요!  ·  R을 눌러 다시 시작",
        }
        if self.state in messages:
            self.canvas.create_text(
                self.WIDTH / 2, 350, text=messages[self.state],
                fill="#ffffff", font=("맑은 고딕", 20, "bold"),
                tag="overlay",
            )


if __name__ == "__main__":
    window = tk.Tk()
    game = BlockBreaker(window)
    window.mainloop()