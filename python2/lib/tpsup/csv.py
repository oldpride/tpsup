import sys
import re

from pprint import pprint,pformat

# https://pythontips.com/2013/08/04/args-and-kwargs-in-python-explained/
# *args and **kwargs allow you to pass a variable number of arguments to
# a function. What does variable mean here is that you do not know before
# hand that how many arguments can be passed to your function by the user
# so in this case you use these two keywords.
# *args is used to send a non-keyworded variable length argument list to
# the function.
# **kwargs allows you to pass keyworded variable length of arguments to
# a function. You should use **kwargs if you want to handle named arguments
# in a function.

def open_csv(_file, **opt):
    if _file == '-' :
        fo = sys.stdin
        filename = 'stdin'
    else:
        fo = open(_file, 'rb')
        filename = _file
        
    if 'skip' in opt and opt['skip']:
        skip = opt['skip']
    else:
        skip = 0
        
    if 'delimiter' in opt:
        delimiter = opt['delimiter']
    else:
        delimiter = ','
        
    ret = {}
        
    # skip lines if needed
    for count in range(0, skip):
        line = fo.readline()
        
        if not line:
            ret['error'] = filename + " has only " + str(count) \
                           + " lines; but need to skip " + str(skip)
            return ret
    
    header_line = fo.readline()
    
    if not header_line:
        ret['error'] = filename + "missing header"
        return ret
    
    header_line = header_line.rstrip()
    
    ret['columns']   = header_line.split(delimiter)
    ret['delimiter'] = delimiter
    ret['fo']        = fo
    
    return ret
        
def csv_to_struct(_file, **opt):
    if 'verbose' in opt and opt['verbose']:
        print >> sys.stderr, "opt = ", pformat(opt)
        
    ref = open_csv(_file, **opt)
        
    if 'error' in ref:
        if 'verbose' in opt and opt['verbose']:
            print >> sys.stderr, _file + " " + ref['error']
        return ref
    
    columns = ref['columns']
    delimiter = ref['delimiter']
    ifo = ref['fo']
    
    num_of_columns = len(columns)
    inconsistent_line_count = 0
    
    compiled_by_attr = {}
    
    # true/false https://docs.python.org/2/library/stdtypes.html#truth-value-testing
    
    #exec("def test_exp(): return r['alpha'] is 'c'")
    for attr in ['MatchPattern', 'ExcludePattern']:
        if attr in opt and opt[attr] != None:
            array = []
        
            for pattern in opt[attr]:
                compiled = re.compile(pattern)
                array.append(compiled)
        
            compiled_by_attr[attr] = array
        
    if 'verbose' in opt and opt['verbose']:
        print >> sys.stderr, "compiled_by_attr = ", pformat(compiled_by_attr)

    array = []
        
    while 1 :
        line = ifo.readline()
        if not line:
            break
        
        line = line.rstrip()
        
        # https://docs.python.org/2/howto/regex.html
        # match() Determine if the RE matches at the beginning of the string.
        # search() Scan through a string, looking for any location where this RE matches.
        # findall() Find all substrings where the RE matches, and returns them as a list.
        # finditer() Find all substrings where the RE matches, and returns
        # them as an iterator.
        
        if 'MatchPattern' in compiled_by_attr:
            matched = 1

            for compiled in compiled_by_attr['MatchPattern']:
                #if not compiled.match(line):
                if not compiled.search(line):
                    matched = 0
                    break
            if not matched:
                continue
        
        if 'ExcludePattern' in compiled_by_attr:
            excluded = 0
        
            for compiled in compiled_by_attr['ExcludePattern']:
                if compiled.search(line):
                    excluded = 1
                    break
            if excluded:
                continue
        
        cells = line.split(delimiter)
        
        if len(cells) != num_of_columns:
            inconsistent_line_count += 1
        
        # zip will throw away any extra columns
        row = dict(zip(columns, cells))
        
        array.append(row)
        
    if inconsistent_line_count:
        print >> sys.stderr, "found", inconsistent_line_count, \
                            "lines having inconsistent number of columns"
    
    if ifo != sys.stdin:
        ifo.close()
    
    ret = {}
    ret['columns'] = columns
    ret['delimiter'] = delimiter
    ret['array'] = array
    
    return ret

