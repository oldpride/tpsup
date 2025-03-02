function f1(a, b) { return a + b; };
var c = 2;

function test_1_line(line, opt) {
    'use strict';
    let verbose = opt && 'verbose' in opt && opt.verbose;
    // let source_code = `return ${line}`;
    // let source_code = `c+1;`;
    // if (verbose) {
    //     console.log(`source_code = ${source_code}`)
    // }

    // this cannot resolve global variables somehow
    // let f = new Function(source_code);
    // let result = f();
    // console.log(`result = ${result}`)

    let result = eval(line);


    return result;
}

let module = null;
async function test_lines(test_codes, url, opt) {
    // we make mdoule global because eval() sometimes only works with global variables.
    module = await import(url);

    // 'use strict';
    let verbose = opt && 'verbose' in opt && opt.verbose;
    let lines = test_codes.toString().split('\r\n'); // ^M
    if (verbose) {
        console.log(`test_codes=\n${test_codes.toString()}`);
        console.log(`lines=\n${lines.join('\n')}`);
        console.log(`lines.length=${lines.length}`);
    }

    // remove first line (function definition) and last line (closing brace)
    lines = lines.slice(1, lines.length - 1);

    if (verbose) {
        console.log(`trimmed lines=\n${lines.join('\n')}`);
    }

    for (let line of lines) {
        // remove comments
        line = line.replace(/\/\/.*/, '');

        // remove empty lines
        if (line.match(/^\s*$/)) {
            continue;
        }

        // trim blanks at the beginning and end
        line = line.trim();

        if (verbose) {
            console.log(`test line=${line}`);
        }

        let r = test_1_line(line, opt);
        console.log(`test=${line}\nresult=${r}\n`);
    }
}

export { test_lines};


if (process.argv[1] === import.meta.filename) {
    let test_codes = () => {
        c + 1;
        c + 1 == 3;
        f1(1, 2);
        f1(1, 2) == 3;
        f1('a', 'b') == 'ab';

    }
    test_lines(test_codes, { verbose: true });
} 
