import unittest
from app import create_app, db
from app.tax.graduated import compute_graduated_tax, compute_graduated_breakdown
from app.tax.schemes import (
    compute_osd,
    compute_itemized,
    compute_eight_percent,
    recommend_scheme,
)


class TestTaxComputations(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_graduated_tax_brackets(self):
        # Bracket 1: 0 - 250,000 (0%)
        self.assertEqual(compute_graduated_tax(0), 0.0)
        self.assertEqual(compute_graduated_tax(250000), 0.0)

        b1 = compute_graduated_breakdown(200000)
        self.assertEqual(b1["bracket_index"], 1)
        self.assertEqual(b1["base_tax"], 0.0)
        self.assertEqual(b1["excess_rate"], 0.0)
        self.assertEqual(b1["income_tax"], 0.0)

        # Bracket 2: 250,000 - 400,000 (15% of excess over 250k)
        # 300,000 -> excess 50,000 * 0.15 = 7,500
        self.assertEqual(compute_graduated_tax(300000), 7500.0)
        b2 = compute_graduated_breakdown(300000)
        self.assertEqual(b2["bracket_index"], 2)
        self.assertEqual(b2["base_tax"], 0.0)
        self.assertEqual(b2["threshold"], 250000.0)
        self.assertEqual(b2["excess_amount"], 50000.0)
        self.assertEqual(b2["excess_rate"], 15.0)
        self.assertEqual(b2["income_tax"], 7500.0)

        # Bracket 3: 400,000 - 800,000 (22,500 + 20% of excess over 400k)
        # 500,000 -> 22,500 + 100,000 * 0.20 = 42,500
        self.assertEqual(compute_graduated_tax(50000), 0.0)
        self.assertEqual(compute_graduated_tax(500000), 42500.0)
        b3 = compute_graduated_breakdown(500000)
        self.assertEqual(b3["bracket_index"], 3)
        self.assertEqual(b3["base_tax"], 22500.0)
        self.assertEqual(b3["threshold"], 400000.0)
        self.assertEqual(b3["excess_amount"], 100000.0)
        self.assertEqual(b3["excess_rate"], 20.0)

        # Bracket 4: 800,000 - 2,000,000 (102,500 + 25% of excess over 800k)
        # 1,000,000 -> 102,500 + 200,000 * 0.25 = 152,500
        self.assertEqual(compute_graduated_tax(1000000), 152500.0)

        # Bracket 5: 2,000,000 - 8,000,000 (402,500 + 30% of excess over 2M)
        # 3,000,000 -> 402,500 + 1,000,000 * 0.30 = 702,500
        self.assertEqual(compute_graduated_tax(3000000), 702500.0)

        # Bracket 6: > 8,000,000 (2,202,500 + 35% of excess over 8M)
        # 10,000,000 -> 2,202,500 + 2,000,000 * 0.35 = 2,902,500
        self.assertEqual(compute_graduated_tax(10000000), 2902500.0)

    def test_scheme_1_osd(self):
        data = {
            "taxpayer_type": "pure",
            "cash_sales": "1,000,000",
            "accrual_sales": "0",
            "osd_percentage": 40,
            "percentage_tax_rate": 3,
        }
        res = compute_osd(data)
        # Sales = 1M, OSD 40% = 400k, Net Income = 600k
        # Taxable income = 600k (Bracket 3: 400k-800k)
        # Basic tax = 22,500, excess = 200k * 20% = 40,000 -> Income Tax = 62,500
        # Percentage tax 3% of 1M = 30,000
        # Total tax = 92,500
        self.assertEqual(res["sales"], 1000000.0)
        self.assertEqual(res["osd_amount"], 400000.0)
        self.assertEqual(res["net_income"], 600000.0)
        self.assertEqual(res["total_taxable_income"], 600000.0)
        self.assertEqual(res["basic_tax"], 22500.0)
        self.assertEqual(res["excess_amount"], 200000.0)
        self.assertEqual(res["excess_rate"], 20.0)
        self.assertEqual(res["income_tax"], 62500.0)
        self.assertEqual(res["percentage_tax"], 30000.0)
        self.assertEqual(res["total_tax"], 92500.0)

    def test_scheme_2_itemized(self):
        data = {
            "taxpayer_type": "pure",
            "cash_sales": "1,000,000",
            "cash_cost": "200,000",
            "ordinary_deductions": {"rent": 100000, "salaries": 100000},
            "special_deductions": [{"title": "R&D", "amount": 50000}],
            "percentage_tax_rate": 3,
        }
        res = compute_itemized(data)
        # Sales = 1M, Cost = 200k -> Gross Operation = 800k
        # Deductions = 100k + 100k + 50k = 250k
        # Net Income = 550k (Bracket 3)
        # Income Tax = 22,500 + (150,000 * 0.20) = 52,500
        # Percentage tax = 30,000
        # Total tax = 82,500
        self.assertEqual(res["gross_operation"], 800000.0)
        self.assertEqual(res["total_deductions"], 250000.0)
        self.assertEqual(res["net_income"], 550000.0)
        self.assertEqual(res["income_tax"], 52500.0)
        self.assertEqual(res["total_tax"], 82500.0)

    def test_scheme_3_eight_percent_pure(self):
        data = {
            "taxpayer_type": "pure",
            "cash_sales": "1,000,000",
            "flat_rate": 8,
            "standard_deduction": 250000,
        }
        res = compute_eight_percent(data)
        # Gross = 1M, Standard Deduction = 250k, Taxable = 750k
        # Tax = 750k * 8% = 60,000
        self.assertEqual(res["gross_income"], 1000000.0)
        self.assertEqual(res["standard_deduction"], 250000.0)
        self.assertEqual(res["taxable_income"], 750000.0)
        self.assertEqual(res["total_tax"], 60000.0)
        self.assertFalse(res["vat_warning"])

    def test_scheme_3_eight_percent_mixed(self):
        data = {
            "taxpayer_type": "mixed",
            "gross_compensation": "500,000",
            "non_taxable_compensation": "100,000",
            "cash_sales": "1,000,000",
            "flat_rate": 8,
        }
        res = compute_eight_percent(data)
        # Taxable compensation = 400,000 (Bracket 2: 250k-400k)
        # Compensation tax = 0 + (150,000 * 0.15) = 22,500
        # Business tax = 1M * 8% = 80,000 (no standard deduction for mixed)
        # Total tax = 102,500
        self.assertTrue(res["is_mixed"])
        self.assertEqual(res["compensation"]["taxable"], 400000.0)
        self.assertEqual(res["compensation_tax"], 22500.0)
        self.assertEqual(res["business_tax"], 80000.0)
        self.assertEqual(res["total_tax"], 102500.0)

    def test_recommendation_selection(self):
        osd_res = {"scheme": "Scheme 1", "total_tax": 92500.0}
        itemized_res = {"scheme": "Scheme 2", "total_tax": 82500.0}
        eight_res = {"scheme": "Scheme 3", "total_tax": 60000.0, "vat_warning": False}

        rec = recommend_scheme(osd_res, itemized_res, eight_res)
        self.assertEqual(rec["best_scheme"], "Scheme 3")
        self.assertEqual(rec["best_tax"], 60000.0)

        # When 8% has VAT warning, it is excluded from automatic recommendation
        eight_res["vat_warning"] = True
        rec2 = recommend_scheme(osd_res, itemized_res, eight_res)
        self.assertEqual(rec2["best_scheme"], "Scheme 2")
        self.assertEqual(rec2["best_tax"], 82500.0)


if __name__ == "__main__":
    unittest.main()
