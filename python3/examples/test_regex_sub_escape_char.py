import re
import os
# path = "C:\\users\\myname"
path = os.environ['TPSUP']
print(path)

if "\\" in path:
    path = path.replace("\\", "\\\\")
    print(path)

# output = re.sub('var', fr'{path}', 'path=var')
output = re.sub('var', path, 'path=var')
# output=re.sub(r'var', r"C:\users\myname", r'path=var')
# output = re.sub('var', "C:\users\myname", 'path=var')
# output = re.sub('var', r"C:\\users\\myname", 'path=var')


print(output)
