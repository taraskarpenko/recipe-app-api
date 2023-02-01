from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


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


def tag_detail_url(tag_id):
    return reverse('recipe:tag-detail', args=[tag_id])


class PublicTagsTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_require_auth_to_list_tags(self):
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        Tag.objects.create(user=self.user, name='halal')
        Tag.objects.create(user=self.user, name='halal')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')

        ser = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, ser.data)

    def tags_limited_to_user(self):
        user2 = create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name='mediterranean')

        tag = Tag.objects.create(user=self.user, name='halal')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_tag_update(self):
        tag = Tag.objects.create(user=self.user, name='halal')

        payload = {'name': 'desert'}

        url = tag_detail_url(tag.id)
        res = self.client.patch(url, payload)

        tag.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        tag = Tag.objects.create(user=self.user, name='halal')

        url = tag_detail_url(tag.id)
        res = self.client.delete(url)

        tag = Tag.objects.filter(id=tag.id)
        self.assertFalse(tag.exists())
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_other_user_tag(self):
        user2 = create_user(email='user2@example.com')
        user2_tag = Tag.objects.create(user=user2, name='mediterranean')

        Tag.objects.create(user=self.user, name='halal')

        url = tag_detail_url(user2_tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_tags_assigned(self):
        recipe = create_recipe(user=self.user, title='Thai')

        tag1 = Tag.objects.create(user=self.user, name='apple')
        tag2 = Tag.objects.create(user=self.user, name='rice')

        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        tag1_serialized = TagSerializer(tag1).data
        tag2_serialized = TagSerializer(tag2).data

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag1_serialized, res.data)
        self.assertNotIn(tag2_serialized, res.data)

    def test_filter_assigned_tags_unique(self):
        recipe1 = create_recipe(user=self.user, title='Thai rice')
        recipe2 = create_recipe(user=self.user, title='Italian pasta')

        tag1 = Tag.objects.create(user=self.user, name='apple')
        tag2 = Tag.objects.create(user=self.user, name='rice')
        tag3 = Tag.objects.create(user=self.user, name='butter')

        recipe1.tags.add(tag1)
        recipe2.tags.add(tag1)
        recipe2.tags.add(tag2)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 2)
