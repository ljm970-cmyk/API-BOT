    def _load_or_create(self, code: str, split: int, capital: float) -> Position:
        """기존과 동일, 단 buy_records[0].date로 시작일 추정"""
        # ... 기존 코드 ...
    
    def reset_for_new_cycle(self, compound: bool = False):
        """
        사이클 완전 초기화 (종료 후 새로 시작)
        """
        if compound:
            self.position.total_capital = self.position.remaining_capital
        
        self.position.current_t = 0
        self.position.is_first_buy = True
        self.position.is_reverse_mode = False
        self.position.reverse_day_count = 0
        self.position.buy_records = []  # 기록 초기화
        
        self.save_state()
        logger.info(f"새 사이클 준비: 원금=${self.position.total_capital}")