def query_csv(**opt):
    if 'verbose' in opt and opt['verbose']:
        print >> sys.stderr, "opt ="
        print >> sys.stderr, pformat(opt);
        
    #import pdb; pdb.set_trace();
        
    if 'input_type' not in opt:
        return None
        
    if opt['input_type'] == 'file':
        csv_struct = csv_to_struct(opt['input'], **opt)
    elif opt['input_type'] == 'struct':
        csv_struct = opt['input']
        
        for attr in [ 'array', 'columns', 'delimiter' ]:
            if not attr in csv_struct:
                print >> sys.stderr, "opt['struct'] missing key=" + attr
                sys.exit(1)
    else:
        print >>sys.stderr, "unknow input_type=", opt['input_type']
        
    if 'error' in csv_struct:
        return csv_struct
        
    if 'verbose' in opt and opt['verbose']:
        print >> sys.stderr, 'csv_struct = ', pformat(csv_struct)
        
    rows = csv_struct['array']
    columns = csv_struct['columns']
    delimiter = csv_struct['delimiter']
        
    #exec("def test_exp(): return r['alpha'] is 'c'")
    MatchExp = None
    ExcludeExp = None

    for Exp in ['MatchExp', 'ExcludeExp']:
        if (Exp in opt and opt[Exp] != None) :
            uncompiled = "def " + Exp + "(r):\n"
            if ( Exp == 'MatchExp' ) :
                for e in opt[Exp]:
                    uncompiled += "    if not " + e + ":\n"
                    uncompiled += "        return False\n"

                uncompiled += "    return True\n"
            else:
                # Exp == 'ExcludeExp'
                for e in opt[Exp]:
                    uncompiled += "    if " + e + ":\n"
                    uncompiled += "        return True\n"
        
                uncompiled += "    return False\n"
            if 'verbose' in opt and opt['verbose']:
                print >> sys.stderr, Exp, "uncompiled = ", uncompiled

            #exec("def test_exp(r): return "    + opt['MatchExp'])
            exec(uncompiled)
        else:
            if ( Exp == 'MatchExp' ):
                exec("def " + Exp + "(r): return True")
            elif ( Exp == 'ExcludeExp' ):
                exec("def " + Exp + "(r): return False")
        
    temp_fields = []
    func_by_field = {}
        
    if 'TempExp' in opt and opt['TempExp'] != None:
        i=0
        for string in opt['TempExp']:
            m = re.match('^([^=]+)=(.+)', string)
            col = m.group(1)
            exp = m.group(2)
        
            func_name = "ef_" + str(i)
        
            uncompiled = "def " + func_name + "(r): return " + exp
            if 'verbose' in opt and opt['verbose']:
                print >> sys.stderr, "temp col = " + col + " uncompiled = ", uncompiled
        
            exec(uncompiled)
        
            temp_fields.append(col)
        
            exec("func_by_field['" + col + "'] = " + func_name)
        
            i += 1
        
        if 'verbose' in opt and opt['verbose']:
            print >> sys.stderr, "func_by_field = ", pformat(func_by_field)
            print >> sys.stderr, "temp_fields = ", pformat(temp_fields)
        
    if 'fields' in opt and opt['fields']:
        fields = opt['fields'].split(",")
    else:
        fields = columns + temp_fields

    csv_struct2 = {}

    rows2 = []
        
    for row in rows:
        for f in temp_fields:
            func = func_by_field[f]
            row[f] = func(row)
        
        if 'verbose' in opt and opt['verbose']:
            print >> sys.stderr, "row = ", pformat(row);

        # MatchExp() and ExcludeExp() were inserted using exec. TODO: delete this confusion
        if MatchExp(row) and not ExcludeExp(row):
            rows2.append(row)
        
    csv_struct2['array'] = rows2
    csv_struct2['delimiter'] = delimiter
    csv_struct2['columns'] = fields
        
    if 'output' in opt:
        print_csv_dict(csv_struct2['array'], csv_struct2['columns'], opt['output'], **opt)
        
    return csv_struct2
        
def print_csv_dict(_dict_rows, _fields, _output, **opt):
    if 'verbose' in opt and opt['verbose']:
        print >> sys.stderr, "print_csv_dict opt = ", pformat(opt);

    ofo = None

    if _output == '-':
        ofo = sys.stdout
    else:
        ofo = open(_output, 'w')

    odelimiter = None

    if 'odelimiter' in opt and opt['odelimiter'] != None:
        odelimiter = opt['odelimiter']
    elif 'delimiter' in opt and opt['delimiter'] != None:
        odelimiter = opt['delimiter']
    else:
        odelimiter = ','
       
    if 'verbose' in opt and opt['verbose']:
        print >> sys.stderr, "ofo = ", pformat(ofo);
        print >> sys.stderr, "odelimiter = ", odelimiter;

    ofo.write(odelimiter.join(_fields) + "\n")
        
    for row in _dict_rows:
        list = []
        
        for f in _fields:
            if not f in row:
                value = ''
            else:
                value = row[f]
        
            list.append(value) #this does    append '' to the list
            #list += value     #this doesn't append '' to the list
        
        if 'verbose' in opt and opt['verbose']:
            print >> sys.stderr, "print_csv_dict row = ",  pformat(row);
            print >> sys.stderr, "print_csv_dict list = ", pformat(list);
        
        # map(function, iterable) applies a function to every item of the iterable and return a list.
        ofo.write(odelimiter.join(map(str, list)) + "\n")
