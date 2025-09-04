import re
from pprint import pformat

test_input = '''
step1=1+2

step2="this is 1 line step2"

"step3=this is 1 line step3"

step4='there is a comment after step4' # this is a comment

# step can repeat
step4='step4 repeats'

step5='there is # in the string for step5'

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

# empty step
step9=""

# allow escaped quotes. note there is only a single escape char below.
step10='there can be a \\' in step10'
step11="there can be a \\" in step11"

# value that contains quotes.
"step12='single quote should be preserved in step12'"
'step13="double quote should be preserved in step13"'

# steps without values.
step14

# quoted step without value.
"step15"

# multiple steps without values.
step16 "step17" step18 'step19'

# step with empty value, not the same as no step value.
step20=''

# quoted string in the middle of a step - we do not want to support this.
# because it is too complicated to be useful.
# step21='hello world'message
# step22="hello 
# world"message


# basically the steps should be able to be accepted by bash or batch.

'''

# a function to parse the above steps into an array of dict of key-value pairs.
# use regular expression to parse each step.
# because we need to handle escaped quotes, and multi-line strings, 
# we need to parse 1 step at a time.

def parse_steps(input: str, **opt) -> list:
    debug = opt.get('debug', 0)

    # input must be a string.
    if not isinstance(input, str):
        raise RuntimeError(f"input must be a string, got {type(input)}, input={pformat(input)}")

    # first tokenize the input into steps.
    # a token is a continous string.
    # eg
    #        step99=hello"my
    #        dear"world
    # is a single token.

    # first remove comments and leading/trailing spaces.
    input = skip_leading_spaces_comments(input)

    tokens = []
    current_token = ''
    in_single_quote = False
    in_double_quote = False
    escape = False
    in_comment = False

    for c in input:
        if in_comment:
            if c == '\n':
                in_comment = False
            continue
        elif escape:
            current_token += c
            escape = False
        elif c == '\\':
            current_token += c
            escape = True
        elif c == "'":
            current_token += c
            if not in_double_quote:
                in_single_quote = not in_single_quote
        elif c == '"':
            current_token += c
            if not in_single_quote:
                in_double_quote = not in_double_quote
        elif c in ' \t\r\n#':
            if in_single_quote or in_double_quote:
                current_token += c
            else:
                # end of token
                if current_token:
                    tokens.append(current_token)
                    current_token = ''
                if c == '#':
                    # skip till end of line
                    in_comment = True
                # else skip multiple spaces
        else:
            current_token += c

    if current_token:
        tokens.append(current_token)

    # now parse each token into a step dict.
    steps = []
    for token in tokens:
        token0 = token # original token
        # if a token is wrapped in quotes, remove the quotes.
        if (token[0] == token[-1]) and token[0] in ("'", "'"):
            token = token[1:-1]
        
        # token must not be empty now.
        if not token:
            raise RuntimeError(f"empty token found,token0={pformat(token0)}")
        
        k, v, *_ = token.split('=', 1) + [None]
        
        '''
        v may have quotes, espcially quotes can be in the middle of the multiple lines.
        step99=message"john's book"here 
        cmd=step99
        arg=messagejohn's bookhere
        '''

def skip_leading_spaces_comments(s: str) -> str:
    # skip leading spaces and comments
    while s:
        if s[0] in ' \t\r\n':
            s = s[1:]
        elif s[0] == '#':
            # skip till end of line
            nl_pos = s.find('\n')
            if nl_pos == -1:
                s = ''
            else:
                s = s[nl_pos+1:]
        else:
            break
    return s

test_single_steps = [
    'refresh',
    "js=file2element=test.js",
    "js=console.log('hello world')",
    '''
    js=
    console.log('hello world2')
    console.log('hello world3')
    ''',
]
def parse_single_step(input: str) -> dict:
    if not isinstance(input, str):
        raise RuntimeError(f"input must be a string, got {type(input)}, input={pformat(input)}")
    
    # remove leading spaces
    input = input.lstrip()

    k, v, *_ = input.split('=', 1) + [None]
    s = {
        'cmd': k,
        'arg': v,
        'original': input,
    }

    return s


def main():
    steps = parse_steps(test_input)
    print(f"steps = {pformat(steps)}")

    print()
    # a step that not ending with a space or newline.
    test_input2 = "step40"
    steps2 = parse_steps(test_input2, debug=1)
    print(f"steps2 = {pformat(steps2)}")

    print()
    for s in test_single_steps:
        step = parse_single_step(s)
        print(f"single step: {s} => {pformat(step)}")

if __name__ == '__main__':
    main()
