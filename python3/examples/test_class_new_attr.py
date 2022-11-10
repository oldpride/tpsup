#!/usr/bin/env python3

# https://stackoverflow.com/questions/54358665/python-set-attributes-during-object-creation-in-new
# test set attr in __new__


class TestClass(object):
    def __new__(cls, test_val):
        obj = object().__new__(cls)  # cant pass custom attrs
        object.__setattr__(obj, 'customAttr', test_val)
        return obj


# another way, NOT WORKING!!!
# https://howto.lintel.in/python-__new__-magic-method-explained/
class CustomizeInstance:
    def __new__(cls, a, b):
        instance = super(CustomizeInstance, cls).__new__(cls)
        instance.a = a
        return instance


def main():
    print(TestClass(1))
    print(TestClass(2).__dict__)
    print(TestClass(3).customAttr)
    print(CustomizeInstance(4, 5))
    print(CustomizeInstance(6, 7).a)


if __name__ == '__main__':
    main()
