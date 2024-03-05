from unittest import TestCase

from randomization import is_id_not_consecutive, is_before_and_after_break, is_break_time_allowed


class Test(TestCase):

    def test_is_id_not_consecutive_1(self):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        actual = is_id_not_consecutive(version, 2, 3)
        excepted = False

        self.assertEqual(actual, excepted)

    def test_is_id_not_consecutive_2(self):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        actual = is_id_not_consecutive(version, 5, 6)
        excepted = True

        self.assertEqual(actual, excepted)

    def test_is_id_not_consecutive_3(self):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        actual = is_id_not_consecutive(version, 8, 9)
        excepted = False

        self.assertEqual(actual, excepted)

    def test_is_id_not_consecutive_4(self):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        actual = is_id_not_consecutive(version, 1, 9)
        excepted = True

        self.assertEqual(actual, excepted)

    def test_is_id_not_consecutive_5(self):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        actual = is_id_not_consecutive(version, 1, 2)
        excepted = False

        self.assertEqual(actual, excepted)

    def test_is_before_and_after_break_1(self):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        actual = is_before_and_after_break(version, 1, 2)
        excepted = False

        self.assertEqual(actual, excepted)

    def test_is_before_and_after_break_2(self):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        actual = is_before_and_after_break(version, 7, 10)
        excepted = False

        self.assertEqual(actual, excepted)

    def test_is_before_and_after_break_3(self):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        actual = is_before_and_after_break(version, 2, 10)
        excepted = True

        self.assertEqual(actual, excepted)

    def test_is_break_allowed_1(self):
        pages = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]

        actual = is_break_time_allowed(pages)
        expected = True

        self.assertEqual(expected, actual)

    def test_is_break_allowed_2(self):
        pages = [10, 10, 10, 10, 5, 5, 5, 5, 5, 5]

        actual = is_break_time_allowed(pages)
        expected = False

        self.assertEqual(expected, actual)

    def test_is_break_allowed_3(self):
        pages = [5, 5, 5, 5, 5, 5, 5, 5, 10, 5]

        actual = is_break_time_allowed(pages)
        expected = True

        self.assertEqual(expected, actual)

    def test_is_break_allowed_4(self):
        pages = [5, 5, 5, 5, 5, 5, 5, 5, 11, 5]

        actual = is_break_time_allowed(pages)
        expected = False

        self.assertEqual(expected, actual)

    def test_is_break_allowed_5(self):
        pages = [5, 11, 5, 5, 5, 5, 5, 5, 5, 5]

        actual = is_break_time_allowed(pages)
        expected = False

        self.assertEqual(expected, actual)

