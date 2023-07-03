from pprint import pformat


class Dummy:
    def __init__(self, arg1=1, **opt):
        self.verbose = opt.get("verbose", 0)
        self.driver = {'arg1': arg1}
        print(f'initiated dummy driver: {pformat(self.driver)}')

    def get_driver(self):
        return self.driver

    def quit_driver(self):
        self.driver = None
        print(f'quit dummy driver: {pformat(self.driver)}')


def get_driver(**args):
    dummy = Dummy(**args)
    return dummy.get_driver()


def pre_batch(all_cfg, **opt):  # known is not available to pre_batch()
    verbose = opt.get('verbose', 0)
    print(f'calling pre_batch()')
    if not 'driver' in all_cfg["resources"]["dummy"]:
        print('we start driver at a delayed time')
        method = all_cfg["resources"]["dummy"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["dummy"]["driver_call"]["kwargs"]
        all_cfg["resources"]["dummy"]['driver'] = method(**kwargs)


def post_batch(all_cfg, known, **opt):
    verbose = opt.get('verbose', 0)
    print(f'calling post_batch()')
    if 'driver' in all_cfg["resources"]["dummy"]:
        all_cfg["resources"]["dummy"]["driver"] = None
        # delete driver so that it will be re-created next time.
        all_cfg["resources"]["dummy"].pop('driver')


tpbatch = {
    'pre_batch': pre_batch,
    'post_batch': post_batch,
    'extra_args': {
        'dummyarg1': {'dest': ['-da1', '-dummyarg1'], 'default': False,
                      'action': 'store_true', 'help': 'dummyarg1 in dummytools.py'},
        'dummyarg2': {'dest': ['-da2', '-dummyarg2'], 'default': False,
                      'action': 'store_true', 'help': 'dummyarg2 in dummytools.py'},
    },
}


def main():
    print(f"call get_driver()")
    driver = Dummy('arg1', 'arg2').get_driver()
    print(f"driver={pformat(driver)}")


if __name__ == "__main__":
    main()
