// start with auto:blank
console.log(`window.location = ${window.location}`)

// go to new tab page
// window.location.assign("chrome://new-tab-page")
// the above failed: security 8 Not allowed to load local resource: chrome://new-tab-page/
if (!window.location.replace("chrome://new-tab-page")) {
    // the above failed: security 10 Not allowed to load local resource: chrome://new-tab-page/

    // this error should be propagated to the caller (python selenium)
    throw new Error("window.location.replace failed")
}

console.log(`window.location = ${window.location}`)
