// cd "C:/Users/tian/sitebase/github/tpsup/python3/scripts"
// python3 -m http.server 8000
// ptslnm url="http://localhost:8000/iframe_over_shadow_test_main.html" sleep=1 debug_after=url,consolelog jsfile=ptslnm_js_test_iframe_xpath.js

// Get the iframe element
var iframe = document.evaluate("/html[1]/body[1]/iframe[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; 

// Access the iframe's document object
var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

// make iframeDoc global
window.iframeDoc = iframeDoc;

// later when other scripts not sure whether to use document or iframeDoc,
var startDoc = document;
if (window.iframeDoc) {
    startDoc = window.iframeDoc;
}
var e2 = startDoc.evaluate("id('shadow_host')", startDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
console.log(`e2=${e2}`);
