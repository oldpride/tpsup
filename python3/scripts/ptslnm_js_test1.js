console.log(`location1 = ${window.location}`)

// window.location.assign("chrome-untrusted://new-tab-page/one-google-bar?paramsencoded=");
window.location.replace("chrome-untrusted://new-tab-page/one-google-bar?paramsencoded=");
console.log(`location2 = ${window.location}`)

//var e = document.evaluate("//div[3]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
//console.log(`e = ${e.outerHTML}`)
//return e;

console.log(`e = ${document.evaluate("//div[3]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.outerHTML}`)
//console.log(`e = ${document.evaluate("//html", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.outerHTML}`)