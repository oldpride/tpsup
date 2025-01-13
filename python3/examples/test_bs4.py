from bs4 import BeautifulSoup
from pprint import pprint, pformat

html_string = '<div class="login-greeting">Hi LCA Editor Tester,</div>'
soup = BeautifulSoup(html_string, 'html.parser')
print(f"soup = {type(soup)}")

print(f"\nthe children")
pprint(soup.children)
for c in soup.children:
    pprint(c)

print(f"\nthe descendants")
pprint(soup.descendants)
for d in soup.descendants:
    pprint(d)

print(f"\nthe attrs")
for elm in soup():
    # soup is generator
    # elm.attrs is dictionary
    attrs = elm.attrs
    pprint(attrs)

print(f"\nsoup() can be called twice")
for elm in soup():
    attrs = elm.attrs
    pprint(attrs)

