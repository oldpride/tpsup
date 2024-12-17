// this is test against chrome new tab. as of 2024/12/13, it is chrome://new-tab-page
// the path to the search input is
// "xpath=/html[@class='focus-outline-visible']/body[1]/ntp-app[1]" "shadow" "css=#searchbox" "shadow" "css=#input"
var e = document.evaluate("/html[@class='focus-outline-visible']/body[1]/ntp-app[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.shadowRoot.querySelector("#searchbox").shadowRoot.querySelector("#input");
// var e = document.evaluate("/html[@class='focus-outline-visible']/body[1]/ntp-app[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue

// click on the search input
e.click();

console.log(`window.location = ${window.location}`)
console.log(`e.outerHTML = ${e.outerHTML}`)

// enter search text: selenium
e.value = 'selenium';

// we cannot hit enter key here. we will do it from outside

return e;
