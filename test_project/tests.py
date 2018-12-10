from hashlib import sha256

from unittest.mock import patch

from django.test import TestCase
from django.core.cache import cache

from cache_helper import settings
from cache_helper.decorators import cached
from cache_helper.interfaces import CacheHelperCacheable
from cache_helper.utils import get_function_type, sanitize_key
from cache_helper.exceptions import CacheKeyCreationError


@cached(60*60)
def foo(a, b):
    return a + b


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

    def assertKeyInCache(self, key):
        sanitized_key = sanitize_key(key)
        self.assertTrue(sanitized_key in cache)


class Vegetable(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'MyNameIs{0}'.format(self.name)

    def fun_math(self, a, b):
        return a + b

    @cached(60*60)
    def take_then_give_back(self, a):
        return a

    @cached(60*60)
    def instance_method(self):
        return self.name

    @classmethod
    def class_method(cls):
        return cls

    @classmethod
    @cached(60*60)
    def add_sweet_letter(cls, a):
        return cls.__name__ + a

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

    @cached(60*60)
    def fun_math(self, a, b):
        return a + b

    @cached(60*60)
    def take_then_give_back(self, a):
        return a

    @property
    @cached(60*60)
    def is_green(self):
        if self.name == 'Apple':
            return True
        return False

    @classmethod
    @cached(60*60)
    def add_sweet_letter(cls, a):
        return cls.__name__ + a

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


class FuncTypeTest(CacheHelperTestBase):
    """
    Test make sure functions catch right type
    """
    def assertFuncType(self, func, tp):
        self.assertEqual(get_function_type(func), tp)

    def test_module_func(self):
        self.assertFuncType(foo, 'function')

    def test_instance_method(self):
        self.assertFuncType(self.celery.instance_method, 'method')

    def test_static_method(self):
        self.assertFuncType(Vegetable.static_method, 'function')

    def test_class_method(self):
        self.assertFuncType(Vegetable.class_method, 'class_method')


class BasicCacheTestCase(CacheHelperTestBase):
    def test_function_cache(self):
        foo(1, 2)
        expected_key = 'tests.foo;1,2;'
        self.assertKeyInCache(expected_key)


class MultipleCallsDiffParamsTestCase(CacheHelperTestBase):

    def test_two_models(self):
        # Call first time and place in cache
        apple_val = self.apple.fun_math(10, 10)
        cherry_val = self.cherry.fun_math(15, 10)

        self.assertEqual(self.apple.fun_math(10, 10), apple_val)
        self.assertEqual(self.cherry.fun_math(15, 10), cherry_val)

    def test_class_method(self):
        Fruit.add_sweet_letter('a')
        Fruit.add_sweet_letter('c')

        add_sweet_letter_a_key = 'tests.Fruit.add_sweet_letter;a;'
        add_sweet_letter_c_key = 'tests.Fruit.add_sweet_letter;c;'

        self.assertKeyInCache(add_sweet_letter_a_key)
        self.assertKeyInCache(add_sweet_letter_c_key)

        self.assertEqual(Fruit.add_sweet_letter('a'), 'Fruita')
        self.assertEqual(Fruit.add_sweet_letter('c'), 'Fruitc')


class KeyLengthTestCase(CacheHelperTestBase):

    def test_keys_are_truncated_beyond_250_chars(self):
        try:
            apple_val = self.apple.fun_math(('a' * 200), ('b' * 200))
            self.assertTrue(isinstance(apple_val, str))
        except Exception:
            self.fail('Keys are not being correctly truncated.')


class KeyCreationTestCase(CacheHelperTestBase):
    def tearDown(self):
        settings.MAX_DEPTH = 2

    def test_same_method_name_different_class(self):
        """
        Two different classes with the same method name should have different cache keys
        """
        apple_take_give_back_cherry_key = self.apple.take_then_give_back.get_cache_key(self.cherry)
        celery_take_give_back_cherry_key = self.celery.take_then_give_back.get_cache_key(self.cherry)
        self.assertNotEqual(apple_take_give_back_cherry_key, celery_take_give_back_cherry_key)

    def test_same_class_method_name_different_class(self):
        """
        Two different classes with the same class method name should have different cache keys
        """
        apple_add_sweet_cherry_key = self.apple.add_sweet_letter.get_cache_key(self.cherry)
        celery_add_sweet_cherry_key = self.celery.add_sweet_letter.get_cache_key(self.cherry)
        self.assertNotEqual(apple_add_sweet_cherry_key, celery_add_sweet_cherry_key)

    def test_same_static_method_name_different_class_instance_reference(self):
        """
        Two different classes with the same static method name should have different cache keys
        """
        apple_static_method_key = self.apple.static_method.get_cache_key(self.cherry)
        celery_static_method_key = self.celery.static_method.get_cache_key(self.cherry)
        self.assertNotEqual(apple_static_method_key, celery_static_method_key)

    def test_same_static_method_name_different_class_class_reference(self):
        """
        Two different classes with the same static method name should have different cache keys
        """
        fruit_static_method_key = Fruit.static_method.get_cache_key(self.cherry)
        vegetable_static_method_key = Vegetable.static_method.get_cache_key(self.cherry)
        self.assertNotEqual(fruit_static_method_key, vegetable_static_method_key)

    def test_same_function_name_from_module_level(self):
        vegetable_static_method_key = Vegetable.foo.get_cache_key(1, 2)
        module_level_key = foo.get_cache_key(1, 2)
        self.assertNotEqual(vegetable_static_method_key, module_level_key)

    def test_args_kwargs_properly_convert_to_string(self):
        """
        Surface level objects are serialized correctly with default settings...
        """
        self.apple.take_then_give_back(self.cherry)
        apple_take_cherry_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,MyNameIsCherry;'
        self.assertKeyInCache(apple_take_cherry_key)

    def test_dict_args_properly_convert_to_string(self):
        self.apple.take_then_give_back({1: self.cherry})
        hashed_dict_key = sha256(str(1).encode('utf-8')).hexdigest()
        expected_cache_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,,,{0},MyNameIsCherry;'.format(hashed_dict_key)
        self.assertKeyInCache(expected_cache_key)

    def test_dict_args_keep_the_same_order_when_convert_to_string(self):
        dict_arg = {1: self.cherry, 'string': 'ay carambe'}
        self.apple.take_then_give_back(dict_arg)
        expected_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,,,' \
                       '473287f8298dba7163a897908958f7c0eae733e25d2e027992ea2edc9bed2fa8,aycarambe,,' \
                       '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b,MyNameIsCherry;'
        self.assertKeyInCache(expected_key)

    def test_set_args_properly_maintain_order_and_convert_to_string(self):
        self.apple.take_then_give_back({1, 'vegetable', self.cherry})
        expected_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,,' \
                       '4715b734085d8d9c9981d91c6d5cff398c75caf44074851baa94f2de24fba4d7,' \
                       '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b,' \
                       'f8201a5264b6b89b4d92c5bc46aa2e5c3e9610e8fc9ef200df1a39c7f10e7af6;'
        self.assertKeyInCache(expected_key)

    def test_list_args_properly_convert_to_string(self):
        self.apple.take_then_give_back([self.cherry])
        expected_cache_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,,MyNameIsCherry;'
        self.assertKeyInCache(expected_cache_key)

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
        expected_cache_key = 'tests.Meat.get_grams_protein;Chicken:20;'
        self.assertTrue(self.chicken.get_cache_helper_key() in expected_cache_key)
        self.assertKeyInCache(expected_cache_key)

    @patch('tests.Meat.get_grams_protein', return_value=20)
    @patch('cache_helper.utils.get_function_type', return_value='function')
    def test_decorator_only_calls_function_once_if_value_cached(self, _, mock_get_grams_protein):
        """
        If decorated function was already called with same args, decorator won't call wrapped function twice
        """
        # Set qualname since internal function uses it
        mock_get_grams_protein.__qualname__ = 'tests.Meat.get_grams_protein'
        decorated_mock_grams_protein = cached(timeout=5*60)(mock_get_grams_protein)
        decorated_mock_grams_protein(self.chicken)
        # Call the function twice with the same args
        decorated_mock_grams_protein(self.chicken)
        # calling the decorated mock function twice with the same args should only call the mock function once
        # as the return value should be stored inside the cache
        self.assertEqual(mock_get_grams_protein.call_count, 1)

    @patch('tests.Meat.get_grams_protein', return_value=20)
    @patch('cache_helper.utils.get_function_type', return_value='function')
    def test_decorator_only_calls_function_twice_when_supplied_different_args(self, _, mock_get_grams_protein):
        """
        Decorator calls function twice when supplied with different args
        """
        # Set qualname since internal function uses it
        mock_get_grams_protein.__qualname__ = 'tests.Meat.get_grams_protein'
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
        expected_cache_key = 'tests.Meat.get_tastier_option;Chicken:20,MyNameIsCelery;'
        self.assertKeyInCache(expected_cache_key)

    def test_key_for_list_of_cacheable_objects(self):
        """
        Test when a cached function takes in a list of CacheHelperCacheable objects
        """
        Meat.get_protein_sum([self.chicken, self.steak])
        expected_cache_key = 'tests.Meat.get_protein_sum;,Chicken:20,Steak:26;'
        self.assertKeyInCache(expected_cache_key)

    def test_key_for_set_of_cacheable_objects(self):
        """
        Test when a cached function takes in a set of CacheHelperCacheable objects
        """
        Meat.get_protein_sum({self.steak, self.chicken})
        expected_cache_key = 'tests.Meat.get_protein_sum;,' \
                             '6dd472107034f41f27f301ddbcc97ba4bc0d54945e759d170268aa1091c436fe,' \
                             '9ff36157b4df732256fe3b151cbf8a6bdcc22969d4d6ceaad588bccbbd5c942f;'
        self.assertKeyInCache(expected_cache_key)

    def test_key_for_dict_of_cacheable_objects(self):
        """
        Test when a cached function takes in a dict with CacheHelperCacheable objects as keys
        """
        Meat.get_tastier_option({self.chicken: 'Tasty'}, {self.celery: 'Terrible'})
        expected_cache_key = 'tests.Meat.get_tastier_option;' \
                             ',,9ff36157b4df732256fe3b151cbf8a6bdcc22969d4d6ceaad588bccbbd5c942f,Tasty,' \
                             ',,8a332387e40497a972a0ab2099659b49b99be0d00130158f9cb92ecc93ca5b18,Terrible;'
        self.assertKeyInCache(expected_cache_key)

    def test_key_for_function_with_cache_helper_cacheable_object_as_kwarg(self):
        """
        Test when a cached function is called with a CacheHelperCacheable object as a kwarg
        """
        Meat.get_grams_protein(meat=self.chicken)
        expected_cache_key = 'tests.Meat.get_grams_protein;;,meat,Chicken:20'
        self.assertKeyInCache(expected_cache_key)
