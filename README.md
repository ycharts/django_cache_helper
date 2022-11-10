django-cache-helper
===================

&nbsp;
![PyPI]()
[![Test Suite]()]()
[![Coverage Status]()]()

## Overview
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
## Support
**Python:** 3.7, 3.8, 3.9, 3.10

**Django:** 3.2

## Contributors ✨

Thanks goes to these wonderful people.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><img src="https://avatars.githubusercontent.com/u/83293?v=4" width="100px;" alt="Ara Anjargolian"/><br /><sub><b>Ara Anjargolian</b></sub></td>
    <td align="center"><img src="https://avatars.githubusercontent.com/u/2000316?v=4" width="100px;" alt="Kevin Fox"/><br /><sub><b>Kevin Fox</b></sub></td>
    <td align="center"><img src="https://avatars.githubusercontent.com/u/3022071?v=4" width="100px;" alt="Tom Jakeway"/><br /><sub><b>Tom Jakeway</b></sub></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->
