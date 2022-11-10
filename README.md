django-cache-helper
===================

&nbsp;
[![PyPI](https://img.shields.io/pypi/v/django-cache-helper?color=green)](https://pypi.org/project/django-cache-helper/)
[![Test Suite](https://github.com/ycharts/django_cache_helper/actions/workflows/main.yml/badge.svg?branch=master)](https://github.com/ycharts/django_cache_helper/actions/workflows/main.yml)
[![Coverage Status](https://coveralls.io/repos/github/ycharts/django_cache_helper/badge.svg?branch=master)](https://coveralls.io/github/ycharts/django_cache_helper?branch=master)

## Overview
django-cache-helper is a simple tool for making caching functions, methods, and class methods a little bit easier.
It is largely based off of django-cache-utils, however, since cache-utils did not support caching model methods by instance and carried other features I didn't need, django-cache-helper was created.

In order to cache and invalidate a function/method/class_method/static_method:

## Support

| Python |
|--------|
|  3.7, 3.8, 3.9, 3.10      |


#### How to Cache

```python
# Caching a function
@cached(60*60)  # 60 Minutes
def foo(bar):
	return bar

class Incrementer:

    @cached_instance_method(60 * 60)
    def instance_increment_by(self, num):
        return num

    @classmethod
    @cached_class_method(60 * 60)
    def class_increment_by(cls, num):
        return num

    @staticmethod
    @cached(60 * 60)
    def get_datetime():
        return datetime.utcnow()
```

#### How to invalidate a cache

```python

foo(1)
foo.invalidate(1)

Incrementer.instance_increment_by(1)
Incrementer.instance_increment_by.invalidate(1)

Incrementer.class_increment_by(1)
Incrementer.class_increment_by.invalidate(1)

Incrementer.get_datetime()
Incrementer.get_datetime.invalidate()
```


## Contributors ✨

Thanks goes to these wonderful people.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><img src="https://avatars.githubusercontent.com/u/2000316?v=4" width="100px;" alt="Kevin Fox"/><br /><sub><b>Kevin Fox</b></sub></td>
    <td align="center"><img src="https://avatars.githubusercontent.com/u/3022071?v=4" width="100px;" alt="Tom Jakeway"/><br /><sub><b>Tom Jakeway</b></sub></td>
    <td align="center"><img src="https://avatars.githubusercontent.com/u/83293?v=4" width="100px;" alt="Ara Anjargolian"/><br /><sub><b>Ara Anjargolian</b></sub></td>
    <td align="center"><img src="https://avatars.githubusercontent.com/u/15602942?v=4" width="100px;" alt="Hyuckin David Lim"/><br /><sub><b>Hyuckin David Lim</b></sub></td>
    <td align="center"><img src="https://avatars.githubusercontent.com/u/1248116?v=4" width="100px;" alt="James"/><br /><sub><b>James</b></sub></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->
