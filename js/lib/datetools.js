

// cache
let Formatter_by_format = {};
// let timezoneOffsetMinutes = (new Date()).getTimezoneOffset();
// let timezoneName = Intl.DateTimeFormat().resolvedOptions().timeZone;
let defaultFormat = '${yyyy}-${mm}-${dd} ${HH}:${MM}:${SS}.${ms}';
let availVars = ['yyyy', 'mm', 'dd', 'HH', 'MM', 'SS', 'ms', 'tzMinutes'];

// genarate a function that returns a template string
function getDateFormatter(format, opt) {
    if (!format) {
        format = defaultFormat;
    }

    if (format in Formatter_by_format) {
        return Formatter_by_format[format];
    }
    
    let code = `
    let now = null;
    if (!userDate) {
        now = new Date();
    } else {
        now = new Date(userDate); // can be interpretted as UTC by default
        // '2023-01-01' is interpretted as midnight of UTC
        // '2023-01-01 00:00:00' is interpretted as midnight of local time
        // '2023-01-01 00:00:00 EST' is interpretted as EST time
        // '2023-01-01 00:00:00 GMT-0500' is interpretted as EST time
    }

    const yyyy = now.getFullYear(); 
    const mm = String(now.getMonth() + 1).padStart(2, "0"); // month is 0-indexed
    const dd = String(now.getDate()).padStart(2, "0"); 
    const HH = String(now.getHours()).padStart(2, "0"); 
    const MM = String(now.getMinutes()).padStart(2, "0"); 
    const SS = String(now.getSeconds()).padStart(2, "0");
    const ms = String(now.getMilliseconds()).padStart(3, "0");
    const tzMinutes = String(now.getTimezoneOffset()).padStart(4, "0");
    // const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    return ` + '`' + format + '`';

    if (opt && 'debug' in opt && opt.debug) {
        console.log(`code = ${code}`);
    }

    let f = new Function('userDate', code);

    Formatter_by_format[format] = f;
    
    return f;
}

function getTimestamp(date, opt) {
    let format = null;
    if (opt && 'formart' in opt) {
        format = opt['format']
    }
    let formatter = getDateFormatter(format, opt);

    return formatter(date);
}

export {
    getDateFormatter, getTimestamp, defaultFormat,
    availVars,
 };

// if this script is called directly, then run below
// if (require.main === module) { // this does not work in es6 module
if (process.argv[1] === import.meta.filename) {
    let formats = [
        '${yyyy}',
        null,
        "${yyyy}-${mm}-${dd} ${HH}:${MM}:${SS}",
    ];

    let dates = [
        null,
        '2023-01-01', // interpret as UTC
        '2023-01-01 00:00:00 EST', // to force to local time
    ];

    'use strict';

    for (let line of formats) {
        let f2 = getDateFormatter(line);
        for (let date of dates) {
            let d = f2(date);
            console.log(`format=${line}, date=${date}, result=${d}`);
        }
    }



    const testtools = await import('./testtools.js');

    let test_codes = () => {
        module.getTimestamp('2023-01-01', { format: "${yyyy}-${mm}-${dd} ${HH}:${MM}:${SS}.${ms} ${tzMinutes}" }); // interpretted as midnight of UTC
        module.getTimestamp('2023-01-01 00:00:00', { format: "${yyyy}-${mm}-${dd} ${HH}:${MM}:${SS}.${ms} ${tzMinutes}" }); // interpretted as local time
        module.getTimestamp('2023-01-01 00:00:00 EST', { format: "${yyyy}-${mm}-${dd} ${HH}:${MM}:${SS}.${ms} ${tzMinutes}" }) == '2023-01-01 00:00:00.000';
        module.getTimestamp();
    };

    // testtools.test_lines is async function but because
    // we call it on the top level, we don't add 'await' in front of it.
    testtools.test_lines(test_codes,
        import.meta.url, // this is to pass the current script's path to testtools
        // same as `file:${process.argv[1].replace(/\\/g, '/')}`,

        // { verbose: true }
    );
}
