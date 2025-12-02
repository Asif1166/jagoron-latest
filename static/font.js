
if ("FileReader" in window && "Promise" in window && "fetch" in window) {
    const fontsForStorage = [{ "name": "notoserifregular", "fontFamily": "Noto Serif Bengali", "fontWeight": 400, "fontStyle": "normal", "src": "/static/fonts/bold.woff2", "fontDisplay": "optional" }];
    const getFont = (location) => {
        return new Promise(function (resolve, reject) {
            fetch(location).then(function (res) {
                return res.blob()
            }).then(function (blob) {
                if (blob && blob.constructor.name === 'Blob') {
                    var reader = new FileReader()
                    reader.addEventListener('load', function () {
                        resolve(this.result)
                    })
                    reader.readAsDataURL(blob)
                }
            }).catch(reject)
        })
    };
    const createStyleAndAttach = (styleInnerText) => {
        const head = document.head || document.getElementsByTagName('head')[0];
        const fontStylePlaceholder = document.createElement('style');
        fontStylePlaceholder.innerHTML = styleInnerText;
        head.appendChild(fontStylePlaceholder);
    };
    const retrieveAndStoreFont = (font, storageKey, shouldAttachStyle) => {
        const fontLocation = font.src ? font.src : '' + font.version + (font.subsets ? '/subsets' : '') + '/' + font.name + '.woff2';
        window.addEventListener("load", (e) => {
            getFont(fontLocation).then((fontContents) => {
                const forStorage = { base64Contents: fontContents, fontFamily: font.fontFamily, fontWeight: font.fontWeight, fontVersion: font.version };
                localStorage.setItem(storageKey, JSON.stringify(forStorage));
                if (shouldAttachStyle) {
                    const styleInnerText = '@font-face{font-family: "' + font.fontFamily + '"; font-weight: ' + font.fontWeight + ';src:url("' + fontContents + '") format("woff2");font-display: swap;}';
                    createStyleAndAttach(styleInnerText);
                }
            });
        });
    };
    fontsForStorage.forEach(font => {
        const storageKey = 'font-' + font.name;
        let fontContents = localStorage.getItem(storageKey);

        if (!fontContents) {
            retrieveAndStoreFont(font, storageKey, true);
        }
        else {
            const { base64Contents, fontFamily, fontWeight, fontVersion } = JSON.parse(fontContents);
            const styleInnerText = '@font-face{font-family: "' + fontFamily + '"; font-weight: ' + fontWeight + '; src:url("' + base64Contents + '") format("woff2");font-display: swap;}';
            createStyleAndAttach(styleInnerText);
            if (fontVersion !== font.version) {
                retrieveAndStoreFont(font, storageKey, false);
            }
        }
    });
}
let wrappedPageTimeStart = new Date();
let wrappedYear = wrappedPageTimeStart.getFullYear();
let wrappedMonth = wrappedPageTimeStart.getMonth() + 1;
let wrappedStorageKey = 'ws_bbc_wrapped';
let wrappedContents = {};
wrappedContents[wrappedYear] = {
    'byMonth': {},
    'pageTypeCounts': {},
    'serviceCounts': {},
    'topicCounts': {},
    'duration': 0,
    'wordCount': 0,
};
wrappedContents[wrappedYear].byMonth[wrappedMonth] = 0;
let saveWrapped = () => {
    localStorage.setItem(wrappedStorageKey, JSON.stringify(wrappedContents));
}
let wrappedLocalStorageContents = localStorage.getItem(wrappedStorageKey);
if (wrappedLocalStorageContents) {
    const wrappedLocalStorageContentsParsed = JSON.parse(wrappedLocalStorageContents);
    if (wrappedLocalStorageContentsParsed.hasOwnProperty(wrappedYear)) {
        wrappedContents[wrappedYear] = wrappedLocalStorageContentsParsed[wrappedYear] || wrappedContents[wrappedYear];
        wrappedContents[wrappedYear].byMonth[wrappedMonth] = wrappedLocalStorageContentsParsed[wrappedYear].byMonth[wrappedMonth] || 0;
    }
}
let wrappedContentsShortcut = wrappedContents[wrappedYear];
let wrappedTopics = undefined;
if (wrappedTopics) {
    wrappedTopics.forEach(({ topicName }) => {
        wrappedContentsShortcut.topicCounts[topicName] = wrappedContentsShortcut.topicCounts[topicName] ? wrappedContentsShortcut.topicCounts[topicName] + 1 : 1;
    });
}
document.onvisibilitychange = () => {
    if (document.visibilityState === "hidden") {
        const wrappedTimeNow = new Date();
        const wrappedDifference = wrappedTimeNow - wrappedPageTimeStart;
        wrappedContentsShortcut.duration = wrappedContentsShortcut.duration ? wrappedContentsShortcut.duration + wrappedDifference : wrappedDifference;
        saveWrapped();
    }
    else {
        wrappedPageTimeStart = new Date();
    }
};
wrappedContentsShortcut.wordCount = wrappedContentsShortcut.wordCount + 0;
wrappedContentsShortcut.serviceCounts.bengali = wrappedContentsShortcut.serviceCounts.bengali ? wrappedContentsShortcut.serviceCounts.bengali + 1 : 1;
wrappedContentsShortcut.pageTypeCounts.home = wrappedContentsShortcut.pageTypeCounts.home ? wrappedContentsShortcut.pageTypeCounts.home + 1 : 1;
wrappedContentsShortcut.byMonth[wrappedMonth] = wrappedContentsShortcut.byMonth[wrappedMonth] ? wrappedContentsShortcut.byMonth[wrappedMonth] + 1 : 1;
wrappedContents[wrappedYear] = wrappedContentsShortcut;
