#!/usr/bin/env -S deno run --allow-env --allow-all

import { basename, dirname} from 'node:path';
// https://2ality.com/2022/08/node-util-parseargs.html
import { parseArgs } from 'node:util';

// import { getDateFormatter } from '../lib/date.js';
// import * as date from '../lib/tpsup/date.js';
let TPJSLIB = process.env.TPJSLIB;
if (!TPJSLIB) {
    console.error("TPJSLIB is not defined");
    process.exit(1);
}
TPJSLIB = TPJSLIB.replace('/cygdrive/c/', 'c:/');
const datetools = await import(`file:${TPJSLIB}/datetools.js`);

// get the current program name
const program = process.argv[1];
// console.log(`program=${program}`);

// get the short name of the program
const shortProgram = basename(program);

// get the script's directory
const scriptDir = dirname(program);
// console.log(`scriptDir=${scriptDir}`);

// let prog = `node ${shortProgram}`;
let prog = shortProgram.replace('_cmd.js', '');

function usage(message) {
    console.log(`Usage: ${message}`);

    let text = `
usage
    ${prog} format

    -v|--verbose     verbose mode
    format           date format, such as '\${yyyy}-\${mm}-\${dd} \${HH}:\${MM}:\${SS}'
                     'default' = ${datetools.defaultFormat}
                     available variables: ${datetools.availVars.join(', ')}
example:
    - use default
    ${prog} default

    - for bash, use single quote
    ${prog} '\${yyyy}-\${mm}-\${dd} \${HH}:\${MM}:\${SS}'

    - for windows batch, use double quote
    ${prog} "\${yyyy}-\${mm}-\${dd} \${HH}:\${MM}:\${SS}"
    `;
    
    console.log(text);

    process.exit(1);
}


const options = {
  verbose: {
    type: 'boolean',
    short: 'v',
  },
//   config: {
//     type: 'string',
//     short: 'c',
//   },
};

const { values, positionals } = parseArgs({ options, allowPositionals: true });

// verbose = values.verbose;
if ('verbose' in values) {
    console.log('values:', values);
    console.log('positionals:', positionals);
}

if (positionals.length != 1) {
    usage('wrong number of positional arguments');
}

let format = positionals[0];
if (format == 'default') {
    format = null;
    console.log(`using default format: ${datetools.defaultFormat}`);
}
let formatter = datetools.getDateFormatter(format);
let dateString = formatter();
console.log(dateString);
