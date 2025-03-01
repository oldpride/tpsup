var a2 = 1;
var lines = [
    ['x', 'y', 'return x + y;'],
    ['"use strict"; return this'],
    ['return 1+1'],
    ['return a2+1'],
];

for (let l of lines) {
    var f = new Function(...l);
    console.log(`Function('${l}') = %o`, f);
    console.log(`Function('${l}')() = %o`, f());
    console.log('');
}
