import re

from lxml import html
import requests
import tpsup.env
import os

path_pattern = '(css|xpath)=(.+)'
compiled_path = re.compile(path_pattern, re.MULTILINE)

def extract_from_html(html_str:str, template:dict, **opt)->dict:
    ret = {}

    if not html_str:
        # to avoid: lxml.etree.ParserError: Document is empty
        print("html is empty")
        return ret

    tree = html.fromstring(html_str)
    for t in template:
        k, path = t
        if m := compiled_path.match(path):
            ptype, pvalue = m.groups()
            # print(f"ptype={ptype}, pvalue={pvalue}")
            if ptype == 'xpath':
                v = tree.xpath(pvalue)
            elif ptype == 'css':
                # use xpath is better than css selector because css selector cannot get attribute
                v = tree.cssselect(pvalue)
            else:
                raise RuntimeError(f"unsupported path type='{ptype}'. only xpath and css are allowed ")
            ret[k] = v
        else:
            raise RuntimeError(f"path='{path}' doesn't match expected pattern='{path_pattern}'")

    return ret

def main():
    template = [
        ['user_id_input_id', 'xpath=//*[@id="user id"]/@id'],

        # use xpath is better than cs sselector because css selector cannot get attribute
        # ['expertise_select_id', 'xpath=//*[@id="Expertise"]/@id'],
        ['expertise_select_id', 'css=#Expertise'],

        # get text
        ['user_id_label_text', 'xpath=//label[@for="user id"]/text()']
    ]
    # this doesn't work as requests.get() doesn't know how to get a local file
    # url = f"file:///{tpsup.env.get_native_path(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html"
    # page = requests.get(url)
    # result = extract_from_html(page.content)

    with open(f"{tpsup.env.get_native_path(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html") as file:
        html_str = file.read()
        result = extract_from_html(html_str, template)
        print(f"result = {result}")


if __name__ == "__main__":
    main()