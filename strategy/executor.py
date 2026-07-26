    def update_after_buy(self, plan, executed_tags: list):
        """매수 체결 후 T값/잔금/보유 갱신"""
        p = self.position
        
        total_buy_value = 0
        total_buy_qty = 0
        
        for o in plan.loc_buys + plan.crash_buys:
            if o.tag not in executed_tags:
                continue
            
            amount = o.price * o.quantity
            total_buy_value += amount
            total_buy_qty += o.quantity
            
            p.remaining_capital -= amount
            p.buy_records.append(BuyRecord(
                date=datetime.now().strftime("%Y%m%d"),
                price=o.price, quantity=o.quantity,
                amount=amount, t_at_buy=p.current_t
            ))
        
        # 평균단가
        if total_buy_qty > 0:
            old = p.avg_price * p.shares_held
            p.shares_held += total_buy_qty
            p.avg_price = round((old + total_buy_value) / p.shares_held, 2) if p.shares_held > 0 else 0
        
        # T값: 매수
        if total_buy_qty > 0:
            if p.current_t == 0:
                p.current_t = self.calculator.apply_full_buy(p.current_t)
            else:
                # 전반전/후반전 구분
                is_full = len(executed_tags) >= 2  # 별지점+평단 모두 체결
                if is_full:
                    p.current_t = self.calculator.apply_full_buy(p.current_t)
                else:
                    p.current_t = self.calculator.apply_half_buy(p.current_t)
        
        p.is_first_buy = False
        self.save_state()

    def update_after_sell(self, plan, executed_tags: list):
        """매도 체결 후 T값/잔금/보유 갱신"""
        p = self.position
        
        # 쿼터매도
        if plan.quarter_sell and plan.quarter_sell.tag in executed_tags:
            o = plan.quarter_sell
            p.shares_held -= o.quantity
            p.remaining_capital += o.price * o.quantity
            
            # T값: 쿼터매도
            p.current_t = self.calculator.apply_quarter_sell(p.current_t)
        
        # 지정가매도 (종료조건 체크)
        if plan.final_sell and plan.final_sell.tag in executed_tags:
            o = plan.final_sell
            p.shares_held -= o.quantity
            p.remaining_capital += o.price * o.quantity
            
            # 3/4 + 1/4 모두 체결되면 T=0
            if p.shares_held == 0:
                p.current_t = 0
                p.is_first_buy = True
        
        self.save_state()
