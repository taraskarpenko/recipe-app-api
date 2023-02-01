from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import (
    RecipeSerializer
)

RECIPE_URL = reverse('recipe:recipe-list')


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


def create_recipe(user, **params):
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 5,
        'price': Decimal('5.25'),
        'description': 'Sample recipe description',
        'link': 'http://example.com/recipe.pdf'
    }

    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


class FilteringRecipesTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='pass123',
        )

        self.client.force_authenticate(self.user)

    def test_filter_by_tags(self):
        recipe1 = create_recipe(user=self.user, title='Thai')
        recipe2 = create_recipe(user=self.user, title='Italian')

        tag1 = Tag.objects.create(user=self.user, name='vegan')
        tag2 = Tag.objects.create(user=self.user, name='vegeterian')

        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)

        recipe3 = create_recipe(user=self.user, title='Mexican')

        params = {'tags': f'{tag1.id},{tag2.id}'}

        res = self.client.get(RECIPE_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe1_serialized = RecipeSerializer(recipe1).data
        recipe2_serialized = RecipeSerializer(recipe2).data
        recipe3_serialized = RecipeSerializer(recipe3).data

        self.assertIn(recipe1_serialized, res.data)
        self.assertIn(recipe2_serialized, res.data)
        self.assertNotIn(recipe3_serialized, res.data)
        self.assertEqual(len(res.data), 2)

    def test_filter_by_ingredients(self):
        recipe1 = create_recipe(user=self.user, title='Thai')
        recipe2 = create_recipe(user=self.user, title='Italian')

        ingredient1 = Ingredient.objects.create(user=self.user, name='rice')
        ingredient2 = Ingredient.objects.create(user=self.user, name='pasta')

        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)

        recipe3 = create_recipe(user=self.user, title='Thai')

        params = {'ingredients': f'{ingredient1.id},{ingredient2.id}'}

        res = self.client.get(RECIPE_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe1_serialized = RecipeSerializer(recipe1).data
        recipe2_serialized = RecipeSerializer(recipe2).data
        recipe3_serialized = RecipeSerializer(recipe3).data

        self.assertIn(recipe1_serialized, res.data)
        self.assertIn(recipe2_serialized, res.data)
        self.assertNotIn(recipe3_serialized, res.data)
        self.assertEqual(len(res.data), 2)
