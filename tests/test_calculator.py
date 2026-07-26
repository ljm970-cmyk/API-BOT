import unittest
from strategy.calculator import InfiniteBuyCalculator

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.t20 = InfiniteBuyCalculator("TQQQ", 20)
        self.t40 = InfiniteBuyCalculator("TQQQ", 40)

    def test_star_percent(self):
        self.assertEqual(self.t20.get_star_percent(0), 15)
        self.assertEqual(self.t20.get_star_percent(10), 0)

    def test_star_price(self):
        p = self.t20.get_star_price(100, 0)
        self.assertEqual(p, 115.0)

    def test_daily_buy_amount(self):
        amt = self.t20.get_daily_buy_amount(20000, 0)
        self.assertEqual(amt, 1000.0)

    def test_t_values(self):
        self.assertEqual(self.t20.apply_full_buy(5), 6)
        self.assertEqual(self.t20.apply_half_buy(5), 5.5)
        self.assertEqual(self.t20.apply_quarter_sell(8), 6)

if __name__ == '__main__':
    unittest.main()
