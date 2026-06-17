const API_BASE = 'http://localhost:5000/api';

let blockedDomains = [];
let isFocusMode = false;
let sessionCheckInterval = null;

function extractDomain(url) {
  try {
    return new URL(url).hostname.replace('www.', '');
  } catch {
    return '';
  }
}

function sendTabData() {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    const activeTab = tabs[0];
    if (!activeTab || !activeTab.url) return;

    const domain = extractDomain(activeTab.url);

    chrome.runtime.sendNativeMessage('com.chronos.tracker', {
      type: 'tab_update',
      title: activeTab.title,
      url: activeTab.url,
      domain: domain,
      favIconUrl: activeTab.favIconUrl,
      timestamp: new Date().toISOString()
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.log('Native messaging error:', chrome.runtime.lastError);
      }
    });

    fetch(`${API_BASE}/browser/activity`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        url: activeTab.url,
        title: activeTab.title,
        domain: domain,
        timestamp: new Date().toISOString()
      })
    }).catch(err => console.log('API error:', err));
  });
}

function checkFocusState() {
  chrome.storage.local.get(['focusMode', 'blockedDomains'], (result) => {
    isFocusMode = result.focusMode || false;
    blockedDomains = result.blockedDomains || [];
  });
}

function isBlockedUrl(url) {
  if (!isFocusMode || blockedDomains.length === 0) return false;
  try {
    const domain = extractDomain(url);
    return blockedDomains.some(bd => domain === bd || domain.endsWith('.' + bd));
  } catch {
    return false;
  }
}

chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    if (isBlockedUrl(details.url)) {
      const domain = extractDomain(details.url);

      fetch(`${API_BASE}/browser/activity`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          url: details.url,
          title: '(Blocked)',
          domain: domain,
          timestamp: new Date().toISOString()
        })
      }).catch(() => {});

      return {redirectUrl: chrome.runtime.getURL('blocked.html')};
    }
    return {};
  },
  {urls: ['<all_urls>']},
  ['blocking']
);

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'startFocus') {
    isFocusMode = true;
    blockedDomains = message.blockedDomains || [];
    chrome.storage.local.set({
      focusMode: true,
      blockedDomains: blockedDomains,
      focusStartTime: new Date().toISOString(),
      focusDuration: message.duration || 25
    }, () => {
      sendResponse({status: 'ok'});
    });
    return true;
  }

  if (message.type === 'stopFocus') {
    isFocusMode = false;
    blockedDomains = [];
    chrome.storage.local.set({
      focusMode: false,
      blockedDomains: []
    }, () => {
      sendResponse({status: 'ok'});
    });
    return true;
  }

  if (message.type === 'getFocusState') {
    sendResponse({
      focusMode: isFocusMode,
      blockedDomains: blockedDomains
    });
  }
});

checkFocusState();
setInterval(() => {
  sendTabData();
  checkFocusState();
}, 5000);
