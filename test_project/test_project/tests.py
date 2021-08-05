from unittest.mock import call, patch

from django.test import TestCase
from django.core.cache import cache

from cache_helper.decorators import cached, cached_class_method, cached_instance_method
from cache_helper.interfaces import CacheHelperCacheable

from datetime import datetime


class Incrementer:
    class_counter = 500

    def __init__(self, instance_counter):
        self.instance_counter = instance_counter

    @cached_instance_method(60*60)
    def instance_increment_by(self, num):
        self.instance_counter += num
        return self.instance_counter

    @classmethod
    @cached_class_method(60*60)
    def class_increment_by(cls, num):
        cls.class_counter += num
        return cls.class_counter

    @staticmethod
    @cached(60*60)
    def get_datetime(useless_arg, useless_kwarg=None):
        return datetime.utcnow()

    @staticmethod
    @cached(60*60)
    def func_with_multiple_args_and_kwargs(arg_1, arg_2, kwarg_1=None, kwarg_2='a string'):
        return datetime.utcnow()


class SubclassIncrementer(Incrementer):
    class_counter = 500

    def __init__(self, instance_counter):
        self.instance_counter = instance_counter
        super().__init__(instance_counter)

    @cached_instance_method(60*60)
    def instance_increment_by(self, num):
        self.instance_counter += (num * 10)
        return self.instance_counter

    @classmethod
    @cached_class_method(60*60)
    def class_increment_by(cls, num):
        cls.class_counter += (num * 10)
        return cls.class_counter

    @staticmethod
    @cached(60*60)
    def get_datetime(useless_arg, useless_kwarg=None):
        return datetime.utcnow()


class UnimplementedSubclassIncrementer(Incrementer):
    pass


class AnotherIncrementer:
    class_counter = 500

    def __init__(self, instance_counter):
        self.instance_counter = instance_counter

    @cached_instance_method(60*60)
    def instance_increment_by(self, num):
        self.instance_counter -= num
        return self.instance_counter

    @classmethod
    @cached_class_method(60*60)
    def class_increment_by(cls, num):
        cls.class_counter -= num
        return cls.class_counter

    @staticmethod
    @cached(60*60)
    def get_datetime(useless_arg, useless_kwarg=None):
        return datetime.utcnow()


