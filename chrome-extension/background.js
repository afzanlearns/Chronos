setInterval(async () => {
  const [activeTab] = await chrome.tabs.query({active: true, currentWindow: true});

  if (activeTab) {
    chrome.runtime.sendNativeMessage('com.chronos.tracker', {
      type: 'tab_update',
      title: activeTab.title,
      url: activeTab.url,
      favIconUrl: activeTab.favIconUrl,
      timestamp: new Date().toISOString()
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.log("Error:", chrome.runtime.lastError);
      }
    });
  }
}, 30000);
