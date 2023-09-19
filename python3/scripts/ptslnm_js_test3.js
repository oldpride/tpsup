console.log(`location1 = ${window.location}`)

var e = document.evaluate("/html/body/ntp-app", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.shadowRoot.querySelector("ntp-iframe").shadowRoot.querySelector("#iframe");

//var iframe_src = e.getAttribute('src');
//var iframe_url = new URL(iframe_src);
//console.log(`iframe_url = ${iframe_url}`)
//window.location.replace(iframe_url);
window.location.replace("chrome-untrusted://new-tab-page/one-google-bar?paramsencoded=");
console.log(`location2 = ${window.location}`)

document.evaluate("//div[3]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
console.log(`e = ${document.evaluate("//div[3]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.outerHTML}`)

//try {
//    e = document.evaluate("//div[3]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
//    console.log(`e = ${e.outerHTML}`)
//} catch (err) {
//    console.log(err.stack)
//}
//return e
//