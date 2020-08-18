import sys
import tarfile
import os
import tpsup.tptmp
import tpsup.env
from typing import List

def create_tar_from_dir_root(tar_name:str, dir:str):
    """
    cd to the dir and then tar all files
    :param tar_name:
    :param dir:
    :return:
    """
    def my_filter(tarinfo: tarfile.TarInfo):
        if tarinfo.isfile() or tarinfo.isdir():
            # only handle basic file types for now
            return tarinfo
        else:
            return None

    saved_pwd = os.getcwd()
    os.chdir(dir)

    tar = None
    try:
        tar = tarfile.open(tar_name, "w")
    except Exception as e:
        os.chdir(saved_pwd)
        raise e

    for name in os.listdir():
        # os.listdir() default to path=., and exclude . and ..
        try:
            tar.add(name, filter=my_filter)
            # tar.add() default to add dir recursively
            # tar will skip the file when filter function returns None
        except OSError as e:
            # accept errors like symbolic link
            # OSError: [Errno 22] Invalid argument: 'link_a.txt'
            print(e, file=sys.stderr)

    tar.close()
    os.chdir(saved_pwd)

def create_tar_from_string(tar_name: str, short_name:str, string: str):
    """
    :param tar_name:
    :param short_name: this is the file name that we can extract from the tar_name
    :param string:
    :return:
    """
    dir = tpsup.tptmp.tptmp().get_nowdir()
    saved_pwd = os.getcwd()
    try:
        os.chdir(dir)
        fh = open(short_name, "w")
        fh.write(string)
        fh.close()
    finally:
        os.chdir(saved_pwd)

    create_tar_from_dir_root(tar_name, dir)


def extract_tar_to_string(tar_name:str, file_name:str, encoding:str = 'utf-8') -> str:
    with tarfile.open(tar_name, "r") as tar:
        # tar.extractfile(file_name) returs an io.BufferedReader
        reader = tar.extractfile(file_name)
        return reader.read().decode(encoding)


def main():
    verbose = 1

    env = tpsup.env.Env()

    dir = os.path.join(env.home_dir, "testdir")
    tar_name = os.path.join(env.home_dir, "junk.tar")
    print(f"\n----------- create {tar_name} from a dir root {dir}")
    create_tar_from_dir_root(tar_name, dir)

    test_str = "hello world"
    tar_name = os.path.join(env.home_dir, "junk2.tar")
    short_name = "short.txt"
    print(f"\n----------- create {tar_name} containing {short_name} from a test string: {test_str}")
    create_tar_from_string(tar_name, short_name, test_str)

    tar_name = os.path.join(env.home_dir, "junk2.tar")
    short_name = "short.txt"
    print(f"\n----------- extract {tar_name}'s {short_name} to a string")
    print(f"{extract_tar_to_string(tar_name, short_name)}")

if __name__ == '__main__':
    main()
