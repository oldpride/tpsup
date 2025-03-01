var a = 1;

var result = eval('a+1');
console.log(`result1 = ${result}`);

var f = new Function('return a+1');
console.log(`result2=${f()}`);
