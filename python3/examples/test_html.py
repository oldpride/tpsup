#!/usr/bin/env python3


from lxml.html import parse


def main():
    doc = parse('http://www.google.com').getroot()
    for div in doc.cssselect('a'):
        print(f'{div.text_content()}, {div.get("href")}')


if __name__ == '__main__':
    main()