// this is test against chrome new tab. as of 2024/12/13, it is chrome://new-tab-page
var e = document.evaluate("/html/body/input", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.shadowRoot.querySelector("ntp-iframe").shadowRoot.querySelector("#iframe");
        
const current_origin = window.location.origin;

var iframe_src = e.getAttribute('src');
var iframe_url = null
var iframe_origin = null
if (iframe_src) {
    //https://developer.mozilla.org/en-US/docs/Web/API/URL/origin
    iframe_url = new URL(iframe_src);
    iframe_origin = iframe_url.origin;
}

var iframe_inner = null;
if ( (!iframe_origin) || (current_origin.toUpperCase() === iframe_origin.toUpperCase()) ) { 
    //case-insensitive compare
    console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks
    iframe_inner=e.contentDocument || e.contentWindow.document;
    document = iframe_inner
} else {
    console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks
    window.location.replace(iframe_url);
}
    
