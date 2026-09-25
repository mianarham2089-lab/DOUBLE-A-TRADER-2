from dataclasses import dataclass


@dataclass
class MoneyManager:
    capital: float
    min_trade: float = 1.0
    risk_percent: float = 2.0
    martingale_enabled: bool = False
    max_mtg_steps: int = 1

    current_step: int = 0

    def __post_init__(self):
        self.capital = max(float(self.capital), 0.0)
        self.min_trade = max(float(self.min_trade), 1.0)

    def calculate_trade_amount(self) -> float:
        if self.capital <= 0:
            return 0.0

        risk_amount = self.capital * (self.risk_percent / 100)

        # Never allow a trade below $1
        amount = max(risk_amount, self.min_trade)

        # Never risk more than available capital
        return round(min(amount, self.capital), 2)

    def record_win(self, profit: float):
        self.capital += max(float(profit), 0.0)
        self.current_step = 0

    def record_loss(self, loss: float):
        self.capital = max(0.0, self.capital - abs(float(loss)))

        if self.martingale_enabled:
            self.current_step += 1

            if self.current_step > self.max_mtg_steps:
                self.current_step = 0
        else:
            self.current_step = 0

    def status(self) -> dict:
        return {
            "capital": round(self.capital, 2),
            "next_trade": self.calculate_trade_amount(),
            "min_trade": self.min_trade,
            "risk_percent": self.risk_percent,
            "martingale_enabled": self.martingale_enabled,
            "mtg_step": self.current_step,
        }
