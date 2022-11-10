import logging

default = {
    # %(msecs)03d, pad with 0
    'format': '%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s',
    'datefmt': '%Y%m%d:%H:%M:%S',
    'level':'INFO',
    'filename': None
}

def get_logger (name:str = None, **kwargs):
    if not name:
        name = __name__
    setting = dict(default)
    setting.update(**kwargs)
    logging.basicConfig(**setting)
    return logging.getLogger(name) # once you get the logger, you cannot change it. but you can get a new one with new name


def main():
    logger = get_logger()
    logger.debug("This is a debug log")
    logger.info("This is an info log")
    logger.critical("This is critical")
    logger.error("An error occurred")

    logger.setLevel(level='WARN')
    logger.info("I should not see this line")

    # logging.basicConfig(level="DEBUG")
    logger2 = get_logger('new')
    logger2.info("I should see this line")

if __name__ == '__main__':
    main()
