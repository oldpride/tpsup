from pprint import pformat
from lxml import html
import os
import re
import requests
import sys
import re
import tpsup.tmptools
from tpsup.logbasic import log_FileFuncLine
import tpsup.human


def get_host_url(url: str):
    if m := re.match(r'^(https?://[^/]+)', url, re.IGNORECASE):
        return m.group(1)
    else:
        return None


def get_url_dir(url: str):
    # https://test.abc.com/~johnsmith/cs102/slides/css/slides.css
    # to https://test.abc.com/~johnsmith/cs102/slides/css
    # https://test.abc.com
    # to https://test.abc.com
    if m := re.match(r'^(https?://.+)/.*', url, re.IGNORECASE):
        return m.group(1)
    else:
        return url


class Crawler:
    def __init__(self,
                 start_url: str,
                 paths: list[str],    # xpath=... css=... id=...
                 maxpage: int = 50,   # max number of pages to download
                 maxdepth: int = 1,   # max depth of the pages to search
                 maxsize: int = 10,   # max size MB of the file to download
                 download_dir: str = None,
                 processed_dir: str = None,
                 breath_first: bool = True,
                 dryrun: bool = False,
                 **opt):
        # trim the ending '/' so that we can add it back later
        self.start_url = start_url.rstrip('/')
        self.paths = paths
        self.maxpage = maxpage
        self.maxdepth = maxdepth
        self.maxsize = maxsize
        self.download_dir = download_dir
        self.processed_dir = processed_dir
        self.breath_first = breath_first
        self.verbose = opt.get('verbose', 0)
        # self.dryrun = dryrun

        # this list can be used as a queue or a stack
        #   if breath_first is True, it is a queue
        #   if breath_first is False, it is a stack
        self.to_crawl_list = [start_url]

        # cache the downloaded files
        self.url_by_local = {}
        self.local_by_url = {}

        # get start_url's host
        self.start_host = None
        if m := re.match(r'^https?://([^/]+)', start_url):
            self.start_host = m.group(1)

        if self.download_dir is None:
            self.download_dir = tpsup.tmptools.get_dailydir() + "/download"
            os.makedirs(self.download_dir, exist_ok=True)
        log_FileFuncLine(f"download_dir = {self.download_dir}")

        if self.processed_dir is None:
            self.processed_dir = tpsup.tmptools.get_dailydir() + "/processed"
            os.makedirs(self.processed_dir, exist_ok=True)
        log_FileFuncLine(f"processed_dir = {self.processed_dir}")

    def get_local_relative_path(self, url: str):
        # map http://example.com/abc/def to abc/def
        # map https://test.abc.com/~johnsmith/cs101/slides/01-course_intro.html#1
        # to cs101/slides/01-course_intro.html
        # map http://samehost.com         to index.html
        # map http://diffhost.com         to diffhost.com/index.html
        # map C:/users/johnsmith/cs101/slides/01-course_intro.html to 01-course_intro.html

        if re.match(r'^https?://', url, re.IGNORECASE):
            if m := re.match(r'^https?://([^/]+)(.*)$', url, re.IGNORECASE):
                host = m.group(1)
                path = m.group(2)

                if path == '' or path == '/':
                    local_relative = 'index.html'
                elif m2 := re.match(r'^/~[^/]+/(.*)$', path):
                    # https://test.abc.com/~johnsmith/cs101/slides/01-course_intro.html#1
                    # to cs101/slides/01-course_intro.html
                    path2 = m2.group(1)
                    if path2 == '' or path2 == '/':
                        local_relative = 'index.html'
                    else:
                        # remove the leading '/'
                        local_relative = path2[1:]
                else:
                    # remove the leading '/'
                    local_relative = path[1:]
            else:
                raise RuntimeError(f"can't parse url {url}")

            if host != self.start_host:
                # change abc.com:8000 to abc.com-8000
                host = re.sub(r':', '-', host)
                local_relative = f"{host}/{local_relative}"

            # remove the trailing '#'
            local_relative = re.sub(r'#.*$', '', local_relative)

            # if there is a trailing '/', convert it to index.html
            if local_relative.endswith('/'):
                local_relative = local_relative + 'index.html'

        else:
            # this is a local file path; this should only happen to the first page
            # ie, start_url
            local_relative = os.path.basename(url)

        return local_relative

    def download_url(
            self,
            url: str,
            maxsizeMB: int = 10,
            humanlike: bool = True,
            **opt) -> str:

        verbose = opt.get('verbose', self.verbose)

        ret = {
            'url': url,
            'abs_local': None,
            'need_process': 1,
            'new_download': 0,

            # files that downloaded in this run but in an early loop
            # doesn't need processing nor downloading.
            #      need_process = 0, new_download = 0
            # files that exist before this run, need processing but not downloading.
            #      need_process = 1, new_download = 0
        }

        if url in self.local_by_url:
            abs_local = self.local_by_url[url]
            if verbose:
                log_FileFuncLine(f"skip downloading {url} to {abs_local} because it is already downloaded")
            ret['abs_local'] = abs_local
            ret['need_process'] = 0
            return ret

        local_relative_path = self.get_local_relative_path(url)
        if verbose:
            log_FileFuncLine(f"local_relative_path = {local_relative_path}, download_dir = {self.download_dir}")

        local_full_path = os.path.join(self.download_dir, local_relative_path)
        if verbose:
            log_FileFuncLine(f"local_full_path = {local_full_path}")

        abs_local = os.path.abspath(local_full_path)

        if abs_local in self.url_by_local:
            url2 = self.url_by_local[abs_local]
            if url2 == url:
                if verbose:
                    log_FileFuncLine(
                        f"skip downloading {url} to {abs_local} because it is already downloaded for {url2}")
                ret['abs_local'] = abs_local
                ret['need_process'] = 0
                return ret
            else:
                raise RuntimeError(
                    f"local file {abs_local} is already used by old {url2}. Can't use it for new {url}")

        self.url_by_local[abs_local] = url
        self.local_by_url[url] = abs_local

        if verbose:
            log_FileFuncLine(f"url_by_local = {pformat(self.url_by_local)}")
            log_FileFuncLine(f"local_by_url = {pformat(self.local_by_url)}")

        total_size = 0
        maxsize = maxsizeMB * 1024 * 1024

        ret['abs_local'] = abs_local

        # if the local file already exists, we don't download it again
        if os.path.exists(abs_local):
            if verbose:
                log_FileFuncLine(f"skip downloading {url} to {abs_local} because it already exists")
            return ret

        log_FileFuncLine(f"downloading {url} to {abs_local}")

        # create parent directory if it does not exist
        parent_dir = os.path.dirname(abs_local)
        if not os.path.exists(parent_dir):
            log_FileFuncLine(f"creating parent directory {parent_dir}")
            os.makedirs(os.path.dirname(abs_local))

        if re.match(r'^https?://', url):
            # add some delay to make it more human like
            if humanlike:
                tpsup.human.human_delay()

            # https://stackoverflow.com/questions/7243750/download-file-from-web-in-python-3
            # https://stackoverflow.com/questions/16694907/how-to-download-large-file-in-python-with-requests-py
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(abs_local, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        total_size += len(chunk)
                        if total_size > maxsize:
                            raise RuntimeError(f"file {abs_local} is too big {total_size} > {maxsize}")
                        f.write(chunk)
        else:
            # assume it is a file
            with open(url, 'rb') as f:
                with open(abs_local, 'wb') as f2:
                    for chunk in iter(lambda: f.read(8192), b''):
                        total_size += len(chunk)
                        if total_size > maxsize:
                            raise RuntimeError(f"file {url} is too big {total_size} > {maxsize}")
                        f2.write(chunk)

        log_FileFuncLine(f"downloaded {url} to {abs_local}")
        ret['new_download'] = 1
        return ret

    def parse_url(self, url: str, **opt):
        verbose = opt.get('verbose', self.verbose)

        if verbose:
            log_FileFuncLine(f"download_url {url}")
        result = self.download_url(url, **opt)

        if result['need_process'] == 0:
            if verbose:
                log_FileFuncLine(f"skip processing {url} because it is already processed")
            return {
                'items': [],
            }

        abs_local = result['abs_local']

        tree = None
        try:
            # pdf file would fail here
            with open(abs_local, 'rb') as f:  # Open the file in binary mode
                page_content = f.read().decode('utf-8')  # Decode the binary content using UTF-8 encoding
                tree = html.fromstring(page_content)
        except Exception as e:
            if verbose:
                log_FileFuncLine(f"cannot parse {abs_local} {e}")
            return {
                'items': [],
            }

        items = []

        # get all the links
        for path in self.paths:
            if m := re.match(r"\s*(xpath|css|id)=(.+)", path):
                path_type = m.group(1)
                path_value = m.group(2)
            else:
                raise RuntimeError(f"unknown path format {path}")

            elements = []
            if path_type == 'xpath':
                elements = tree.xpath(path_value)
            elif path_type == 'css':
                elements = tree.cssselect(path_value)
            elif path_type == 'id':
                elements = tree.xpath(f"//*[@id='{path_value}']")
            else:
                raise RuntimeError(f"unknown path_type {path_type}")

            if verbose:
                log_FileFuncLine(f"path={path}, elements={elements}")

            for e in elements:
                # get the href attribute
                href_raw = e.get('href')
                if href_raw is not None:
                    if verbose:
                        log_FileFuncLine(f"found href={href_raw} in {url}")
                    # download the file

                    if re.match(r'^https?://', href_raw, re.IGNORECASE):
                        href_full = href_raw
                    else:
                        # we need to convert it to an absolute path
                        # so that we can download it.
                        if re.search(r'stylesheet', path_value):
                            # if path is for css stylesheet, the href is a relative path
                            # this href is a relative path, relative to the current url
                            href_full = f"{get_url_dir(url)}/{href_raw}"
                        else:
                            # this href is a relative path, relative to url's host part.

                            host_url = get_host_url(url)
                            if host_url is None:
                                raise RuntimeError(f"can't get host url from {url}")
                            href_full = f"{get_host_url(url)}/{href_raw}"

                    # change the href to "/local_relative_path" because we are going to download it
                    # and run it with local server
                    local_relative_path = self.get_local_relative_path(href_full)

                    # replace href_raw with local_basename.
                    # this way, when we start a local web server, we can serve the local files
                    e.set('href', f"/{local_relative_path}")

                    item = {
                        'url': url,
                        'relative_path': local_relative_path,
                        'href_full': href_full,
                        'href_raw': href_raw,
                    }

                    items.append(item)

        # update the page content tree
        processed_page_content = html.tostring(tree, pretty_print=True)

        local_relative_path = self.get_local_relative_path(url)

        processed_file = os.path.join(self.processed_dir, local_relative_path)

        # create parent directory if it does not exist
        parent_dir = os.path.dirname(processed_file)
        if not os.path.exists(parent_dir):
            log_FileFuncLine(f"creating parent directory {parent_dir}")
            os.makedirs(os.path.dirname(processed_file))

        with open(processed_file, 'wb') as f:
            f.write(processed_page_content)

        return {
            'items': items,
        }

    def crawl(self, **opt):
        verbose = opt.get('verbose', self.verbose)
        page_count = 0

        while page_count < self.maxpage and len(self.to_crawl_list) > 0:
            if self.breath_first:
                # now to_crawl_list is a queue
                # we pop the first element
                try:
                    url2 = self.to_crawl_list.pop(0)
                except:
                    return
            else:
                # now to_crawl_list is a stack
                # we pop the last element
                try:
                    url2 = self.to_crawl_list.pop()
                except:
                    return

            page_count += 1

            if verbose:
                log_FileFuncLine(f"crawl {url2}, page_count={page_count}")

            # download and parse the page

            result = self.parse_url(url2, **opt)

            for item in result['items']:
                href_full = item['href_full']
                self.to_crawl_list.append(href_full)

        #

        start_relative_path = self.get_local_relative_path(self.start_url)

        readme_string = f"""
        To run a local server to view the processed files, you can run the following command:

            $ python -m http.server 8000 -d "{self.processed_dir}"
        
        Then from browser, go to 
        
            http://localhost:8000 
            or
            http://localhost:8000/{start_relative_path}

        """

        # create a README_local_server.md
        readme_file = os.path.join(self.processed_dir, "README_local_server.md")
        with open(readme_file, 'w') as f:
            f.write(readme_string)

        print(readme_string)
        print(f"above message is saved to {readme_file}")


def main():
    #  <li class="next">
    #     <a href="/page/2/">Next <span aria-hidden="true">&rarr;</span></a>
    #  </li>
    #
    # the xpath to next page is //li[@class='next']/a

    # <head>
    # 	<meta charset="UTF-8">
    # 	<title>Quotes to Scrape</title>
    #     <link rel="stylesheet" href="/static/bootstrap.min.css">
    #     <link rel="stylesheet" href="/static/main.css">
    # </head>
    #
    # the xpath to stylesheet is //link[@rel='stylesheet']

    crawler = Crawler(
        start_url="http://quotes.toscrape.com",
        paths=[
            "xpath=//li[@class='next']/a",
            "xpath=//link[@rel='stylesheet']",
        ],
        # maxpage=3,
        # maxdepth=1,
        # maxsize=10, # MB
        # download_dir=None,
        # processed_dir=None,
        # breath_first=True,
        # dryrun=False,
        # verbose=1,
    )

    crawler.crawl()


if __name__ == '__main__':
    main()
