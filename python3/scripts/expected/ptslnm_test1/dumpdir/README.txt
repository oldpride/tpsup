
element/
    directory for element dump

dom/
    directory for dom dump

page/
    directory for page dump

iframe*.html
    the iframe html of the page (dump all) or specified element (dump element)
    note that when there is a shadow dom, the iframe*.html doesn't show the shadow dom;
    you need to look at shadow*.html for that.

locator_chain_list.txt
    the locator chain on command line format
    eg
        "xpath=id('shadow_host')" "shadow"
        "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow"

locator_chain_map.txt
    The most useful file!!!

    the locator chain to shadow/iframe mapping. 
    This shows how to reach to each child shadow or iframe from the scope (element, iframe, or root).
    you can run ptslnm with the chain on command line to locate the element.
    eg
        iframe001: "xpath=/html[1]/body[1]/iframe[1]" "iframe"
        iframe001.shadow001: "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow"
        iframe001.shadow001.shadow002: "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow"
    
    you may see shadow doms not defined by you. for example, form input may have a shadow dom.
        <!-- shadow_test2_main.html -->
        <input type="checkbox" />
        <input type="file" />
    they create two shadow doms
        shadow001.shadow003: "xpath=id('shadow_host')" "shadow" "css=INPUT:nth-child(4)" "shadow"
        shadow001.shadow004: "xpath=id('shadow_host')" "shadow" "css=INPUT:nth-child(6)" "shadow"

screenshot_element.png
    the screenshot of the element, iframe, or shadow dom.

shadow*.html
    the shadow dom of the page or specific element.
    it is the HTML of the shadow host.

source.html
    the source html specific to dump scope: element, or dom, or the whoe page: 
        if dump_element, this will be the html of the element.
        if dump_dom, this will be the html of the innest iframe dom that contains the element.
                     we cannot get the innest shadow dom html because shadowRoot (shadow driver) 
                     has no page_source attribute.
        if dump_all, this will be the whole page.

    dump_element and dump_dom are reliable because they are not affected by the driver's state (in iframe/shadow or not).
    dump_page is unreliable or have side effect because it needs to switch driver to the original driver.

    note that when there is a shadow dom, the source.html doesn't show the shadow dom's full content.
    you need to look at shadow*.html for that.

    normally source.html will be different from the original html because source.html contains
    dynamic content, such as the content of shadow dom or js generated content.

    you will see see some tags are neither from the original html nor from the js that you provided.
    for example: 
        <input type="button" value="Choose File" pseudo="-webkit-file-upload-button" id="file-upload-button" aria-hidden="true">
    here,
        'aria' (Accessible Rich Internet Applications) is a set attributes that define ways to make web content and web 
        applications (especially those developed with JavaScript) more accessible to people with disabilities.

        'pseudo': A CSS pseudo-class is a keyword added to a selector that specifies a special state of the selected element(s).
        For example, the pseudo-class :hover can be used to select a button when a user's pointer hovers over the button and
        this selected button can then be styled.

xpath_chain_list.txt
    similar to locator_chain_list.txt, but only xpath
    eg
        /html[1]/body[1]/iframe[1] iframe
        /html[1]/body[1]/iframe[1] iframe id('shadow_host') shadow
        /html[1]/body[1]/iframe[1] iframe id('shadow_host') shadow /div[@id='nested_shadow_host'] shadow
    note: xpath* files are less useful than locator* files, because xpath is not useable in shadow dom.

xpath_chain_map.txt
    similar to locator_chain_map.txt, but only xpath
    eg
        iframe001: /html[1]/body[1]/iframe[1] iframe
        iframe001.shadow001: /html[1]/body[1]/iframe[1] iframe id('shadow_host') shadow
        iframe001.shadow001.shadow002: /html[1]/body[1]/iframe[1] iframe id('shadow_host') shadow /div[@id='nested_shadow_host'] shadow
    note: xpath* files are less useful than locator* files, because xpath is not useable in shadow dom.

xpath_list.txt
    all xpaths of shadow/iframe.
    The list are single x-paths pointing to iframe/shadow, not a chain as in xpath_chain_list.txt
    eg
        /html[1]/body[1]/iframe[1]
        id('shadow_host')
        /iframe[1]
        /div[@id='nested_shadow_host']
    note: xpath* files are less useful than locator* files, because xpath is not useable in shadow dom.

xpath_map.txt
    map between xpath and shadow/iframe. 
    This map uses a single xpath to locate a iframe/shadow, not a chain as in xpath_chain_map.txt
    eg
        iframe001: /html[1]/body[1]/iframe[1]
        shadow001: id('shadow_host')
        shadow001.iframe002: /iframe[1]
        shadow001.shadow002: /div[@id='nested_shadow_host']
    note: xpath* files are less useful than locator* files, because xpath is not useable in shadow dom.
    for example, the last line above is a nested shadow dom, which is not reachable by the xpath.

How to use these files:
    scenario 1: I want to locate the search box in google new tab page
        dump the page
            $ ptslnm -rm newtab -dump $HOME/dumpdir -scope all
        open browser, go to new tab page, open devtools, inspect the search box html
            it has: id="input"
        find this string in our dump files
            $ cd $HOME/dumpdir/page
            $ grep 'id="input"' *
            shadow009.html:<div id="inputWrapper"><input id="input" class="truncate" type="search" ...
            shadow028.html:        <input id="input" part="input" autocomplete="off" ...

            shadow009.html is the shadow dom that contains the search box.

            find the locator chain for shadow009.html
            $ grep shadow009 locator_chain_map.txt
            shadow006.shadow009: "xpath=/html[@class='focus-outline-visible']/body[1]/ntp-app[1]" "shadow" "css=#searchbox" "shadow"

            this locator chain will bring us the the shadow that contains the search box.
        now we need to find the css selector (xpath doesn't work in shadow dom) for the search box
            in browser, inspect the search box. in devtools, right click the search box, copy css selector.
            it is: #searchbox

        now we can locate the search box
            $ ptslnm newtab -locator "xpath=/html[@class='focus-outline-visible']/body[1]/ntp-app[1]" "shadow" "css=#searchbox"
    
