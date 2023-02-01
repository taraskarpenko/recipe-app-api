from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer

INGREDIENT_URL = reverse('recipe:ingredient-list')


def create_user(email='user@example.com', password='userpass123'):
    return get_user_model().objects.create_user(email, password)


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


def ingredient_detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


class PublicIngredientsTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_require_auth_to_list_ingredients(self):
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_Ingredient(self):
        Ingredient.objects.create(user=self.user, name='beetroot')
        Ingredient.objects.create(user=self.user, name='carrot')

        res = self.client.get(INGREDIENT_URL)

        ingredients = Ingredient.objects.all().order_by('-name')

        ser = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, ser.data)

    def ingredients_limited_to_user(self):
        user2 = create_user(email='user2@example.com')
        Ingredient.objects.create(user=user2, name='beetroot')

        ingredient = Ingredient.objects.create(user=self.user, name='carrot')

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user, name='beetroot')

        payload = {'name': 'carrot'}

        url = ingredient_detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        ingredient.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user, name='halal')

        url = ingredient_detail_url(ingredient.id)
        res = self.client.delete(url)

        tag = Ingredient.objects.filter(id=ingredient.id)
        self.assertFalse(tag.exists())
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_other_user_ingredient(self):
        user2 = create_user(email='user2@example.com')
        user2_ingredient = Ingredient.objects.create(
            user=user2, name='mediterranean'
        )

        Ingredient.objects.create(user=self.user, name='halal')

        url = ingredient_detail_url(user2_ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_ingredients_assigned(self):
        recipe = create_recipe(user=self.user, title='Thai')

        ingredient1 = Ingredient.objects.create(user=self.user, name='apple')
        ingredient2 = Ingredient.objects.create(user=self.user, name='rice')

        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        ingredient1_serialized = IngredientSerializer(ingredient1).data
        ingredient2_serialized = IngredientSerializer(ingredient2).data

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient1_serialized, res.data)
        self.assertNotIn(ingredient2_serialized, res.data)

    def test_filter_assigned_ingredients_unique(self):
        recipe1 = create_recipe(user=self.user, title='Thai rice')
        recipe2 = create_recipe(user=self.user, title='Italian pasta')

        ingredient1 = Ingredient.objects.create(user=self.user, name='apple')
        ingredient2 = Ingredient.objects.create(user=self.user, name='rice')
        Ingredient.objects.create(user=self.user, name='butter')

        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 2)
