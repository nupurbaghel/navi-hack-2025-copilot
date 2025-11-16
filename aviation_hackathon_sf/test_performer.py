from unittest import TestCase

from aviation_hackathon_sf import performer


class PerformerTest(TestCase):
    def test_perform_something__happy_path__success(self):
        output = performer.perform_something()

        self.assertEqual(2, len(output))
        self.assertEqual("Everything everywhere all at once.", output[0])


class ValueGeneratorTest(TestCase):
    def test_value_generator__happy_path__success(self):
        output = performer.value_generator()

        self.assertEqual(42.0, output)

    def test_value_generator__no_noise__follow_default(self):
        output = performer.value_generator(add_noise=False)

        self.assertEqual(42.0, output)

    def test_value_generator__add_noise__noise_visible(self):
        output = performer.value_generator(add_noise=True)

        self.assertGreater(output, 42.0)
