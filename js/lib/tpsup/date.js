// genarate a function that returns a template string
function getDateFunction(format, opt) {
    if (!format) {
        format = '${yyyy}-${mm}-${dd} ${HH}:${MM}:${SS}';
    }
    
    let code = `
    let now = null;
    if (!userDate) {
        now = new Date();
    } else {
        now = new Date(userDate); // interpretted as UTC by default
    }

    const yyyy = now.getFullYear(); 
    const mm = String(now.getMonth() + 1).padStart(2, "0"); // month is 0-indexed
    const dd = String(now.getDate()).padStart(2, "0"); 
    const HH = String(now.getHours()).padStart(2, "0"); 
    const MM = String(now.getMinutes()).padStart(2, "0"); 
    const SS = String(now.getSeconds()).padStart(2, "0"); 
    return ` + '`' + format + '`';

    if (opt && 'debug' in opt && opt.debug) {
        console.log(`code = ${code}`);
    }

    let f = new Function('userDate', code);
    return f;
}

export { getDateFunction };

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
        let f2 = getDateFunction(line);
        for (let date of dates) {
            let d = f2(date);
            console.log(`format=${line}, date=${date}, result=${d}`);
        }
    }
}
