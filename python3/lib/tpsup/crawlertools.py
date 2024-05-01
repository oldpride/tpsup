from pprint import pformat
from lxml import html
import os
import re
import requests
import sys
import re
import tpsup.htmltools
import tpsup.tmptools
from tpsup.logbasic import log_FileFuncLine
import tpsup.human


def get_url_host(url: str):
    # https://test.abc.com:8000/def/ghi -> https://test.abc.com
    # https://test.abc.com/~johnsmith/def/ghi -> https://test.abc.com
    if m := re.match(r'^(https?://[^/]+)', url, re.IGNORECASE):
        return m.group(1)


def get_url_base(url: str):
    # https://test.abc.com/def/ghi -> https://test.abc.com
    # https://test.abc.com/~johnsmith/def/ghi -> https://test.abc.com/~johnsmith

    if m := re.match(r'^(https?://[^/]+)(/.*)', url, re.IGNORECASE):
        host_url = m.group(1)
        rest = m.group(2)

        if m2 := re.match(r'^(/~[^/]+)', rest, re.IGNORECASE):
            return f"{host_url}/{m2.group(1)}"
        else:
            return host_url
    elif re.match(r'^(https?://.+)', url, re.IGNORECASE):
        return url
    else:
        raise RuntimeError(f"can't parse url {url}")


def get_url_dirname(url: str):
    # https://test.abc.com/~johnsmith/cs102/slides/css/slides.css
    # to https://test.abc.com/~johnsmith/cs102/slides/css
    # https://test.abc.com
    # to https://test.abc.com
    if m := re.match(r'^(https?://.+)/.*', url, re.IGNORECASE):
        return m.group(1)
    else:
        return url


linkAttribute_by_type = {
    # this is in the <header> section
    # <link rel="stylesheet" href="/static/bootstrap.min.css">
    'stylesheet': 'href',

    # <script src="js/remark.js" type="text/javascript"></script>
    'script': 'src',

    # <img width="220px" alt="general tree" src="img/10/tree-2.jpg">
    'img': 'src',

    # <a href="http://test.abc.com/~johnsmith/cs102/slides/01-course_intro.html#1">
    # <li class="next">
    #     <a href="/page/2/">
    #     Next
    #     <span aria-hidden="true">→</span>
    #     </a>
    # </li>
    'default': 'href',
}


