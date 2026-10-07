import json
import unittest
from app import create_app, db
from app.models import User, Computation, TaxBracket


class TestApiAndRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SECRET_KEY"] = "test-secret"
        self.app.config["ADMIN_EMAIL"] = "admin@example.com"
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed tax brackets
        from app.tax.graduated import TAX_BRACKETS
        if TaxBracket.query.count() == 0:
            for upper, base_tax, rate, threshold in TAX_BRACKETS:
                db.session.add(TaxBracket(
                    tax_year="2023 onwards (TRAIN Law)",
                    over_amount=None if threshold == 0 else threshold,
                    upper_amount=None if upper == float("inf") else upper,
                    base_tax=base_tax,
                    rate=rate,
                    threshold=threshold,
                    is_active=True,
                ))
            db.session.commit()

        # Register normal user
        from app import bcrypt
        self.user = User(
            email="user@example.com",
            full_name="Regular User",
            password_hash=bcrypt.generate_password_hash("password123").decode("utf-8"),
        )
        self.admin = User(
            email="admin@example.com",
            full_name="Admin User",
            password_hash=bcrypt.generate_password_hash("admin123").decode("utf-8"),
        )
        db.session.add(self.user)
        db.session.add(self.admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, email, password):
        return self.client.post("/login", data={
            "email": email,
            "password": password,
        }, follow_redirects=True)

    def test_auth_login_logout(self):
        resp = self.login_as("user@example.com", "password123")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Welcome back", resp.data)
        self.assertIn(b"Welcome back, Regular User", resp.data)

        # Authenticated user visiting /login or /register redirects to /dashboard
        resp_already_login = self.client.get("/login", follow_redirects=False)
        self.assertEqual(resp_already_login.status_code, 302)
        self.assertTrue(resp_already_login.location.endswith("/dashboard"))

        resp_already_reg = self.client.get("/register", follow_redirects=False)
        self.assertEqual(resp_already_reg.status_code, 302)
        self.assertTrue(resp_already_reg.location.endswith("/dashboard"))

        resp_logout = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(resp_logout.status_code, 200)
        self.assertIn(b"logged out", resp_logout.data)

    def test_register_directs_to_dashboard(self):
        reg_resp = self.client.post("/register", data={
            "email": "newbie@example.com",
            "full_name": "New Taxpayer",
            "password": "secretpassword",
            "confirm_password": "secretpassword",
        }, follow_redirects=False)
        # Should redirect directly to dashboard
        self.assertEqual(reg_resp.status_code, 302)
        self.assertTrue(reg_resp.location.endswith("/dashboard"))

        # Follow to dashboard
        dash_resp = self.client.get(reg_resp.location)
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn(b"Welcome, New Taxpayer", dash_resp.data)
        self.assertIn(b"Saved computations", dash_resp.data)

    def test_login_with_next_query(self):
        # When next is "/", it should still direct to dashboard
        resp = self.client.post("/login?next=%2F", data={
            "email": "user@example.com",
            "password": "password123",
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.endswith("/dashboard"))

        self.client.get("/logout")

        # When next is a specific page like /history, it respects the deep link
        resp2 = self.client.post("/login?next=/history", data={
            "email": "user@example.com",
            "password": "password123",
        }, follow_redirects=False)
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue(resp2.location.endswith("/history"))

    def test_api_compute(self):
        self.login_as("user@example.com", "password123")
        payload = {
            "taxpayer_type": "pure",
            "cash_sales": 1000000,
            "accrual_sales": 0,
            "cash_cost": 200000,
            "accrual_cost": 0,
            "ordinary_deductions": {"rent": 50000},
            "special_deductions": [],
            "nolco": [],
            "osd_percentage": 40,
            "percentage_tax_rate": 3,
            "standard_deduction": 250000,
            "flat_rate": 8,
        }
        res = self.client.post(
            "/api/compute",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("results", data)
        self.assertIn("osd", data["results"])
        self.assertIn("itemized", data["results"])
        self.assertIn("eight", data["results"])
        self.assertIn("best_scheme", data["results"])

    def test_api_save_and_history(self):
        self.login_as("user@example.com", "password123")
        payload = {
            "computation_title": "FY 2025 Test Estimate",
            "computation_note": "Internal audit test",
            "taxpayer_type": "pure",
            "cash_sales": 500000,
            "accrual_sales": 0,
            "cash_cost": 0,
            "accrual_cost": 0,
            "ordinary_deductions": {},
            "special_deductions": [],
            "nolco": [],
            "osd_percentage": 40,
            "percentage_tax_rate": 3,
            "standard_deduction": 250000,
            "flat_rate": 8,
        }
        res = self.client.post(
            "/api/save",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("id", data)
        computation_id = data["id"]

        # View route
        view_res = self.client.get(f"/view/{computation_id}")
        self.assertEqual(view_res.status_code, 200)
        self.assertIn(b"FY 2025 Test Estimate", view_res.data)
        self.assertIn(b"Basic Amount based on Tax Table", view_res.data)

        # History route
        hist_res = self.client.get("/history")
        self.assertEqual(hist_res.status_code, 200)
        self.assertIn(b"FY 2025 Test Estimate", hist_res.data)

        # PDF and CSV exports
        pdf_res = self.client.get(f"/export/pdf/{computation_id}")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.mimetype, "application/pdf")

        csv_res = self.client.get(f"/export/csv/{computation_id}")
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn(b"Basic Tax (Tax Table)", csv_res.data)

    def test_tax_table_permissions(self):
        # 1. Regular user can VIEW the tax table (GET is 200, not 403)
        self.login_as("user@example.com", "password123")
        res_view = self.client.get("/tax-table")
        self.assertEqual(res_view.status_code, 200)
        self.assertIn(b"Graduated Individual Income Tax Table", res_view.data)
        # Regular user should NOT see the save changes button
        self.assertNotIn(b"Save Tax Table Changes", res_view.data)

        # Regular user POST should be rejected with 403
        res_post_denied = self.client.post("/tax-table", data={"action": "save"})
        self.assertEqual(res_post_denied.status_code, 403)

        # 2. Admin user can view and edit
        self.client.get("/logout")
        self.login_as("admin@example.com", "admin123")
        admin_view = self.client.get("/tax-table")
        self.assertEqual(admin_view.status_code, 200)
        self.assertIn(b"Save Tax Table Changes", admin_view.data)
        self.assertIn(b"+ Add New Bracket", admin_view.data)

        # Admin reset defaults
        reset_res = self.client.post(
            "/tax-table",
            data={"action": "reset_defaults"},
            follow_redirects=True,
        )
        self.assertEqual(reset_res.status_code, 200)
        self.assertIn(b"Tax table reset", reset_res.data)

    def test_api_tax_table(self):
        self.login_as("user@example.com", "password123")
        res = self.client.get("/api/tax-table")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("brackets", data)
        self.assertEqual(len(data["brackets"]), 6)


if __name__ == "__main__":
    unittest.main()
