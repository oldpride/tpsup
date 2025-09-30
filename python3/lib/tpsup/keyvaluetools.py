import re
from pprint import pformat
import shlex

test_input = '''
step1=1+2

step2_0="1 line, quoted value, step2_0"
step2_1='double quote " in single-quoted value, step2_1'
step2_2="single quote ' in double-quoted value, step2_2"


"step3=1 line, quoted key and value, step3"

step4='there is a comment after step4' # this is a comment

# step can repeat
step4='step4 repeats'

step5_1='there is a # in the string for step5'
step5_2=css="#nested_shadow_host"
"step5_3=css=#nested_shadow_host"

# multi-line value can be quoted either from key or value side.
step6="this is
multiple lines
step6"

"step7=this is
multiple lines
step7"

# there can be space before each step
# but there is no space around the equal sign
   step8="there can be space before step8"

# empty-value step
step9=""

# allow escape
step10_0=escaped\\ space\\ in\\ step10_0
step10_1=escaped\\ single\\ quote\\ \\'\\ in\\ step10_1
step10_2=escaped\\ double\\ quote\\ \\"\\ in\\ step10_2

# allow escaped quotes. note there is only a single escape char below.
step11_0='escaped \\' in single-quoted step11_0'
step11_1="escaped \\" in double-quoted step11_1"

# value that contains quotes.
"step12='single quote should be preserved in step12'"
'step13="double quote should be preserved in step13"'

# steps without values.
step14

# quoted step without value.
"step15"

# multiple steps without values.
step16 "step17" step18 'step19'

# multiple steps with values.
step20=123 step21="456" step22='789'

# step with quotes in the middle of value, not the same as no step value.
step23=C:/"Program Files"/myapp

# basically the steps should be able to be accepted by bash or batch.

'''

expected_kv_list =  [
    {'key': 'step1',
    'original': 'step1=1+2',
    'token': 'step1=1+2',
    'value': '1+2'},
    {'key': 'step2_0',
    'original': 'step2_0="1 line, quoted value, step2_0"',
    'token': 'step2_0=1 line, quoted value, step2_0',
    'value': '1 line, quoted value, step2_0'},
    {'key': 'step2_1',
    'original': 'step2_1=\'double quote " in single-quoted value, step2_1\'',
    'token': 'step2_1=double quote " in single-quoted value, step2_1',
    'value': 'double quote " in single-quoted value, step2_1'},
    {'key': 'step2_2',
    'original': 'step2_2="single quote \' in double-quoted value, step2_2"',
    'token': "step2_2=single quote ' in double-quoted value, step2_2",
    'value': "single quote ' in double-quoted value, step2_2"},
    {'key': 'step3',
    'original': 'step3=1 line, quoted key and value, step3"',
    'token': 'step3=1 line, quoted key and value, step3',
    'value': '1 line, quoted key and value, step3'},
    {'key': 'step4',
    'original': "step4='there is a comment after step4'",
    'token': 'step4=there is a comment after step4',
    'value': 'there is a comment after step4'},
    {'key': 'step4',
    'original': "step4='step4 repeats'",
    'token': 'step4=step4 repeats',
    'value': 'step4 repeats'},
    {'key': 'step5',
    'original': "step5='there is a # in the string for step5'",
    'token': 'step5=there is a # in the string for step5',
    'value': 'there is a # in the string for step5'},
    {'key': 'step6',
    'original': 'step6="this is\nmultiple lines\nstep6"',
    'token': 'step6=this is\nmultiple lines\nstep6',
    'value': 'this is\nmultiple lines\nstep6'},
    {'key': 'step7',
    'original': 'step7=this is\nmultiple lines\nstep7"',
    'token': 'step7=this is\nmultiple lines\nstep7',
    'value': 'this is\nmultiple lines\nstep7'},
    {'key': 'step8',
    'original': 'step8="there can be space before step8"',
    'token': 'step8=there can be space before step8',
    'value': 'there can be space before step8'},
    {'key': 'step9', 'original': 'step9=""', 'token': 'step9=', 'value': ''},
    {'key': 'step10_0',
    'original': 'step10_0=escaped\\ space\\ in\\ step10_0',
    'token': 'step10_0=escaped space in step10_0',
    'value': 'escaped space in step10_0'},
    {'key': 'step10_1',
    'original': "step10_1=escaped\\ single\\ quote\\ \\'\\ in\\ step10_1",
    'token': "step10_1=escaped single quote ' in step10_1",
    'value': "escaped single quote ' in step10_1"},
    {'key': 'step10_2',
    'original': 'step10_2=escaped\\ double\\ quote\\ \\"\\ in\\ step10_2',
    'token': 'step10_2=escaped double quote " in step10_2',
    'value': 'escaped double quote " in step10_2'},
    {'key': 'step11_0',
    'original': "step11_0='escaped \\' in single-quoted step11_0'",
    'token': "step11_0=escaped ' in single-quoted step11_0",
    'value': "escaped ' in single-quoted step11_0"},
    {'key': 'step11_1',
    'original': 'step11_1="escaped \\" in double-quoted step11_1"',
    'token': 'step11_1=escaped " in double-quoted step11_1',
    'value': 'escaped " in double-quoted step11_1'},
    {'key': 'step12',
    'original': 'step12=\'single quote should be preserved in step12\'"',
    'token': "step12='single quote should be preserved in step12'",
    'value': "'single quote should be preserved in step12'"},
    {'key': 'step13',
    'original': 'step13="double quote should be preserved in step13"\'',
    'token': 'step13="double quote should be preserved in step13"',
    'value': '"double quote should be preserved in step13"'},
    {'key': 'step14', 'original': 'step14', 'token': 'step14', 'value': None},
    {'key': 'step15', 'original': 'step15"', 'token': 'step15', 'value': None},
    {'key': 'step16', 'original': 'step16', 'token': 'step16', 'value': None},
    {'key': 'step17', 'original': 'step17"', 'token': 'step17', 'value': None},
    {'key': 'step18', 'original': 'step18', 'token': 'step18', 'value': None},
    {'key': 'step19', 'original': "step19'", 'token': 'step19', 'value': None},
    {'key': 'step20',
    'original': 'step20=123',
    'token': 'step20=123',
    'value': '123'},
    {'key': 'step21',
    'original': 'step21="456"',
    'token': 'step21=456',
    'value': '456'},
    {'key': 'step22',
    'original': "step22='789'",
    'token': 'step22=789',
    'value': '789'},
    {'key': 'step23',
    'original': 'step23=C:/"Program Files"/myapp',
    'token': 'step23=C:/Program Files/myapp',
    'value': 'C:/Program Files/myapp'},
  ]

