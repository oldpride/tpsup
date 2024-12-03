# dump we request GET, POST

from pprint import pformat
from flask import Flask, request
app = Flask(__name__)

# https://stackoverflow.com/questions/33662842
# https://www.youtube.com/watch?v=Z1RJmh_OqeA&ab_channel=freeCodeCamp.org


usage = """

Run server in terminal like:
    run with flask command
    for windows: 
        set FLASK_APP=flask_dump.py
    for linux:
        export FLASK_APP=flask_dump.py
    flask run --reload --host "127.0.0.1" --port 5000
or
$ python flask_dump.py

to test:

Send queries like: curl -i http://localhost:5000/?q=q
or 
from browser: file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/flask_dump_test.html


"""

from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    # print out the request data
    if request.method == 'POST':
        # data = request.form['name'] # get the value of 'name' key
        # return jsonify(request.form.to_dict())
        data = request.form.to_dict()
    else:
        data = request.args.to_dict()  

    # data = request.args   

    print(f'data={pformat(data)}')
    return f'received data successfully={pformat(data)}'

if __name__ == '__main__':
    app.run(debug=True)
