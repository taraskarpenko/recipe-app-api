"""Tests for models"""

from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model

from decimal import Decimal

from core import models


def create_user(email='user@example.com', password='userpass123'):
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):

    def test_create_user_with_email_successful(self):
        email = 'test@example.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normilized(self):
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@EXAMPLE.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(
                email=email,
                password="Pass123",
            )

            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(
                email="",
                password="Pass123",
            )

    def test_greate_superuser(self):
        user = get_user_model().objects.create_superuser(
            email="superuser@example.com",
            password="Pass123"
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        user = create_user()

        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample recipe name',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample recipe description'
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_recipe_with_tag(self):
        user = create_user()
        tag1 = models.Tag.objects.create(user=user, name='tag1')
        tag2 = models.Tag.objects.create(user=user, name='tag2')

        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample recipe name',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample recipe description',
        )
        recipe.tags.set([tag1, tag2])

        self.assertEqual(str(recipe), recipe.title)
        self.assertEqual(list(recipe.tags.all()), [tag1, tag2])

    def test_create_tag(self):
        user = create_user()

        tag = models.Tag.objects.create(user=user, name='tag1')

        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        user = create_user()
        ingredient = models.Ingredient.objects.create(
            user=user, name='beetroot'
        )

        self.assertEqual(str(ingredient), ingredient.name)

    def test_create_recipe_with_ingredients(self):
        user = create_user()
        ing1 = models.Ingredient.objects.create(user=user, name='ing1')
        ing2 = models.Ingredient.objects.create(user=user, name='ing2')

        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample recipe name',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample recipe description',
        )
        recipe.ingredients.set([ing1, ing2])

        self.assertEqual(str(recipe), recipe.title)
        self.assertEqual(list(recipe.ingredients.all()), [ing1, ing2])

    @patch('core.models.uuid.uuid4')
    def test_recipe_filename_uuid(self, mock_uuid):
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')
