function f1(a, b) { return a + b; };
let c = 2;




    // let source_code = `return ${line}`;
    let source_code = `return c+1`;
 
        console.log(`source_code = ${source_code}`)


    let f = new Function(source_code);

let result = f();
console.log(`result = ${result}`)
