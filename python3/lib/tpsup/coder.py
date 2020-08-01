import array


# Bytes and bytearray objects contain single bytes – the former is immutable while the latter is a mutable sequence.
# Bytes objects can be constructed the constructor, bytes(), and from literals; use a b prefix with normal string
# syntax: b'hello world'. To construct byte arrays, use the bytearray() function
class Coder:
    ''' shuffle the bits before send the data over network '''
    def __init__(self, key_str: str):
        if not (key_str is None or key_str == ""):
            self.key_str = key_str
            self.key_array = key_str.encode('utf-8')  # convert string to bytes. bytes is immutable
            self.key_length = len(self.key_array)
            self.index = 0  # current char position in key_str
        else:
            self.key_str = None

    def xor(self, plain_bytes: bytearray, size: int = -1, inPlace: bool = False) -> bytearray:
        if size < 0:
            size = len(plain_bytes)

        xored_bytes = None
        if inPlace:
            xored_bytes = plain_bytes
        else:
            xored_bytes = bytearray(size)

        if self.key_str is None:
            if not inPlace:
                # copy bytearray
                # https://stackoverflow.com/questions/10633881/how-to-copy-a-python-bytearray-buffer
                xored_bytes[:] = plain_bytes
        else:
            i = 0
            for b in plain_bytes:
                i+=1
                if size >= 0 and i > size:
                    break
                xored_bytes[i - 1] = b ^ self.key_array[self.index]
                self.index += 1
                if self.index == self.key_length:
                    self.index = 0

        return xored_bytes


def main():
    key_str = "abc"
    plain = "hello world"
    encoder = Coder(key_str)
    decoder = Coder(key_str)

    # encode() create bytes, immutable. therefore, we convert it to bytearray, mutable. we need it be mutable in case
    # we want to change in place.
    encoded_bytes = encoder.xor(bytearray(plain.encode('utf-8')))
    decoded_bytes = decoder.xor(encoded_bytes)
    decoded_str = decoded_bytes.decode('utf-8')
    print(f'plain="{plain}", encoded_len={len(encoded_bytes)}, decoded_len={len(decoded_bytes)}, decoded_str="{decoded_str}"')


if __name__ == '__main__':
    main()