from typing import List, Tuple
from models.position import Position
from models.order_plan import DailyOrderPlan, OrderItem, OrderType, BuyTag, SellTag

class InfiniteBuyCalculator:
    def __init__(self, stock_code: str, split_count: int):
        self.stock_code = stock_code.upper()
        self.split_count = split_count
        assert split_count in [20, 40]

    # ... 기존 메서드들 ...

    def create_today_report(self, position: Position, current_price: float) -> DailyOrderPlan:
        """
        오늘의 리포트 생성 (사진과 동일한 형태)
        """
        from utils.timezone import MarketTime
        
        plan = DailyOrderPlan(
            stock_code=self.stock_code,
            mode="리버스모드" if position.is_reverse_mode else "일반모드",
            shares_held=position.shares_held,
            avg_price=round(position.avg_price, 2),
            current_price=round(current_price, 2),
            t_value=position.current_t,
            daily_buy_amount=0,
            star_point=0,
            target_price=0
        )
        
        # 소진/종료 체크
        if position.shares_held == 0 and not position.is_first_buy:
            plan.mode = "사이클 종료"
            return plan
        
        # 리버스모드 분기
        if position.is_reverse_mode:
            return self._create_reverse_report(position, current_price, plan)
        
        # 일반모드 - 첫매수/전반전/후반전
        return self._create_normal_report(position, current_price, plan)

    def _create_normal_report(self, position, current_price, plan):
        """일반모드 리포트 생성"""
        
        daily_amount = self.get_daily_buy_amount(
            position.remaining_capital, position.current_t
        )
        plan.daily_buy_amount = daily_amount
        
        star = self.get_star_price(position.avg_price, position.current_t)
        plan.star_point = star
        target = self.get_target_sell_price(position.avg_price)
        plan.target_price = target
        
        # 매수 구성
        if position.is_first_buy:
            # 첫 매수: 큰수 + 폭락대비
            big_price = current_price * 1.12  # 12% 위
            main_qty = int(daily_amount / big_price)
            
            if main_qty > 0:
                plan.loc_buys.append(OrderItem(
                    price=round(big_price, 2),
                    quantity=main_qty,
                    tag=BuyTag.STAR_BUY.value,  # or "big_number"
                    order_type=OrderType.LOC,
                    note="첫매수 큰수"
                ))
            
            # 폭락대비 5개
            for i, div in enumerate(range(13, 18)):
                crash_price = round(daily_amount / div, 2)
                if crash_price > 0:
                    plan.crash_buys.append(OrderItem(
                        price=crash_price,
                        quantity=1,
                        tag=f"crash_buy_{i+1}",
                        order_type=OrderType.LOC
                    ))
        
        elif position.current_t < (self.split_count / 2):
            # 전반전: 별지점/평단 절반씩
            half = daily_amount / 2
            
            # 별지점 - 0.01
            star_buy_price = round(star - 0.01, 2)
            star_qty = int(half / star_buy_price)
            avg_qty = int(half / position.avg_price)
            
            # 홀짝: 총 홀수면 평단+1
            total = star_qty + avg_qty
            if total % 2 == 1:
                avg_qty += 1
            
            plan.loc_buys.append(OrderItem(
                price=star_buy_price,
                quantity=max(1, star_qty),
                tag=BuyTag.STAR_BUY.value,
                order_type=OrderType.LOC
            ))
            
            plan.loc_buys.append(OrderItem(
                price=round(position.avg_price, 2),
                quantity=max(1, avg_qty),
                tag=BuyTag.AVG_BUY.value,
                order_type=OrderType.LOC
            ))
            
            # 추가 폭락대비
            used = sum(o.price * o.quantity for o in plan.loc_buys)
            remaining = daily_amount - used
            if remaining > 0:
                # 1주씩 추가
                extra_price = round(position.avg_price * 0.93, 2)
                plan.crash_buys.append(OrderItem(
                    price=extra_price, quantity=1,
                    tag="crash_buy_1", order_type=OrderType.LOC
                ))
        
        else:
            # 후반전: 별지점 아래 전체
            star_buy_price = round(star - 0.01, 2)
            qty = max(1, int(daily_amount / star_buy_price))
            
            plan.loc_buys.append(OrderItem(
                price=star_buy_price, quantity=qty,
                tag=BuyTag.STAR_BUY.value, order_type=OrderType.LOC
            ))
            
            # 추가 1주씩
            ratio = 0.95
            remaining = daily_amount - (star_buy_price * qty)
            for i in range(4):
                extra = round(star_buy_price * ratio, 2)
                if remaining > extra:
                    plan.crash_buys.append(OrderItem(
                        price=extra, quantity=1,
                        tag=f"crash_buy_{i+1}", order_type=OrderType.LOC
                    ))
                    remaining -= extra
                    ratio -= 0.03
        
        # 매도 (보유 있을 때)
        if position.shares_held > 0 and not position.is_first_buy:
            # 쿼터매도
            q_qty = self.calculate_quarter_sell(position.shares_held)
            plan.quarter_sell = OrderItem(
                price=round(star, 2),  # 별지점 그대로
                quantity=q_qty,
                tag=SellTag.QUARTER_SELL.value,
                order_type=OrderType.LOC
            )
            
            # 지정가 매도
            remaining_shares = position.shares_held - q_qty
            if remaining_shares > 0:
                plan.final_sell = OrderItem(
                    price=round(target, 2),
                    quantity=remaining_shares,
                    tag=SellTag.FINAL_SELL.value,
                    order_type=OrderType.LIMIT
                )
        
        return plan

    def _create_reverse_report(self, position, current_price, plan):
        """리버스모드 리포트 생성"""
        from strategy.reverse_mode import ReverseModeCalculator
        
        rev = ReverseModeCalculator(position)
        day = position.reverse_day_count + 1
        
        if day == 1:
            # 첫날: MOC 매도만
            plan.mode = "리버스모드 (DAY 1)"
            moc_qty = rev.calculate_moc_sell()
            if moc_qty > 0:
                plan.quarter_sell = OrderItem(
                    price=0,  # 시장가
                    quantity=moc_qty,
                    tag=SellTag.QUARTER_SELL.value,
                    order_type=OrderType.MOC,
                    note="처음매도 MOC"
                )
        
        else:
            # 둘째날~: 별지점 매도 + 쿼터매수
            star = rev.get_star_price()
            plan.star_point = star
            
            # 매도
            sell_qty = rev.calculate_star_sell(position.shares_held)
            if sell_qty > 0:
                plan.quarter_sell = OrderItem(
                    price=round(star, 2),
                    quantity=sell_qty,
                    tag=SellTag.QUARTER_SELL.value,
                    order_type=OrderType.LOC
                )
            
            # 쿼터매수
            quarter_amount, buys = rev.calculate_quarter_buy()
            plan.daily_buy_amount = quarter_amount
            
            for price, qty, btype in buys:
                tag = BuyTag.BIG_NUMBER.value if "big" in btype else BuyTag.STAR_BUY.value
                plan.loc_buys.append(OrderItem(
                    price=round(price, 2), quantity=qty,
                    tag=tag, order_type=OrderType.LOC
                ))
        
        return plan
