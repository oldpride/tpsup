import array
from typing import Union


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

    # this was originally for socket.sendto(bytes[,flags]), but we also allowed bytearray as input.
    # output will follow input type
    def xor(self, plain_bytes: Union[bytearray, bytes], size: int = -1) -> Union[bytearray, bytes]:
        # multiple type hints use Union()
        # https://stackoverflow.com/questions/48709104/how-do-i-specify-multiple-types-for-a-parameter-using-type-hints
        if size < 0:
            size = len(plain_bytes)
        input_type = type(plain_bytes)

        if self.key_str is None:
            if input_type == bytes:
                return plain_bytes
            else:
                # return a copy of bytearray as it is mutable
                plain_copy = bytearray(size)
                plain_copy[:] = plain_bytes
                return plain_bytes
        else:
            xored_array = bytearray(size)
            i = 0
            for b in plain_bytes:
                i += 1
                if size >= 0 and i > size:
                    break
                xored_array[i - 1] = b ^ self.key_array[self.index]
                self.index += 1
                if self.index == self.key_length:
                    self.index = 0
            # output type follow input
            if input_type == bytes:
                return bytes(xored_array)
            else:
                return xored_array


def main():
    for key in ("abc", ""):
        for t in (bytes, bytearray):
            plain = "hello world"
            encoder = Coder(key)
            decoder = Coder(key)

            # encode() create bytes, immutable.
            if t == bytes:
                encoded_bytes = encoder.xor(plain.encode('utf-8'))
            else:
                encoded_bytes = bytearray(encoder.xor(plain.encode('utf-8')))
            decoded_bytes = decoder.xor(encoded_bytes)
            decoded_str = decoded_bytes.decode('utf-8')
            print(f'key="{key}", type="{str(t)}", plain="{plain}", encoded_len={len(encoded_bytes)}, '
                f'decoded_len={len(decoded_bytes)}, decoded_str="{decoded_str}"'
            )


if __name__ == '__main__':
    main()
