import re


def parse_input(input: Union[list, str], **opt):
    if isinstance(input, str):
        input = input.split()

    if not isinstance(input, list):
        raise Exception(
            f'input must be a list or a string, but it is {type(input)}')

    pair_pattern = re.compile(r'(\w+)=(.*)')

    ref = {}

    for pair in input:
        if re.match(r'any|check', re.IGNORECASE):
            return
        elif pair_pattern.match(pair):
            key, value = pair_pattern.match(pair).groups()
            # convert key to upper case so that user can use both upper case and lower case
            # on command line.
            key = key.upper()

            # if qty, remove comma
            if "QTY" in key:
                value = value.replace(',', '')

            ref[key] = value
        else:
            raise Exception(
                f'input must be a list of key=value pairs, but {pair} is not')

    if AliasMap := opt.get('AliasMap', None):
        for alias in AliasMap.keys():
            key = AliasMap[alias]

            uc_alias = alias.upper()
            if uc_alias in ref:
                ref[key] = ref[uc_alias]  # remember key is already upper case

    check_allowed_keys(ref, **opt)

    return ref


def check_allowed_keys(ref: dict, **opt):
    if not (allowed_keys := opt.get('AllowedKeys', None)):
        return

    # check ref is empty
    if not ref:
        return

    allowed = {}
    for key in allowed_keys:
        allowed[key.upper()] = True

    if allowed_keys:
        for key in ref.keys():
            if key not in allowed_keys:
                raise Exception(f'key {key} is not allowed')
    return
