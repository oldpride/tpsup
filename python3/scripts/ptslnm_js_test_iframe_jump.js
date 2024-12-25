// from javascript, we can access each iframe's content by using the iframe's document object, very easy

// cd "C:/Users/tian/sitebase/github/tpsup/python3/scripts"
// python3 -m http.server 8000
// ptslnm url="http://localhost:8000/iframe_nested_test_main.html" sleep=1 debug_after=url,consolelog,domstack jsfile=ptslnm_js_test_iframe_jump.js

var startDoc = document;
var e = startDoc.evaluate("//iframe[1]", startDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
var iframeElement = e;
window.iframeDoc_1 = e.contentDocument || e.contentWindow.document;
window.iframeElement_1 = e;
console.log(`iframeElement_1=${window.iframeElement_1}`);

var startDoc = window.iframeDoc_1;
var e = startDoc.evaluate("//iframe[2]", startDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
window.iframeDoc_1_2 = e.contentDocument || e.contentWindow.document;
window.iframeElement_1_2 = e;
console.log(`iframeElement_1_2=${window.iframeElement_1_2}`);

var startDoc = window.iframeDoc_1_2;
var e = startDoc.evaluate("//iframe[1]", startDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
window.iframeDoc_1_2_1 = e.contentDocument || e.contentWindow.document;
window.iframeElement_1_2_1 = e;
console.log(`iframeElement_1_2_1=${window.iframeElement_1_2_1}`);

var startDoc = window.iframeDoc_1_2_1;
var e = startDoc.evaluate("/html/body/div[1]/p[1]", startDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
console.log(`e=${e}`);

// access each iframe's content by using the iframe's document object
console.log(`document.URL=${document.URL}`);
console.log(`window.iframeDoc_1.URL=${window.iframeDoc_1.URL}`);
console.log(`window.iframeDoc_1_2.URL=${window.iframeDoc_1_2.URL}`);
console.log(`window.iframeDoc_1_2_1.URL=${window.iframeDoc_1_2_1.URL}`);
