from pprint import pformat
import re

usage_by_subject = {
    'i' : '''
        inject python code. examples
        i print("hello world")

    ''',
}

nonstop_step_count = 0

def hit_enter_to_continue(initial_steps=0, helper: dict = {}, message:str = None, verbose=0):
    # helper example, see seleniumtools.py
    # helper = {
    #     'd' : ["dump page", dump, {'driver':driver, 'outputdir_dir' : tmpdir} ],
    # }
    global nonstop_step_count

    ret = {'skip': 0}

    if initial_steps:
        nonstop_step_count = initial_steps

    if nonstop_step_count > 0:
        nonstop_step_count -= 1
        if verbose:
            print(f"step_count left={nonstop_step_count}")
    else:
        while True:
            if message:
                print(message)
            hint = f"Hit Enter=1 step; number=steps; i=inject code; q=quit; s=skip; h=help"
            # if we have custom helper, add them to next line
            if helper:
                hint += ";\n   "
                for k in helper.keys():
                    v = helper[k]
                    # print(f"helper[{k}] = {pformat(v)}")
                    hint += f" {k} - {v['desc']};"

                    if 'usage' in v:
                        usage_by_subject[k] = v['usage']
                # remove last semicolon
                hint = hint[:-1]
            
            hint += " : "

            answer = input(hint)
            # if answer is just Enter, then continue
            if not answer:
                break
            elif m := re.match(r"(\d+)$", answer):
                # even if only capture 1 group, still add *_; other step_count would become list, not scalar
                step_count_str, *_ = m.groups()
                nonstop_step_count = int(step_count_str)
                break
            elif m := re.match("q$", answer):
                print("quit")
                quit(0)  # same as exit
            elif m := re.match("s$", answer):
                print("skip")
                ret['skip'] = 1
                break
            elif m := re.match("[h](.*)", answer):
                # help
                subject = m.group(1).strip()
                
                if not subject:
                    # if subject is not specified, print all subjects
                    for k in usage_by_subject.keys():
                        print(f"{k} {usage_by_subject[k]}")
                elif subject in usage_by_subject.keys():
                    print(f"{subject} {usage_by_subject[subject]}")
                else:
                    print(f"no usage for '{subject}'")
            elif m := re.match("[i]\\s(.*)", answer):
                print("inject code")
                code = m.group(1)
                try:
                    exec(code, globals(), locals())
                except Exception as e:
                    print(f"Error executing code: {e}")
            elif helper:  # test dict empty
                matched_helper = False
                for k in helper.keys():
                    if m := re.match(f"{k}(.*)", answer):
                        v = helper[k]
                        # print(f"matched helper {k} = {v}")
                        arg = m.group(1)
                        # trim whitespace
                        arg = arg.strip()
                    
                        # v[0] is the description, v[1] is the function, v[2] is the args
                        myfunc = v['func']
                        args = v['args']

                        if args.get('fromUser', False):
                            # if args['fromUser'] is True, then get the value from user
                            myfunc(arg)
                        else:
                            myfunc(**args)

                        matched_helper = True
                        break
                if matched_helper:
                    # call recursively to get to the hint line
                    hit_enter_to_continue(initial_steps, helper)
            else:
                print("don't understand, try again")

    return ret
