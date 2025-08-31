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

# basically the steps should be able to be accepted by bash or batch.

'''

# a function to parse the above steps into an array of dict of key-value pairs.
# use regular expression to parse each step.
# because we need to handle escaped quotes, and multi-line strings, 
# we need to parse 1 step at a time.

def parse_steps(input: str, **opt) -> list:
    debug = opt.get('debug', 0)

    steps = []

    while input:
        # now we either just finished a step, or this is the first step.
        if debug > 1:
            print(f"input = {input}")

        
        # skip leading spaces - this could be multiple lines of spaces, including \n
        # note space and comment are intertwined.
        # therefore, we need to loop until we see neither space nor comment.
        seen_space = True
        seen_comment = True
        while seen_space or seen_comment:
            if m := re.match(r'^\s+', input, re.MULTILINE):
                seen_space = True
                input = input[m.end():]
                if debug > 1:
                    print(f"skipped space='<{m.group(0)}>'")
            else:
                seen_space = False
            if not input:
                break
            
            # skip comments. this is not multi-line.
            if m := re.match(r'^#.*', input):
                seen_comment = True
                input = input[m.end():]
                if debug > 1:
                    print(f"skipped comment='<{m.group(0)}>'")
            else:
                seen_comment = False
            if not input:
                break  

        if not input:
            break      

        if input[0] in ('"', "'"):
            # step string is quoted
            #   "step99='value here'"
            quote = input[0]
            esc = False
            for i in range(1, len(input)):
                if esc:
                    esc = False
                elif input[i] == '\\':
                    esc = True
                elif input[i] == quote:
                    # found the matching quote
                    step_string = input[:i+1]

                    # remove the surrounding quotes
                    step_unquoted = step_string[1:-1]
                    
                    # break the step into key and value
                    k, v, *_ = step_unquoted.split('=', 1) + [None]

                    s = {
                        'cmd': k,
                        'arg': v,
                        'original': step_string,
                        }

                    steps.append(s)
                    if debug:
                        print(f"step={step_string}, parsed={pformat(s)}")

                    # set input to the rest of the string
                    input = input[i+1:]
                    break
            else:
                raise RuntimeError(f"unmatched quote in input: {input}")
        else:
            # step string does not start with a quote
            # we need to find the first space or '='
            # if space, this is a step without value
            #    eg, break, continue, refresh
            # if '=', this is a step with value.
            #    eg, step99=value
            # because we allow step without value, we cannot allow space around '='.
            m = re.match(r'^([a-zA-Z0-9_.:-]+?)(\s|=|$)', input)
            if not m:
                raise RuntimeError(f"no '=' found in input: {input}")
            k = m.group(1)
            
            step_string = input[:m.end()]

            # move the 'pointer' to the rest of the string after the key
            input = input[m.end():]

            if not input or m.group(2).isspace():
               # end of input after key, imply step without value.
               v = None
               s = {
                   'cmd': k,
                   'arg': v,
                   'original': step_string,
               }
               steps.append(s)
               if debug:
                   print(f"step={step_string}, parsed={pformat(s)}")

            if not input:
               # end of input. done.
               break
            elif m.group(2).isspace():
               # step without value, continue to next step
               continue
           
            # found '=', now input is the rest of the string after '='
            # now we need to find the end of the value
            if input[0] in ('"', "'"):
                # step value is quoted
                #   step99='value here'
                #   step99="value here"
                quote = input[0]
                esc = False
                for i in range(1, len(input)):
                    if esc:
                        esc = False
                    elif input[i] == '\\':
                        esc = True
                    elif input[i] == quote:
                        # found the matching quote
                        v = input[:i+1]
                        step_string += v

                        # remove the surrounding quotes
                        v = v[1:-1]

                        input = input[i+1:]
                        break
                else:
                    raise RuntimeError(f"unmatched quote in input: {input}")
            else:
                # step value is not quoted
                #   step99=value
                # value is the rest of line after =.
                m = re.match(r'^(.*)', input)
                if not m:
                    raise RuntimeError(f"no value found for key: {k}, at input: {input}")
                v = m.group(1)
                input = input[m.end():]
                step_string += v

            s = {
                'cmd': k,
                'arg': v,
                'original': step_string,
            }
            steps.append(s)
            if debug:
                print(f"step={step_string}, parsed={pformat(s)}")

    return steps

def main():
    steps = parse_steps(test_input)
    print(f"steps = {pformat(steps)}")


    # a step that not ending with a space or newline.
    test_input2 = "step40"
    steps2 = parse_steps(test_input2, debug=1)
    print(f"steps2 = {pformat(steps2)}")

if __name__ == '__main__':
    main()