class CacheableIfSumsAreEqual(CacheHelperCacheable):
    """
    The product of 2 numbers is not guaranteed to be equal if their sums are equal.
    This is a contrived example to test `get_cache_helper_key`
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def get_cache_helper_key(self):
        return 'sum={}'.format(self.x + self.y)

    @cached_instance_method(60*60)
    def get_product(self):
        return self.x * self.y


class CachedInstanceMethodTests(TestCase):

    def tearDown(self):
        super().tearDown()
        cache.clear()

    def test_cached_instance_method_basic(self):
        """
        Tests that calling a cached instance method with the same arguments uses the cached values.
        """
        incrementer = Incrementer(100)

        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(incrementer.instance_increment_by(1), 101)
        self.assertEqual(incrementer.instance_increment_by(2), 103)

        # Stale results are retrieved from the cache instead of calling increment() again
        self.assertEqual(incrementer.instance_increment_by(1), 101)
        self.assertEqual(incrementer.instance_increment_by(2), 103)

    def test_cached_instance_method_with_two_instances_of_same_class(self):
        """
        Tests that two instances of the same class do not clash.
        """
        incrementer_1 = Incrementer(100)
        incrementer_2 = Incrementer(200)

        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(incrementer_1.instance_increment_by(1), 101)
        self.assertEqual(incrementer_1.instance_increment_by(2), 103)

        # Same args, but different instance, so the function actually gets called
        self.assertEqual(incrementer_2.instance_increment_by(1), 201)
        self.assertEqual(incrementer_2.instance_increment_by(2), 203)

        # Stale results for both incrementers now
        self.assertEqual(incrementer_1.instance_increment_by(1), 101)
        self.assertEqual(incrementer_1.instance_increment_by(2), 103)
        self.assertEqual(incrementer_2.instance_increment_by(1), 201)
        self.assertEqual(incrementer_2.instance_increment_by(2), 203)

    def test_cached_instance_methods_with_same_name_subclass(self):
        """
        Tests that two instances, one of which is a subclass of the other, do not clash.
        """
        incrementer_1 = Incrementer(100)
        incrementer_2 = SubclassIncrementer(100)

        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(incrementer_1.instance_increment_by(1), 101)
        self.assertEqual(incrementer_1.instance_increment_by(2), 103)

        # Different instance with same args hasn't been computed before
        self.assertEqual(incrementer_2.instance_increment_by(1), 110)
        self.assertEqual(incrementer_2.instance_increment_by(2), 130)

        # Stale results for both incrementers now
        self.assertEqual(incrementer_1.instance_increment_by(1), 101)
        self.assertEqual(incrementer_1.instance_increment_by(2), 103)
        self.assertEqual(incrementer_2.instance_increment_by(1), 110)
        self.assertEqual(incrementer_2.instance_increment_by(2), 130)

    def test_cached_instance_methods_with_same_name_unimplemented_subclass(self):
        """
        Tests that two instances, one of which is an unimplemented subclass of the other, do not clash.
        """
        incrementer_1 = Incrementer(100)
        incrementer_2 = UnimplementedSubclassIncrementer(100)

        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(incrementer_1.instance_increment_by(1), 101)
        self.assertEqual(incrementer_1.instance_increment_by(2), 103)

        # Different instance with same args hasn't been computed before
        self.assertEqual(incrementer_2.instance_increment_by(2), 102)
        self.assertEqual(incrementer_2.instance_increment_by(1), 103)

        # Stale results for both incrementers now
        self.assertEqual(incrementer_1.instance_increment_by(1), 101)
        self.assertEqual(incrementer_1.instance_increment_by(2), 103)
        self.assertEqual(incrementer_2.instance_increment_by(2), 102)
        self.assertEqual(incrementer_2.instance_increment_by(1), 103)

    def test_cached_instance_method_with_same_name_different_class(self):
        """
        Tests that two instances of different classes with the same method name do not clash.
        """
        incrementer_1 = Incrementer(100)
        incrementer_2 = AnotherIncrementer(100)

        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(incrementer_1.instance_increment_by(1), 101)
        self.assertEqual(incrementer_1.instance_increment_by(2), 103)

        # Different instance with same args hasn't been computed before
        self.assertEqual(incrementer_2.instance_increment_by(1), 99)
        self.assertEqual(incrementer_2.instance_increment_by(2), 97)

        # Stale results for both incrementers now
        self.assertEqual(incrementer_1.instance_increment_by(1), 101)
        self.assertEqual(incrementer_1.instance_increment_by(2), 103)
        self.assertEqual(incrementer_2.instance_increment_by(1), 99)
        self.assertEqual(incrementer_2.instance_increment_by(2), 97)

    def test_invalidate_instance_method(self):
        """
        Tests that invalidate works on an instance method
        """
        incrementer = Incrementer(100)

        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(incrementer.instance_increment_by(1), 101)
        self.assertEqual(incrementer.instance_increment_by(2), 103)

        # Stale results are retrieved from the cache instead of calling increment() again
        self.assertEqual(incrementer.instance_increment_by(1), 101)
        self.assertEqual(incrementer.instance_increment_by(2), 103)

        # invalidate 1
        incrementer.instance_increment_by.invalidate(1)

        # 1 gets recomputed
        self.assertEqual(incrementer.instance_increment_by(1), 104)

        # but 2 is still stale
        self.assertEqual(incrementer.instance_increment_by(2), 103)


class CachedClassMethodTests(TestCase):

    def tearDown(self):
        super().tearDown()

        Incrementer.class_counter = 500
        SubclassIncrementer.class_counter = 500
        UnimplementedSubclassIncrementer.class_counter = 500
        AnotherIncrementer.class_counter = 500

        cache.clear()

    def test_cached_class_method_basic(self):
        """
        Tests that calling a cached class method with the same arguments uses the cached values.
        """
        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)

        # Stale results are retrieved from the cache instead of calling class_increment_by again
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)

    def test_cached_class_method_from_instance_and_class(self):
        """
        Tests that it does not matter if you call the class method through an instance or the class itself.
        """
        incrementer_instance = Incrementer(100)

        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(incrementer_instance.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)

        # Stale results are retrieved from the cache instead of calling class_increment_by again
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(incrementer_instance.class_increment_by(2), 503)

    def test_cached_class_methods_with_same_name_subclass(self):
        """
        Tests that two instances, one of which is a subclass of the other, do not clash.
        """
        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)

        # Different class with same args hasn't been computed before
        self.assertEqual(SubclassIncrementer.class_increment_by(1), 510)
        self.assertEqual(SubclassIncrementer.class_increment_by(2), 530)

        # Stale results for both Incrementers now
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)
        self.assertEqual(SubclassIncrementer.class_increment_by(1), 510)
        self.assertEqual(SubclassIncrementer.class_increment_by(2), 530)

    def test_cached_class_methods_with_same_name_unimplemented_subclass(self):
        """
        Tests that two instances, one of which is an unimplemented subclass of the other, do not clash.
        """
        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)

        # Stale results since the subclass has not implemented its own class_increment_by method
        self.assertEqual(UnimplementedSubclassIncrementer.class_increment_by(2), 503)
        self.assertEqual(UnimplementedSubclassIncrementer.class_increment_by(1), 501)

        # Stale results for both Incrementers now
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)
        self.assertEqual(UnimplementedSubclassIncrementer.class_increment_by(1), 501)
        self.assertEqual(UnimplementedSubclassIncrementer.class_increment_by(2), 503)

    def test_cached_class_method_with_same_name_different_class(self):
        """
        Tests that two instances of different classes with the same method name do not clash.
        """
        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)

        # Different class with same args hasn't been computed before
        self.assertEqual(AnotherIncrementer.class_increment_by(1), 499)
        self.assertEqual(AnotherIncrementer.class_increment_by(2), 497)

        # Stale results for both Incrementers now
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)
        self.assertEqual(AnotherIncrementer.class_increment_by(1), 499)
        self.assertEqual(AnotherIncrementer.class_increment_by(2), 497)

    def test_invalidate_class_method(self):
        """
        Tests that invalidate works on an class method
        """
        # Hasn't been computed before, so the function actually gets called
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)

        # Stale results are retrieved from the cache instead of calling increment() again
        self.assertEqual(Incrementer.class_increment_by(1), 501)
        self.assertEqual(Incrementer.class_increment_by(2), 503)

        # invalidate 1
        Incrementer.class_increment_by.invalidate(1)

        # 1 gets recomputed
        self.assertEqual(Incrementer.class_increment_by(1), 504)

        # but 2 is still stale
        self.assertEqual(Incrementer.class_increment_by(2), 503)


class CachedStaticMethodTests(TestCase):

    def tearDown(self):
        super().tearDown()
        cache.clear()

    def test_cached_static_method_basic(self):
        """
        Tests that calling a cached static method with the same arguments uses the cached values.
        """
        # Hasn't been computed before, so the function actually gets called
        initial_datetime_1 = Incrementer.get_datetime(1)
        initial_datetime_2 = Incrementer.get_datetime(2)
        self.assertNotEqual(initial_datetime_1, initial_datetime_2)

        # Stale results are retrieved from the cache instead of calling inner_func() again
        cached_datetime_1 = Incrementer.get_datetime(1)
        cached_datetime_2 = Incrementer.get_datetime(2)
        self.assertEqual(initial_datetime_1, cached_datetime_1)
        self.assertEqual(initial_datetime_2, cached_datetime_2)

    def test_cached_static_methods_with_same_name_subclass(self):
        """
        Tests that a subclass with a different implementation of the cached method does not clash.
        """
        # Hasn't been computed before, so the function actually gets called
        initial_datetime_1 = Incrementer.get_datetime(1)
        initial_datetime_2 = Incrementer.get_datetime(2)
        self.assertNotEqual(initial_datetime_1, initial_datetime_2)

        # Hasn't been computed before, so the function actually gets called
        initial_subclass_datetime_1 = SubclassIncrementer.get_datetime(1)
        initial_subclass_datetime_2 = SubclassIncrementer.get_datetime(2)
        self.assertNotEqual(initial_subclass_datetime_1, initial_subclass_datetime_2)
        self.assertNotEqual(initial_datetime_1, initial_subclass_datetime_2)
        self.assertNotEqual(initial_datetime_2, initial_subclass_datetime_2)

        # Stale results are retrieved from the cache instead of calling utc_now() again
        self.assertEqual(Incrementer.get_datetime(1), initial_datetime_1)
        self.assertEqual(Incrementer.get_datetime(2), initial_datetime_2)
        self.assertEqual(SubclassIncrementer.get_datetime(1), initial_subclass_datetime_1)
        self.assertEqual(SubclassIncrementer.get_datetime(2), initial_subclass_datetime_2)

    def test_cached_static_methods_with_same_name_unimplemented_subclass(self):
        """
        Tests that a subclass with the same implementation of the cached method does not clash.
        """
        # Hasn't been computed before, so the function actually gets called
        initial_datetime_1 = Incrementer.get_datetime(1)
        initial_datetime_2 = Incrementer.get_datetime(2)
        self.assertNotEqual(initial_datetime_1, initial_datetime_2)

        # Stale results since the subclass has not implemented its own class_increment_by method
        initial_subclass_datetime_1 = UnimplementedSubclassIncrementer.get_datetime(1)
        initial_subclass_datetime_2 = UnimplementedSubclassIncrementer.get_datetime(2)
        self.assertEqual(initial_datetime_1, initial_subclass_datetime_1)
        self.assertEqual(initial_datetime_2, initial_subclass_datetime_2)

        # Stale results are retrieved from the cache instead of calling utc_now() again
        self.assertEqual(Incrementer.get_datetime(1), initial_datetime_1)
        self.assertEqual(Incrementer.get_datetime(2), initial_datetime_2)
        self.assertEqual(UnimplementedSubclassIncrementer.get_datetime(1), initial_datetime_1)
        self.assertEqual(UnimplementedSubclassIncrementer.get_datetime(2), initial_datetime_2)

    def test_cached_static_method_with_same_name_different_class(self):
        """
        Tests two classes with the same static method name do not clash.
        """
        # Hasn't been computed before, so the function actually gets called
        initial_datetime_1 = Incrementer.get_datetime(1)
        initial_datetime_2 = Incrementer.get_datetime(2)
        self.assertNotEqual(initial_datetime_1, initial_datetime_2)

        # Hasn't been computed before, so the function actually gets called
        initial_another_datetime_1 = AnotherIncrementer.get_datetime(1)
        initial_another_datetime_2 = AnotherIncrementer.get_datetime(2)
        self.assertNotEqual(initial_another_datetime_1, initial_another_datetime_2)
        self.assertNotEqual(initial_datetime_1, initial_another_datetime_2)
        self.assertNotEqual(initial_datetime_2, initial_another_datetime_2)

        # Stale results are retrieved from the cache instead of calling utc_now() again
        self.assertEqual(Incrementer.get_datetime(1), initial_datetime_1)
        self.assertEqual(Incrementer.get_datetime(2), initial_datetime_2)
        self.assertEqual(AnotherIncrementer.get_datetime(1), initial_another_datetime_1)
        self.assertEqual(AnotherIncrementer.get_datetime(2), initial_another_datetime_2)

    def test_invalidate_static_method(self):
        """
        Tests that invalidate works on an class method
        """
        # Hasn't been computed before, so the function actually gets called
        initial_datetime_1 = Incrementer.get_datetime(1)
        initial_datetime_2 = Incrementer.get_datetime(2)
        self.assertNotEqual(initial_datetime_1, initial_datetime_2)

        # Stale results are retrieved from the cache instead of calling inner_func() again
        cached_datetime_1 = Incrementer.get_datetime(1)
        cached_datetime_2 = Incrementer.get_datetime(2)
        self.assertEqual(initial_datetime_1, cached_datetime_1)
        self.assertEqual(initial_datetime_2, cached_datetime_2)

        # Invalidate 1
        Incrementer.get_datetime.invalidate(1)

        # 1 gets recomputed
        self.assertNotEqual(Incrementer.get_datetime(1), initial_datetime_1)

        # but 2 is still stale
        self.assertEqual(Incrementer.get_datetime(2), initial_datetime_2)


class CacheHelperCacheableTests(TestCase):

    def tearDown(self):
        super().tearDown()
        cache.clear()

    def test_cache_helper_cacheable_on_instance_method(self):
        obj_1 = CacheableIfSumsAreEqual(3, 7)  # sum=10
        obj_2 = CacheableIfSumsAreEqual(4, 6)  # sum=10

        # sum=10 hasn't been an arg before, so the product gets computed
        self.assertEqual(obj_1.get_product(), 21)

        # obj_1 and obj_2 are considered the same because their sums are equal.
        # So this returns cached value of 21 rather than recomputing get_product and getting 24
        self.assertEqual(obj_2.get_product(), 21)

        # obj_3 has a different sum than obj_1 so get_product gets computed correctly
        obj_3 = CacheableIfSumsAreEqual(4, 7)
        self.assertEqual(obj_3.get_product(), 28)

    def test_cache_helper_cacheable_on_static_method_as_arg(self):
        """
        Tests that calling a cached class method with the same arguments uses the cached values.
        """
        obj_1 = CacheableIfSumsAreEqual(1, 3)  # sum = 4
        obj_2 = CacheableIfSumsAreEqual(1, 2)  # sum = 3
        obj_3 = CacheableIfSumsAreEqual(2, 2)  # sum = 4

        # sum=4 gets computed for the first time
        initial_datetime_1 = Incrementer.get_datetime(obj_1)

        # sum=3 gets computed for the first time
        initial_datetime_2 = Incrementer.get_datetime(obj_2)
        self.assertNotEqual(initial_datetime_1, initial_datetime_2)

        # Since obj_1 and obj_3 are considered the same, we get the cached value
        self.assertEqual(Incrementer.get_datetime(obj_3), initial_datetime_1)

    def test_cache_helper_cacheable_on_static_method_as_kwarg(self):
        """
        Tests that calling a cached class method with the same arguments uses the cached values.
        """
        obj_1 = CacheableIfSumsAreEqual(1, 3)  # sum = 4
        obj_2 = CacheableIfSumsAreEqual(1, 2)  # sum = 3
        obj_3 = CacheableIfSumsAreEqual(2, 2)  # sum = 4

        # Hasn't been computed before, so the function actually gets called
        initial_datetime_1 = Incrementer.get_datetime(0, useless_kwarg=obj_1)
        initial_datetime_2 = Incrementer.get_datetime(0, useless_kwarg=obj_2)
        self.assertNotEqual(initial_datetime_1, initial_datetime_2)

        # Since obj_1 and obj_3 are considered the same, we get the cached value
        self.assertEqual(Incrementer.get_datetime(0, useless_kwarg=obj_3), initial_datetime_1)

    def test_arg_order_matters(self):
        """
        Tests that calling a cached class method with the same arguments uses the cached values.
        """
        obj_1 = CacheableIfSumsAreEqual(1, 3)  # sum = 4
        obj_2 = CacheableIfSumsAreEqual(2, 2)  # sum = 4

        # Hasn't been computed before, so the function actually gets called
        initial_datetime_1 = Incrementer.func_with_multiple_args_and_kwargs(0, 'a', kwarg_1=obj_1)
        initial_datetime_2 = Incrementer.func_with_multiple_args_and_kwargs(0, 'a', kwarg_1=obj_2)
        self.assertEqual(initial_datetime_1, initial_datetime_2)

        swapped_arg_datetme = Incrementer.func_with_multiple_args_and_kwargs('a', 0, kwarg_1=obj_1)

        # Since obj_1 and obj_3 are considered the same, we get the cached value
        self.assertNotEqual(initial_datetime_1, swapped_arg_datetme)

    def test_kwarg_order_does_not_matter(self):
        """
        Tests that calling a cached class method with the same arguments uses the cached values.
        """
        obj_1 = CacheableIfSumsAreEqual(1, 3)  # sum = 4

        # Hasn't been computed before, so the function actually gets called
        initial_datetime_1 = Incrementer.func_with_multiple_args_and_kwargs(0, 'a', kwarg_1=obj_1, kwarg_2='hmm')
        initial_datetime_2 = Incrementer.func_with_multiple_args_and_kwargs(0, 'a', kwarg_2='hmm', kwarg_1=obj_1)
        self.assertEqual(initial_datetime_1, initial_datetime_2)
