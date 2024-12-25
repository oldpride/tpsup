// cd "C:/Users/tian/sitebase/github/tpsup/python3/scripts"
// python3 -m http.server 8000
// ptslnm url="http://localhost:8000/iframe_over_shadow_test_main.html" sleep=1 debug_after=url,consolelog jsfile=ptslnm_js_test_iframe_xpath_bad.js

// Get the iframe element
var iframe = document.evaluate("/html[1]/body[1]/iframe[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; 

// Access the iframe's document object
var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

var e1 = iframeDoc.evaluate("id('shadow_host')", iframeDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
console.log(`e1=${e1}`); // e1=[object HTMLDivElement], good

// can I assign iframeDoc to document? no. because window.document is read-only.
// https://stackoverflow.com/questions/79300259
window.document = iframeDoc;
var e2 = window.document.evaluate("id('shadow_host')", window.document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
console.log(`e2=${e2}`); // e2=null, bad

// return {e1:e1, e2:e2};
// all above returns are not working!!! 
//     Error: "stale element not found in the current frame"
// the error is from python's driver.execute_script() function. This is because e1 and e2 
// are in the iframe's context in js, but the python 'driver' is still in the main context.
// Therefore, e1 and e2 are not accessible to python.

// return { iframeDoc: iframeDoc };
// the above doen't work either. The reason is that python's driver.execute_script() only
// takes primitive types and WebElement. It doesn't take other types. iframeDoc is not a
// WebElement.

// therefore, to persist the value, attach it to 'window' - monkey patching. 
// Don't attach it to 'document' because entering iframe will reset 'document'.
// we can also return an indicator to tell python to get the value from window.
window.e1 = e1;
window.e2 = e2;
window.iframeDoc = iframeDoc;
return { weSetWindowiframeDoc: 1, iframeElement: iframe };
