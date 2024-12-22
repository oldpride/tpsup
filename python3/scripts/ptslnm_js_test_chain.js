// cd "C:/Users/tian/sitebase/github/tpsup/python3/scripts"
// python3 -m http.server 8000
// ptslnm url="http://localhost:8000/iframe_over_shadow_test_main.html" sleep=1 debug_after=url,consolelog jsfile=ptslnm_js_test_chain.js
var shadowHost = null; var e = document.evaluate("/html[1]/body[1]/iframe[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
console.log(`e=${e}, shadowHost=${shadowHost}`);
// remove shadowHost because iframe is not in shadow dom, no need to change locator_driver.
var shadowHost = null;
try {
    // cd(e.contentWindow); // cd is not defined in chrome's js. it is only in firefox.
    let iframe_inner = e.contentDocument || e.contentWindow.document;
    document = iframe_inner
    element_url = e.src;
    console.log('element_url=' + element_url);
    iframe_url = window.location.href;
    iframe_parent_url = document.referrer;
    console.log('iframe_url=' + iframe_url);
    console.log('iframe_parent_url=' + iframe_parent_url);
    const current_origin = window.location.origin;
    console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks
} catch(err) {
    // print the error. note that console.log() is not available in Selenium.
    // console log is only available in browser's webtools console.
    // we have a locator 'consolelog' to print it out.
    console.log(err.stack);

    let iframe_src = e.getAttribute('src');
    //iframe_url = new URL(iframe_src);
    iframe_url = iframe_src;
    console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks

    // window is the main JavaScript object root.
    // window.document or just document is the main object of the potentially visible.
    // below replaces the whole oject root - then we loss all the previous objects, eg, iframe parent.
    window.location.replace(iframe_url);
}
// 'iframe' doesn't return an element because it enters a new page, no element is selected yet.
// however, 'iframe' changes 'document' to the new iframe's document.
// 'document' corresponds to python selenium's 'driver'.

// let iframe_inner = e.contentDocument || e.contentWindow.document;
// document = iframe_inner
    
// var e = document.evaluate("id('shadow_host')", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
// var e = document.evaluate("id('shadow_host')", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;

e = e.contentWindow.document.evaluate("id('shadow_host')", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;

console.log(`e=${e}, shadowHost=${shadowHost}`);