class Crawler:
    def __init__(self,
                 start_url: str,
                 paths: list[str],    # xpath=... css=... id=...

                 # paths for stylesheet, script, img, only take local path, ie, no https?://
                 #  stylesheet_paths: list = ["xpath=//link[@rel='stylesheet']"],
                 #  script_paths: list = ["xpath=//script[@src]"],
                 #  img_paths: list = ["xpath=//img[@src]"],
                 stylesheet_paths: list = ["xpath=//link[@rel='stylesheet' and not(starts-with(@href, 'http'))]"],
                 script_paths: list = ["xpath=//script[@src and not(starts-with(@src, 'http'))]"],
                 img_paths: list = ["xpath=//img[@src and not(starts-with(@src, 'http'))]"],

                 maxpage: int = 50,   # max number of pages to download
                 maxdepth: int = 3,   # max depth of the pages to search
                 maxsize: int = 10,   # max size MB of the file to download
                 download_dir: str = None,
                 processed_dir: str = None,
                 breath_first: bool = True,
                 dryrun: bool = False,
                 download_favicon: bool = True,
                 humanlike: bool = True,
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
        self.humanlike = humanlike
        # self.dryrun = dryrun

        # this list can be used as a queue or a stack
        #   if breath_first is True, it is a queue
        #   if breath_first is False, it is a stack
        self.to_crawl_list = [{'todo_link_full': start_url, 'depth': 0}]

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

        # organize the paths
        self.paths_by_type = {
            'stylesheet': stylesheet_paths,
            'script': script_paths,
            'img': img_paths,
            'default': paths,
        }

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

                    # ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS_HTML&delayStartupUntil=configured
                    # change wierd characters to '-'
                    local_relative = re.sub(r'[^a-zA-Z0-9=./-]', '-', local_relative)
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
                log_FileFuncLine(
                    f"skip downloading {url} to {abs_local} because it is already downloaded and processed")
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
            if self.humanlike:
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

    def parse_url(self, item: dict, **opt):
        verbose = opt.get('verbose', self.verbose)

        url = item['todo_link_full']
        depth = item['depth']
        link_type = item.get('todo_link_type', 'default')

        ret = {
            'items': [],
            'parsed': 0,
        }

        if verbose:
            log_FileFuncLine(f"download_url {url}")
        result = self.download_url(url, **opt)

        if result['need_process'] == 0:
            if verbose:
                log_FileFuncLine(f"skip processing {url} because it is already processed")
            return ret

        abs_local = result['abs_local']

        local_relative_path = self.get_local_relative_path(url)

        processed_file = os.path.join(self.processed_dir, local_relative_path)

        # create parent directory if it does not exist
        parent_dir = os.path.dirname(processed_file)
        if not os.path.exists(parent_dir):
            log_FileFuncLine(f"creating parent directory {parent_dir}")
            os.makedirs(os.path.dirname(processed_file))

        tree = None
        cannot_parse = 0
        try:
            # pdf file would fail here
            with open(abs_local, 'rb') as f:  # Open the file in binary mode
                page_content = f.read().decode('utf-8')  # Decode the binary content using UTF-8 encoding
                tree = html.fromstring(page_content)
        except Exception as e:
            if verbose:
                log_FileFuncLine(f"cannot parse {abs_local} {e}")
            cannot_parse = 1

        if link_type != 'default' or cannot_parse:
            # For css and script, we just copy downloaded file to processed_dir.
            # Ff we load the css or script file into html tree and then write out to a file,
            # the file will be different from the original file.
            # The new file will be an html file, with tags added.
            # The added tag will cause javascript to fail.
            log_FileFuncLine(f"copy {abs_local} to {processed_file}")

            with open(abs_local, 'rb') as f:  # Open the file in binary mode
                with open(processed_file, 'wb') as f2:
                    f2.write(f.read())

            # for now we don't process css and script further
            ret['parsed'] = 1

            # parse stylesheet for more url to download but no need to update current processed file
            # because we only use the relative url.
            if link_type == 'stylesheet':
                # for css, we don't parse it
                log_FileFuncLine(f"copy {abs_local} to {processed_file}")

                with open(abs_local, 'rb') as f:
                    css_string = f.read().decode('utf-8')

                sheet = tpsup.htmltools.parse_css(css_string)
                style_rule = sheet.get('STYLE_RULE', {})
                # '.title-slide': {'background-image': 'url(../img/back1.jpg)',
                #                  'background-size': 'cover',

                for selector, prop in style_rule.items():
                    for prop_name, prop_value in prop.items():
                        if m := re.match(r'url\((.*)\)', prop_value):
                            url2 = m.group(1)
                            if re.match(r'^https?://', url2):
                                # don't download external url
                                if verbose:
                                    log_FileFuncLine(f"skip downloading external url {url2} in {prop}")
                            else:
                                # will download the file
                                if verbose:
                                    log_FileFuncLine(f"need to download {url2} in {abs_local} to {processed_file}")

                                # assume
                                # url = http://test.abc.com/~johnsmith/cs102/slides/css/slides.css
                                # url2 = ../img/back1.jpg
                                # local_relative_path = cs102/slides/css/slides.css
                                # url_dir = http://test.abc.com/~johnsmith/cs102/slides/css
                                # todo_link_full = http://test.abc.com/~johnsmith/cs102/slides/css/../img/back1.jpg
                                # todo_link_raw = ../img/back1.jpg

                                url_dir = get_url_dirname(url)
                                todo_link_full = url_dir + '/' + url2

                                item = {
                                    'parent_url': url,
                                    'parent_relative_path': local_relative_path,
                                    'todo_link_full': todo_link_full,
                                    'todo_link_raw': url2,
                                    'todo_link_type': 'default',
                                    'depth': depth + 1,
                                }

                                # if verbose:
                                log_FileFuncLine(f"append item={pformat(item, width=1)} to ret['items']")

                                ret['items'].append(item)
            return ret

        ret['parsed'] = 1
        for link_type2, paths in self.paths_by_type.items():
            attribute = linkAttribute_by_type[link_type2]
            for path in paths:
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
                    log_FileFuncLine(f"path={path}, elements={pformat(elements, width=1)}")

                for e in elements:
                    # get the href attribute
                    link_raw = e.get(attribute)
                    if link_raw is not None:
                        if verbose:
                            log_FileFuncLine(f"found {attribute}={link_raw} in {url}")
                        # download the file

                        if re.match(r'^https?://', link_raw, re.IGNORECASE):
                            link_full = link_raw
                        elif link_raw.startswith('/'):
                            # absolute path
                            link_full = get_url_base(url) + link_raw
                        else:
                            # relative path
                            link_full = get_url_dirname(url) + '/' + link_raw

                        # change the href to "/local_relative_path" because we are going to download it
                        # and run it with local server
                        local_relative_path = self.get_local_relative_path(link_full)

                        # replace link_raw with local_basename.
                        # this way, when we start a local web server, we can serve the local files
                        if verbose:
                            log_FileFuncLine(
                                f"link_type2={link_type2}, link_raw={link_raw}, link_full={link_full}, local_relative_path={local_relative_path}")
                        if link_type2 != 'default':
                            # for css and script, I only see relative path so far; and it is relative to
                            # the current directory, not base directory. So I don't need to change the link.
                            if verbose:
                                log_FileFuncLine(
                                    f"skip changing {attribute} because link_type={link_type2}")
                        else:
                            e.set(attribute, f"{local_relative_path}")
                            if verbose:
                                log_FileFuncLine(
                                    f"set link {attribute} in processed page: link_raw={link_raw} -> link_full={link_full} -> local_relative_path={local_relative_path}")

                        if depth < self.maxdepth:
                            item = {
                                'parent_url': url,
                                'parent_relative_path': local_relative_path,
                                'todo_link_full': link_full,
                                'todo_link_raw': link_raw,
                                'todo_link_type': link_type2,
                                'depth': depth + 1,
                            }

                            if verbose:
                                log_FileFuncLine(f"append item={pformat(item, width=1)} to ret['items']")
                            ret['items'].append(item)
                        else:
                            if verbose:
                                log_FileFuncLine(
                                    f"skip crawling {link_full} because depth={depth} >= maxdepth={self.maxdepth}")

        else:
            processed_page_content = html.tostring(tree, pretty_print=True)

            # update the page content tree
            with open(processed_file, 'wb') as f:
                f.write(processed_page_content)

        return ret

    def download_favicon(self, **opt):
        # favicon is at /favicon.ico
        # we download it to the root of the processed_dir
        verbose = opt.get('verbose', self.verbose)

        # if the start_url is http://test.abc.com/def/ghi, the favicon is at http://test.abc.com/favicon.ico
        if not re.match(r'^https?://', self.start_url):
            # if the start_url is a local file, we don't download the favicon
            if verbose:
                log_FileFuncLine(f"skip downloading favicon because start_url={self.start_url} is a local file")
            return

        host_url = get_url_host(self.start_url)

        if host_url is None:
            raise RuntimeError(f"skip downloading favicon because start_url={self.start_url} is not a valid url")

        favicon_url = f"{host_url}/favicon.ico"
        favicon_local = os.path.join(self.processed_dir, "favicon.ico")

        if verbose:
            log_FileFuncLine(f"downloading favicon {favicon_url} to {favicon_local}")

        # use requests to download the favicon
        with requests.get(favicon_url, stream=True) as r:
            r.raise_for_status()
            with open(favicon_local, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def crawl(self, **opt):
        verbose = opt.get('verbose', self.verbose)

        page_count = 0

        if self.download_favicon:
            try:
                self.download_favicon(**opt)
            except Exception as e:
                log_FileFuncLine(f"failed to download favicon {e}")
            page_count += 1

        while len(self.to_crawl_list) > 0:

            if self.breath_first:
                # now to_crawl_list is a queue
                # we pop the first element
                try:
                    item = self.to_crawl_list.pop(0)
                except:
                    return
            else:
                # now to_crawl_list is a stack
                # we pop the last element
                try:
                    item = self.to_crawl_list.pop()
                except:
                    return

            if verbose:
                log_FileFuncLine(f"crawl {pformat(item, width=1)}, page_count={page_count}")

            # download and parse the page

            result = self.parse_url(item, **opt)
            if result['parsed'] == 1:
                page_count += 1
            if page_count >= self.maxpage:
                log_FileFuncLine(f"reached maxpage={self.maxpage}")
                break

            # add all items to to_crawl_list
            self.to_crawl_list.extend(result['items'])
            # log_FileFuncLine(f"to_crawl_list = {pformat(self.to_crawl_list, width=1)}")

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
