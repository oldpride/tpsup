import time


def human_delay(max_delay: int = 3, min_delay: int = 1):
    # default to sleep, 1, 2, or 3 seconds

    if min_delay < 0:
        raise RuntimeError(
            f"min={min_delay} is less than 0, not acceptable. min must >= 0")
    if max_delay < 0:
        raise RuntimeError(
            f"max={max_delay} is less than 0, not acceptable. max must >= 0")
    if max_delay < min_delay:
        raise RuntimeError(f"max ({max_delay}) < min ({min_delay})")
    elif max_delay == min_delay:
        # not random any more
        print(f"like human: sleep seconds = {max}")
        if max_delay > 0:
            time.sleep(max_delay)
    else:
        seconds = int(time.time())
        # random_seconds = (seconds % max) + 1
        random_seconds = (seconds % (max_delay+1-min_delay)) + min_delay
        print(f"like human: sleep random_seconds = {random_seconds}")
        if random_seconds > 0:
            time.sleep(random_seconds)
