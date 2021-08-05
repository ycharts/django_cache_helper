from hashlib import sha256

from unittest.mock import patch

from django.test import TestCase
from django.core.cache import cache

from cache_helper import settings
from cache_helper.decorators import cached, cached_class_method, cached_instance_method
from cache_helper.interfaces import CacheHelperCacheable
from cache_helper.utils import get_hashed_cache_key, get_function_cache_key
from cache_helper.exceptions import CacheKeyCreationError


@cached(60*60)
def foo(a, b):
    return a + b


@cached(5*60)
def return_string(s):
    return s


class Vegetable(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'MyNameIs{0}'.format(self.name)

    def fun_math(self, a, b):
        return a + b

    @cached_instance_method(60*60)
    def take_then_give_back(self, a):
        return a

    @classmethod
    @cached_class_method(60*60)
    def add_sweet_letter(cls, a):
        return cls.__name__ + str(a)

    @staticmethod
    @cached(60*60)
    def static_method(a):
        return a

    @staticmethod
    @cached(60*60)
    def foo(a, b):
        return a + b


class Fruit(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'MyNameIs{0}'.format(self.name)

    @cached_instance_method(60*60)
    def fun_math(self, a, b):
        return a + b

    @cached_instance_method(60*60)
    def take_then_give_back(self, a):
        return a

    @classmethod
    @cached_class_method(60*60)
    def add_sweet_letter(cls, a):
        return cls.__name__ + str(a)

    @staticmethod
    @cached(60*60)
    def static_method(a):
        return a


class Meat(CacheHelperCacheable):
    def __init__(self, name, grams_protein):
        self.name = name
        self.grams_protein = grams_protein

    def __str__(self):
        return 'MyNameIs{0}'.format(self.name)

    def get_cache_helper_key(self):
        return '{name}:{grams_protein}'.format(name=self.name, grams_protein=self.grams_protein)

    @staticmethod
    @cached(60*5)
    def get_grams_protein(meat):
        return meat.grams_protein

    @staticmethod
    @cached(60*60)
    def get_tastier_option(meat, veggie):
        return meat

    @staticmethod
    @cached(60*60)
    def get_protein_sum(meats):
        return sum(meat.grams_protein for meat in meats)


class CacheHelperTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apple = Fruit('Apple')
        cls.cherry = Fruit('Cherry')

        cls.celery = Vegetable('Celery')

        cls.chicken = Meat(name='Chicken', grams_protein=20)
        cls.steak = Meat(name='Steak', grams_protein=26)

    @classmethod
    def tearDownClass(cls):
        pass

    def tearDown(self):
        cache.clear()

    def assertExpectedKeyInCache(self, key):
        """
        Tests given key is in cache, making sure to get the hashed version of key first
        """
        finalized_key = get_hashed_cache_key(key)
        self.assertTrue(finalized_key in cache)

    def assertKeyNotInCache(self, key):
        """
        Tests given key is in cache, making sure to get the hashed version of key first
        """
        finalized_key = get_hashed_cache_key(key)
        self.assertFalse(finalized_key in cache)


class MultipleCallsDiffParamsTestCase(CacheHelperTestBase):

    def test_two_models(self):
        # Call first time and place in cache
        apple_val = self.apple.fun_math(10, 10)
        expected_apple_cache_key = 'test_project.tests.Fruit.fun_math;MyNameIsApple,10,10;'

        cherry_val = self.cherry.fun_math(15, 10)
        expected_cherry_cache_key = 'test_project.tests.Fruit.fun_math;MyNameIsCherry,15,10;'

        self.assertExpectedKeyInCache(expected_apple_cache_key)
        self.assertExpectedKeyInCache(expected_cherry_cache_key)

        self.assertEqual(self.apple.fun_math(10, 10), apple_val)
        self.assertEqual(self.cherry.fun_math(15, 10), cherry_val)

    def test_class_method(self):
        Fruit.add_sweet_letter('a')
        Fruit.add_sweet_letter('c')

        add_sweet_letter_a_key = 'test_project.tests.Fruit.add_sweet_letter;a;'
        add_sweet_letter_c_key = 'test_project.tests.Fruit.add_sweet_letter;c;'

        self.assertExpectedKeyInCache(add_sweet_letter_a_key)
        self.assertExpectedKeyInCache(add_sweet_letter_c_key)

        self.assertEqual(Fruit.add_sweet_letter('a'), 'Fruita')
        self.assertEqual(Fruit.add_sweet_letter('c'), 'Fruitc')


class KeyCreationTestCase(CacheHelperTestBase):
    def tearDown(self):
        settings.MAX_DEPTH = 2

    def test_unusual_character_key_creation(self):
        return_string('āęìøü')
        expected_key_unusual_chars = get_function_cache_key('test_project.tests.return_string', ('āęìøü',), {})
        self.assertExpectedKeyInCache(expected_key_unusual_chars)

        return_string('aeiou')
        expected_key = get_function_cache_key('test_project.tests.return_string', ('aeiou',), {})
        self.assertExpectedKeyInCache(expected_key)

        self.assertNotEqual(expected_key_unusual_chars, expected_key)

    def test_same_method_name_different_class(self):
        """
        Two different classes with the same method name should have different cache keys
        """
        self.apple.take_then_give_back(self.cherry)
        apple_take_give_back_cherry_key = get_function_cache_key('test_project.tests.Fruit.take_then_give_back',
            (self.apple, self.cherry), {})
        self.assertExpectedKeyInCache(apple_take_give_back_cherry_key)

        self.celery.take_then_give_back(self.cherry)
        celery_take_give_back_cherry_key = get_function_cache_key('test_project.tests.Vegetable.take_then_give_back',
            (self.celery, self.cherry), {})
        self.assertExpectedKeyInCache(celery_take_give_back_cherry_key)

        self.assertNotEqual(apple_take_give_back_cherry_key, celery_take_give_back_cherry_key)

    def test_same_class_method_name_different_class(self):
        """
        Two different classes with the same class method name should have different cache keys
        """
        self.apple.add_sweet_letter(self.cherry)
        apple_add_sweet_cherry_key = get_function_cache_key('test_project.tests.Fruit.add_sweet_letter',
            (self.cherry,), {})
        self.assertExpectedKeyInCache(apple_add_sweet_cherry_key)

        self.celery.add_sweet_letter(self.cherry)
        celery_add_sweet_cherry_key = get_function_cache_key('test_project.tests.Vegetable.add_sweet_letter',
            (self.cherry,), {})
        self.assertExpectedKeyInCache(celery_add_sweet_cherry_key)

        self.assertNotEqual(apple_add_sweet_cherry_key, celery_add_sweet_cherry_key)

    def test_same_static_method_name_different_class_instance_reference(self):
        """
        Two different classes with the same static method name should have different cache keys
        """
        self.apple.static_method(self.cherry)
        apple_static_method_key = get_function_cache_key('test_project.tests.Fruit.static_method', (self.cherry,), {})
        self.assertExpectedKeyInCache(apple_static_method_key)

        self.celery.static_method(self.cherry)
        celery_static_method_key = get_function_cache_key('test_project.tests.Vegetable.static_method', (self.cherry,),
            {})
        self.assertExpectedKeyInCache(celery_static_method_key)

        self.assertNotEqual(apple_static_method_key, celery_static_method_key)

    def test_same_static_method_name_different_class_class_reference(self):
        """
        Two different classes with the same static method name should have different cache keys
        """
        Fruit.static_method(self.cherry)
        fruit_static_method_key = get_function_cache_key('test_project.tests.Fruit.static_method', (self.cherry,), {})
        self.assertExpectedKeyInCache(fruit_static_method_key)

        Vegetable.static_method(self.cherry)
        vegetable_static_method_key = get_function_cache_key('test_project.tests.Vegetable.static_method',
            (self.cherry,), {})
        self.assertExpectedKeyInCache(vegetable_static_method_key)

        self.assertNotEqual(fruit_static_method_key, vegetable_static_method_key)

    def test_same_function_name_from_module_level(self):
        """Two different functions with same name should have different cache keys"""
        Vegetable.foo(1, 2)
        vegetable_static_method_key = get_function_cache_key('test_project.tests.Vegetable.foo', (1, 2), {})
        self.assertExpectedKeyInCache(vegetable_static_method_key)

        foo(1, 2)
        module_function_key = get_function_cache_key('test_project.tests.foo', (1, 2), {})
        self.assertExpectedKeyInCache(module_function_key)

        self.assertNotEqual(vegetable_static_method_key, module_function_key)

    def test_args_kwargs_properly_convert_to_string(self):
        """
        Surface level objects are serialized correctly with default settings...
        """
        self.apple.take_then_give_back(self.cherry)
        apple_take_cherry_key = 'test_project.tests.Fruit.take_then_give_back;MyNameIsApple,MyNameIsCherry;'
        self.assertExpectedKeyInCache(apple_take_cherry_key)

    def test_dict_args_properly_convert_to_string(self):
        self.apple.take_then_give_back({1: self.cherry})
        hashed_dict_key = sha256(str(1).encode('utf-8')).hexdigest()
        expected_cache_key = 'test_project.tests.Fruit.take_then_give_back;MyNameIsApple,,,{0},MyNameIsCherry;'.format(hashed_dict_key)
        self.assertExpectedKeyInCache(expected_cache_key)

    def test_dict_args_keep_the_same_order_when_convert_to_string(self):
        dict_arg = {1: self.cherry, 'string': 'ay carambe'}
        self.apple.take_then_give_back(dict_arg)
        expected_key = 'test_project.tests.Fruit.take_then_give_back;MyNameIsApple,,,' \
                       '473287f8298dba7163a897908958f7c0eae733e25d2e027992ea2edc9bed2fa8,ay carambe,,' \
                       '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b,MyNameIsCherry;'
        self.assertExpectedKeyInCache(expected_key)

    def test_set_args_properly_maintain_order_and_convert_to_string(self):
        self.apple.take_then_give_back({1, 'vegetable', self.cherry})
        expected_key = 'test_project.tests.Fruit.take_then_give_back;MyNameIsApple,,' \
                       '4715b734085d8d9c9981d91c6d5cff398c75caf44074851baa94f2de24fba4d7,' \
                       '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b,' \
                       'f8201a5264b6b89b4d92c5bc46aa2e5c3e9610e8fc9ef200df1a39c7f10e7af6;'
        self.assertExpectedKeyInCache(expected_key)

    def test_list_args_properly_convert_to_string(self):
        self.apple.take_then_give_back([self.cherry])
        expected_cache_key = 'test_project.tests.Fruit.take_then_give_back;MyNameIsApple,,MyNameIsCherry;'
        self.assertExpectedKeyInCache(expected_cache_key)

    def test_raises_depth_error(self):
        settings.MAX_DEPTH = 0
        with self.assertRaises(CacheKeyCreationError):
            self.apple.take_then_give_back([self.cherry])


class CacheableTestCase(CacheHelperTestBase):

    def test_key_for_function_with_cache_helper_cacheable_arg(self):
        """
        An instance of a class that implements the CacheHelperCacheable class should use the get_cache_helper_key
        """
        Meat.get_grams_protein(self.chicken)
        expected_cache_key = 'test_project.tests.Meat.get_grams_protein;Chicken:20;'
        self.assertTrue(self.chicken.get_cache_helper_key() in expected_cache_key)
        self.assertExpectedKeyInCache(expected_cache_key)

    @patch('test_project.tests.Meat.get_grams_protein', return_value=20)
    def test_decorator_only_calls_function_once_if_value_cached(self, mock_get_grams_protein):
        """
        If decorated function was already called with same args, decorator won't call wrapped function twice
        """
        # Set qualname since internal function uses it
        mock_get_grams_protein.__qualname__ = 'test_project.tests.Meat.get_grams_protein'
        decorated_mock_grams_protein = cached(timeout=5*60)(mock_get_grams_protein)
        decorated_mock_grams_protein(self.chicken)
        # Call the function twice with the same args
        decorated_mock_grams_protein(self.chicken)
        # calling the decorated mock function twice with the same args should only call the mock function once
        # as the return value should be stored inside the cache
        self.assertEqual(mock_get_grams_protein.call_count, 1)

    @patch('test_project.tests.Meat.get_grams_protein', return_value=20)
    def test_decorator_only_calls_function_twice_when_supplied_different_args(self, mock_get_grams_protein):
        """
        Decorator calls function twice when supplied with different args
        """
        # Set qualname since internal function uses it
        mock_get_grams_protein.__qualname__ = 'test_project.tests.Meat.get_grams_protein'
        decorated_mock_grams_protein = cached(timeout=5*60)(mock_get_grams_protein)
        decorated_mock_grams_protein(self.chicken)
        # Call the function with different args to see if function will be called again
        decorated_mock_grams_protein(self.steak)
        self.assertEqual(mock_get_grams_protein.call_count, 2)

    def test_key_for_cacheable_function_with_mixed_cacheable_args(self):
        """
        Test when a cached function takes in both a CacheHelperCacheable object and a regular object
        """
        Meat.get_tastier_option(self.chicken, self.celery)
        expected_cache_key = 'test_project.tests.Meat.get_tastier_option;Chicken:20,MyNameIsCelery;'
        self.assertExpectedKeyInCache(expected_cache_key)

    def test_key_for_list_of_cacheable_objects(self):
        """
        Test when a cached function takes in a list of CacheHelperCacheable objects
        """
        Meat.get_protein_sum([self.chicken, self.steak])
        expected_cache_key = 'test_project.tests.Meat.get_protein_sum;,Chicken:20,Steak:26;'
        self.assertExpectedKeyInCache(expected_cache_key)

    def test_key_for_set_of_cacheable_objects(self):
        """
        Test when a cached function takes in a set of CacheHelperCacheable objects
        """
        Meat.get_protein_sum({self.steak, self.chicken})
        expected_cache_key = 'test_project.tests.Meat.get_protein_sum;,' \
                             '6dd472107034f41f27f301ddbcc97ba4bc0d54945e759d170268aa1091c436fe,' \
                             '9ff36157b4df732256fe3b151cbf8a6bdcc22969d4d6ceaad588bccbbd5c942f;'
        self.assertExpectedKeyInCache(expected_cache_key)

    def test_key_for_dict_of_cacheable_objects(self):
        """
        Test when a cached function takes in a dict with CacheHelperCacheable objects as keys
        """
        Meat.get_tastier_option({self.chicken: 'Tasty'}, {self.celery: 'Terrible'})
        expected_cache_key = 'test_project.tests.Meat.get_tastier_option;' \
                             ',,9ff36157b4df732256fe3b151cbf8a6bdcc22969d4d6ceaad588bccbbd5c942f,Tasty,' \
                             ',,8a332387e40497a972a0ab2099659b49b99be0d00130158f9cb92ecc93ca5b18,Terrible;'
        self.assertExpectedKeyInCache(expected_cache_key)

    def test_key_for_function_with_cache_helper_cacheable_object_as_kwarg(self):
        """
        Test when a cached function is called with a CacheHelperCacheable object as a kwarg
        """
        Meat.get_grams_protein(meat=self.chicken)
        expected_cache_key = 'test_project.tests.Meat.get_grams_protein;;,meat,Chicken:20'
        self.assertExpectedKeyInCache(expected_cache_key)


class CacheInvalidateTestCase(CacheHelperTestBase):
    def test_invalidate_instance_method(self):
        """
        Tests that invalidate works on an instance method
        """
        expected_apple_cache_key = 'test_project.tests.Fruit.fun_math;MyNameIsApple,1,1;'

        self.assertKeyNotInCache(expected_apple_cache_key)

        # Call the function, store result in the cache
        self.apple.fun_math(1, 1)
        self.assertExpectedKeyInCache(expected_apple_cache_key)

        # Invalidate the call, now the result is no longer in the cache
        self.apple.fun_math.invalidate(1, 1)
        self.assertKeyNotInCache(expected_apple_cache_key)

    def test_invalidate_static_method(self):
        """
        Tests that invalidate works on a static method
        """
        expected_apple_cache_key = 'test_project.tests.Fruit.static_method;15;'

        self.assertKeyNotInCache(expected_apple_cache_key)

        # Call the function, store result in the cache
        self.apple.static_method(15)
        self.assertExpectedKeyInCache(expected_apple_cache_key)

        # Invalidate the call, now the result is no longer in the cache
        self.apple.static_method.invalidate(15)
        self.assertKeyNotInCache(expected_apple_cache_key)

    def test_invalidate_class_method(self):
        """
        Tests that invalidate works on a class method
        """
        expected_apple_cache_key = 'test_project.tests.Fruit.add_sweet_letter;x;'

        self.assertKeyNotInCache(expected_apple_cache_key)

        # Call the function, store result in the cache
        Fruit.add_sweet_letter('x')
        self.assertExpectedKeyInCache(expected_apple_cache_key)

        # Invalidate the call, now the result is no longer in the cache
        Fruit.add_sweet_letter.invalidate('x')
        self.assertKeyNotInCache(expected_apple_cache_key)

    def test_invalidate_only_removes_one_key(self):
        """
        Tests that calling invalidate only removes a single key, and does not disturb other similar keys in the cache.
        """
        self.apple.fun_math(7, 15)
        self.apple.fun_math(7, 16)
        self.apple.fun_math(15, 7)
        self.cherry.fun_math(7, 15)

        expected_cache_keys = [
            'test_project.tests.Fruit.fun_math;MyNameIsApple,7,15;',
            'test_project.tests.Fruit.fun_math;MyNameIsApple,7,16;',
            'test_project.tests.Fruit.fun_math;MyNameIsApple,15,7;',
            'test_project.tests.Fruit.fun_math;MyNameIsCherry,7,15;',
        ]

        for key in expected_cache_keys:
            self.assertExpectedKeyInCache(key)

        self.apple.fun_math.invalidate(7, 15)

        self.assertKeyNotInCache(expected_cache_keys[0])
        for key in expected_cache_keys[1:]:
            self.assertExpectedKeyInCache(key)
