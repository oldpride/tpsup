from pprint import pformat


class Dummy:
    def __init__(self, arg1, arg2, **opt):
        self.verbose = opt.get("verbose", 0)
        self.driver = {'arg1': arg1, 'arg2': arg2}
        print(f'initiated dummy driver: {pformat(self.driver)}')

    def get_driver(self):
        return self.driver


def get_driver(**args):
    dummy = Dummy(**args)
    return Dummy.get_driver()


def main():
    print(f"call get_driver()")
    driver = Dummy('arg1', 'arg2').get_driver()
    print(f"driver={pformat(driver)}")


if __name__ == "__main__":
    main()
