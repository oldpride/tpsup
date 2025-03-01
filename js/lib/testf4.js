var globalVar = 'I am global';

function exampleFunction() {
  var localVar = 'I am local';

  var myFunc = new Function('return globalVar + " and I cannot access localVar"');

  console.log(myFunc()); // Output: I am global and I cannot access localVar
}

exampleFunction();