# a function to parse the above steps into an array of dict of key-value pairs.
def parse_keyvalue(input: str, **opt):
    '''
    parse a single step string into a dict of key-value pairs.
    '''
    debug = opt.get('debug', 0)

    # use shlex to split the string into tokens, respecting quotes
    lexer = shlex.shlex(input, posix=True)
    lexer.whitespace_split = True

    # https://stackoverflow.com/questions/37814808/shlex-escaping-quotes-in-python-3
    # allow both single and double quotes to be escaped
    #    step11_0='escaped \' in single-quoted step11_0'
    #    step11_1="escaped \" in double-quoted step11_1"
    lexer.escapedquotes = "'\""

    lexer.commenters = '#'
    
    ret = []

    # get the tokens 1 by 1
    last_loc = 0 # last location in the input string
    input_length = len(input) # this is the max location
    while token := lexer.get_token():
        # get the location of the token
        loc = lexer.instream.tell() # location after the token

        # get token length
        token_length = len(token)

        # print how the input looks like at the location
        # context = input[max(0, loc-token_length-3):loc]
        context = input[last_loc:loc]
        if debug:
            print(f"context at token: ...{context}...")
            print(f"token: {token}")
            print()
            print("-------------------------------------------")

        # now we have a token
        detail = {'token': token}
        if '=' in token:
            k, v = token.split('=', 1)
            detail['key'] = k
            detail['value'] = v
            v_lenth = len(v)
        else:
            k = token
            detail['key'] = k
            detail['value'] = None
            v_lenth = 0

        # get the original token string from the context
        # find the key of the token between last_loc and loc - v_length -1 (= char)
        key_start = input.find(k, last_loc, loc - v_lenth - 1)
        original = input[key_start: loc]

        # if we are not at the end of input, and the original was delimited by delimiter.
        # therefore, we trim the last char - the delimiter.
        if loc < input_length:
            original = original[:-1]
        detail['original'] = original
        ret.append(detail)

        last_loc = loc

    if debug:
        print(f"tokens: {pformat(ret)}")

    return ret


def main():
    kv_list = parse_keyvalue(test_input, 
                          debug=1
                          )
    
    print()
    # compare with expected_kv_list
    if len(kv_list) != len(expected_kv_list):
        print(f"length mismatch: got {len(kv_list)}, expected {len(expected_kv_list)}")
    else:
        print(f"length match: {len(kv_list)}")

        all_match = True
        for i, kv in enumerate(kv_list):
            expected = expected_kv_list[i]
            if kv != expected:
                print(f"mismatch at index {i}: got {kv}, expected {expected}")
                all_match = False
        if all_match:
            print("all match!")
    
if __name__ == '__main__':
    main()
