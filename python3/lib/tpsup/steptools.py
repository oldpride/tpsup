import re

test_input = '''
step1=1+2

step2="this is 1 line step2"

"step3=this is 1 line step3"

step4='there is a comment after step4' # this is a comment

# step can repeat
step4='step4 repeats'

step5='there is # in the string for step5'

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

# allow escaped quotes
step10='there can be a \\' in step10'
step11="there can be a \\" in step11"

"step12='single quote should be preserved in step12'"
'step13="double quote should be preserved in step13"'

# basically the steps should be able to be accepted by bash or batch.

'''

# a function to parse the above steps into an array of key-value pairs.
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
                    step = input[:i+1]

                    # remove the surrounding quotes
                    step = step[1:-1]
                    
                    # break the step into key and value
                    k, v = step.split('=', 1)

                    steps.append((k, v))
                    if debug:
                        print(f"step={step}, k={k}, v={v}")

                    # set input to the rest of the string
                    input = input[i+1:]
                    break
            else:
                raise RuntimeError(f"unmatched quote in input: {input}")
        else:
            # step string does not start with a quote
            # we need to find the first '='
            m = re.match(r'^([a-zA-Z0-9_.:-]+?)=', input)
            if not m:
                raise RuntimeError(f"no '=' found in input: {input}")
            k = m.group(1)
            input_old = input
            input = input[m.end():]
            if not input:
               raise RuntimeError(f"no value found for key: {k}, at input: {input_old}")
            
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

                        # print(f"v (with quotes) = {v}")

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

            steps.append((k, v))
            if debug:
                print(f"step={k}={v}, k={k}, v={v}")

    return steps

def main():
    steps = parse_steps(test_input, debug=1)
    for k, v in steps:
        print(f"{k}={v}")

if __name__ == '__main__':
    main()
