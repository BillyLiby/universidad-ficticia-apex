import unittest
import validators as v


class TestValidators(unittest.TestCase):
    def test_email(self):
        self.assertTrue(v.valid_email("ana@uni.test"))
        for bad in ["ana", "a@b", "<script>@x.com", "ana@uni.test'--", "a b@x.com", "x" * 300 + "@a.com"]:
            self.assertFalse(v.valid_email(bad), bad)

    def test_student_id(self):
        self.assertTrue(v.valid_student_id("2026001"))
        for bad in ["202600", "20260011", "abc1234", "2026001; DROP", "../etc"]:
            self.assertFalse(v.valid_student_id(bad), bad)

    def test_name(self):
        for ok in ["Ana", "José Luis", "O'Connor", "Pérez-Gómez"]:
            self.assertTrue(v.valid_name(ok), ok)
        for bad in ["", "Ana123", "<b>Ana</b>", "Ana;", "A" * 51, "'--"]:
            self.assertFalse(v.valid_name(bad), bad)

    def test_grade(self):
        self.assertEqual(v.valid_grade("85.5"), 85.5)
        for bad in ["-1", "101", "abc", "nan", "inf", "", None, "1e999"]:
            self.assertIsNone(v.valid_grade(bad), bad)

    def test_search(self):
        for ok in ["Ana", "O'Connor", "2026001", "ana@uni.test", ""]:
            self.assertTrue(v.valid_search(ok), ok)
        for bad in ["a" * 51, "<script>", "x; DROP TABLE users", "%' OR 1=1 --"]:
            self.assertFalse(v.valid_search(bad), bad)

    def test_password(self):
        self.assertTrue(v.valid_password("Abcdef12"))
        for bad in ["short1", "sololetras", "12345678", "a" * 200 + "1"]:
            self.assertFalse(v.valid_password(bad), bad)

    def test_int_param_y_ciclo(self):
        self.assertEqual(v.int_param("2"), 2)
        for bad in ["", "abc", "-1", "1;2", "\u00b2", "\u0663", "9999999999", None]:
            self.assertIsNone(v.int_param(bad), bad)
        self.assertEqual(v.valid_ciclo("4"), 4)
        for bad in ["0", "11", "x"]:
            self.assertIsNone(v.valid_ciclo(bad), bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
