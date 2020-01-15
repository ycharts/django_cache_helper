[![Build Status](https://travis-ci.org/ycharts/django_cache_helper.svg?branch=master)](https://travis-ci.org/ycharts/django_cache_helper)

django-cache-helper
===================

django-cache-helper is a simple tool for making caching functions, methods, and class methods a little bit easier.
It is largely based off of django-cache-utils, however, since cache-utils did not support caching model methods by instance and carried other features I didn't need, django-cache-helper was created.

In order to cache a function/method/class_method:

```python
@cached(60*60)
def foo(bar):
	return bar

@property
@cached(60*60)
def foo(self):
	return self.id + 2
```
