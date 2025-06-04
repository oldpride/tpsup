from pprint import pformat

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
            hint = f"Hit Enter - continue; number - multiple steps; i - inject code; q - quit"
            # if we have custom helper, add them to next line
            if helper:
                hint += ";\n   "
                for k in helper.keys():
                    v = helper[k]
                    # print(f"helper[{k}] = {pformat(v)}")
                    hint += f" {k} - {v['desc']};"
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
                        arg = m.group(1)
                        # trim whitespace
                        arg = arg.strip()
                    
                        # v[0] is the description, v[1] is the function, v[2] is the args
                        func = v['func']
                        args = v['args']

                        if args.get('fromUser', False):
                            # if args['fromUser'] is True, then get the value from user
                            func(arg)
                        else:
                            func(**args)

                        matched_helper = True
                        break
                if matched_helper:
                    # call recursively to get to the hint line
                    hit_enter_to_continue(initial_steps, helper)
            else:
                print("don't understand, try again")

    return ret
