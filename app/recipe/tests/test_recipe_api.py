from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status

from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer
)

RECIPE_URL = reverse('recipe:recipe-list')


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


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


class TestPublicRecipeApi(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class TestPrivateRecipeApi(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'pass123'
        )

        self.client.force_authenticate(self.user)

    def test_retrieve_recipes_list(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')

        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_user_recipes_only(self):
        other_user = get_user_model().objects.create_user(
            'user2@example.com',
            'pass123'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user)

        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            'title': 'my Recipe 1',
            'time_minutes': 5,
            'price': Decimal('10.1'),
        }

        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(self.user, recipe.user)

    def test_partial_update(self):
        """Test partial update of a recipe."""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link,
        )

        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link='https://exmaple.com/recipe.pdf',
            description='Sample recipe description.',
        )

        payload = {
            'title': 'New recipe title',
            'link': 'https://example.com/new-recipe.pdf',
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error."""
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_recipe_error(self):
        """Test trying to delete another users recipe gives error."""
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        payload = {
            'title': 'Fav dish',
            'time_minutes': 50,
            'price': Decimal('10.1'),
            'tags': [
                {'name': 'mexican'},
                {'name': 'vaegan'}
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        self.assertEqual(recipe.tags.count(), 2)
        for tag in recipe.tags.all():
            self.assertIn({'name': tag.name}, payload['tags'])

    def test_create_recipe_with_mixed_tags(self):
        tag = Tag.objects.create(user=self.user, name='mexican')

        payload = {
            'title': 'Fav dish',
            'time_minutes': 50,
            'price': Decimal('10.1'),
            'tags': [
                {'name': 'mexican'},
                {'name': 'vaegan'}
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        self.assertIn(tag, recipe.tags.all())

        self.assertEqual(recipe.tags.count(), 2)

        tags = Tag.objects.filter(user=self.user)
        self.assertEqual(tags.count(), 2)
        for tag in tags:
            self.assertIn({'name': tag.name}, payload['tags'])

    def test_create_tag_on_patch_update_recipe(self):
        payload = {
            'title': 'Fav dish',
            'time_minutes': 50,
            'price': Decimal('10.1'),
            'tags': [
                {'name': 'mexican'},
                {'name': 'vaegan'}
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        self.assertEqual(recipe.tags.count(), 2)
        for tag in recipe.tags.all():
            self.assertIn({'name': tag.name}, payload['tags'])

        update_payload = {'tags': [
            {'name': 'mexican'},
            {'name': 'halal'},
            {'name': 'fish'}
        ]}

        url = detail_url(recipe.id)

        update_res = self.client.patch(url, update_payload, format='json')
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        # recipe.refresh_from_db()
        self.assertEqual(recipe.tags.count(), 3)
        for tag in recipe.tags.all():
            self.assertIn({'name': tag.name}, update_payload['tags'])

    def test_assign_existing_tag_patch_update_recipe(self):
        recipe = create_recipe(user=self.user)
        tag1 = Tag.objects.create(user=self.user, name='GlutenFree')
        recipe.tags.add(tag1)

        tag2 = Tag.objects.create(user=self.user, name='Gluten')

        update_payload = {'tags': [
            {'name': tag2.name},
        ]}

        url = detail_url(recipe.id)

        update_res = self.client.patch(url, update_payload, format='json')
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        # recipe.refresh_from_db()
        self.assertEqual(recipe.tags.count(), 1)

        tags = Tag.objects.filter(user=self.user).all()

        self.assertEqual(len(tags), 2)

        actual_tags = recipe.tags.all()
        self.assertEqual(len(actual_tags), 1)
        self.assertEqual(actual_tags[0].name, tag2.name)

    def test_assign_empty_tag_patch_update_recipe(self):
        recipe = create_recipe(user=self.user)
        tag = Tag.objects.create(user=self.user, name='GlutenFree')
        recipe.tags.add(tag)

        update_payload = {'tags': []}

        url = detail_url(recipe.id)

        update_res = self.client.patch(url, update_payload, format='json')
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        # recipe.refresh_from_db()
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredient(self):
        payload = {
            'title': 'Fav dish',
            'time_minutes': 50,
            'price': Decimal('10.1'),
            'ingredients': [
                {'name': 'beetroot'},
                {'name': 'carrot'}
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in recipe.ingredients.all():
            self.assertIn({'name': ingredient.name}, payload['ingredients'])

        ingredients = Ingredient.objects.filter(user=self.user).all()

        self.assertEqual(len(ingredients), 2)

        for ingredient in ingredients:
            self.assertIn({'name': ingredient.name}, payload['ingredients'])

    def test_create_recipe_with_mixed_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user, name='beetroot')
        payload = {
            'title': 'Fav dish',
            'time_minutes': 50,
            'price': Decimal('10.1'),
            'ingredients': [
                {'name': ingredient.name},
                {'name': 'carrot'}
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in recipe.ingredients.all():
            self.assertIn({'name': ingredient.name}, payload['ingredients'])

        ingredients = Ingredient.objects.filter(user=self.user).all()

        self.assertEqual(len(ingredients), 2)

        for ingredient in ingredients:
            self.assertIn({'name': ingredient.name}, payload['ingredients'])
