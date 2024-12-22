// cd "C:/Users/tian/sitebase/github/tpsup/python3/scripts"
// python3 -m http.server 8000
// ptslnm url="http://localhost:8000/iframe_over_shadow_test_main.html" sleep=1 debug_after=url,consolelog jsfile=ptslnm_js_test_iframe_xpath.js

// Get the iframe element
var iframe = document.evaluate("/html[1]/body[1]/iframe[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; 

// Access the iframe's document object
var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

var e1 = iframeDoc.evaluate("id('shadow_host')", iframeDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
console.log(`e1=${e1}`);

// can I assign iframeDoc to document?
window.document = iframeDoc;
var e2 = window.document.evaluate("id('shadow_host')", window.document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
console.log(`e2=${e2}`);

// all below returns are not working!!! 
//     Error: "stale element not found in the current frame"
// return {e1:e1, e2:e2};
// return { iframeDoc: iframeDoc };
// return { iframe: iframe };
// to persist the value, assign it to document.
document.e1 = e1;
document.e2 = e2;
document.iframeDoc = iframeDoc;
return "please pick my vaule from document.e1, document.e2, document.iframeDoc";
