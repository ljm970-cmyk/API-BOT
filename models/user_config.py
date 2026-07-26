import json
import os
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class UserStrategyConfig:
    """사용자별 무한매수법 설정"""
    chat_id: int
    stock_code: str           # "TQQQ" or "SOXL"
    split_count: int          # 20 or 40
    total_capital: float      # 달러 기준 시드
    
    # 자동 생성
    stock_name: str = ""
    target_profit_pct: float = 0  # TQQQ=15%, SOXL=20%
    
    def __post_init__(self):
        self.stock_name = "TQQQ" if "TQQQ" in self.stock_code else "SOXL"
        self.target_profit_pct = 15.0 if "TQQQ" in self.stock_code else 20.0
    
    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "stock_code": self.stock_code,
            "split_count": self.split_count,
            "total_capital": self.total_capital,
            "stock_name": self.stock_name,
            "target_profit_pct": self.target_profit_pct,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserStrategyConfig":
        return cls(
            chat_id=data["chat_id"],
            stock_code=data["stock_code"],
            split_count=data["split_count"],
            total_capital=data["total_capital"],
        )


class UserConfigManager:
    """사용자 설정 저장소"""
    
    FILE = "data/user_configs.json"
    
    def __init__(self):
        self.configs: Dict[int, UserStrategyConfig] = {}
        self._load()
    
    def _load(self):
        if not os.path.exists(self.FILE):
            return
        try:
            with open(self.FILE, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    self.configs[int(k)] = UserStrategyConfig.from_dict(v)
        except Exception:
            pass
    
    def _save(self):
        os.makedirs("data", exist_ok=True)
        with open(self.FILE, 'w') as f:
            json.dump({str(k): v.to_dict() for k, v in self.configs.items()}, f, indent=2)
    
    def get(self, chat_id: int) -> Optional[UserStrategyConfig]:
        return self.configs.get(chat_id)
    
    def set(self, config: UserStrategyConfig):
        self.configs[config.chat_id] = config
        self._save()
    
    def exists(self, chat_id: int) -> bool:
        return chat_id in self.configs
    
    def delete(self, chat_id: int):
        if chat_id in self.configs:
            del self.configs[chat_id]
            self._save()
