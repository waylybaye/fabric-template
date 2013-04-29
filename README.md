fabric-template
===============


## Simple Template

Including these stacks:

* nginx
* gunicorn
* supervisord


### Usage

```python
# fabfile.py
from fabric_template.templates import simple

def install():
    simple.create_app('myapp', 'git@github.com:django/djagno-demo.git')

def deploy():
    simple.deploy('myapp')

def status():
    simple.status('myapp')
```
