from pprint import pformat
import re

from lxml import html
import os

path_pattern = '(css|xpath)=(.+)'
compiled_path = re.compile(path_pattern, re.MULTILINE)


def extract_from_html(html_str: str, template: dict, **opt) -> dict:
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
                raise RuntimeError(
                    f"unsupported path type='{ptype}'. only xpath and css are allowed ")
            ret[k] = v
        else:
            raise RuntimeError(
                f"path='{path}' doesn't match expected pattern='{path_pattern}'")

    return ret


def is_string_html(s: str, strict=0, **opt) -> bool:
    # https://stackoverflow.com/questions/24856035
    # this is not accurate at all
    if strict:
        return html.fromstring(s).find('html/body') is not None
    else:
        return html.fromstring(s).find('.//*') is not None


def is_file_html(file: str, **opt) -> bool:
    # make sure the file can be read as text
    s: str = None
    try:
        f = open(file, 'rb')
        s = f.read().decode('utf-8')
    except Exception as e:
        if opt.get('verbose', False):
            print(f"cannot read file {file} {e}")
        return False

    return is_string_html(s, **opt)


def parse_css(string: str):
    # if url is a file, we need to read the file
    # if url is a http url, we need to get the content
    # if url is a css string, we just use it
    if string.startswith('http://') or string.startswith('https://'):
        import requests
        page = requests.get(string)
        css_str = page.content
    elif len(string) < 1000 and os.path.isfile(string):
        with open(string) as file:
            css_str = file.read()
    else:
        css_str = string

    # https://pypi.org/project/cssutils/

    import cssutils

    sheet = cssutils.parseString(css_str)

    d = {}
    for rule in sheet:
        if rule.typeString not in d:
            d[rule.typeString] = {}
        d2 = {}
        if rule.type == rule.STYLE_RULE:

            for property in rule.style:
                d2[property.name] = property.value

            selector = rule.selectorText

            d[rule.typeString][selector] = d2
        else:
            d[rule.typeString] = {
                'cssText': rule.cssText
            }

    return d


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
    # url = f"file:///{os.path.normpath(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html"
    # page = requests.get(url)
    # result = extract_from_html(page.content)

    with open(f"{os.path.normpath(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html") as file:
        html_str = file.read()
        result = extract_from_html(html_str, template)
        print(f"result = {result}")

    import tpsup.testtools

    p3lib = f"{os.path.normpath(os.environ.get('TPSUP'))}/python3/lib/tpsup"

    def test_codes():
        is_string_html("Hello, <b>world</b>") == True
        is_string_html("Hello, world") == False
        is_string_html("<ht fldf d>") == False

        # border between strict and non-strict
        is_string_html("%<D3><EB><E9><E1>") == True
        is_string_html("%<D3><EB><E9><E1>", strict=1) == False

        is_string_html("<html><body><p>hello</p></body></html>", strict=1) == True

        is_file_html(f"{p3lib}/htmltools_test.html", verbose=1) == True
        is_file_html(f"{p3lib}/htmltools_test_from_text.pdf", verbose=1) == False
        is_file_html(f"{p3lib}/htmltools_test_from_image.txt", verbose=1) == False

        re.match(r'^url', parse_css(f"{p3lib}/htmltools_test_css.css")
                 ['STYLE_RULE']['.title-slide']['background-image']) is not None

    tpsup.testtools.test_lines(test_codes)

    # sheet = parse_css(f"{p3lib}/htmltools_test_css.css")
    # # print(f"sheet = {sheet.cssText}")
    # print(f"sheet = {pformat(sheet, width=1)}")


if __name__ == "__main__":
    main()
