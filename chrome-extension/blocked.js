const encouragements = [
  'Deep work leads to great results.',
  'Every moment of focus builds momentum.',
  'You are building something important.',
  'Distraction is the enemy of creation.',
  'Stay present. Stay focused.',
  'Your future self will thank you.',
  'One task at a time. You can do this.',
  'Great work happens in focused blocks.',
];

function updateTimer() {
  chrome.storage.local.get(['focusStartTime', 'focusDuration'], (result) => {
    if (!result.focusStartTime || !result.focusDuration) {
      document.getElementById('timer').textContent = '00:00';
      return;
    }

    const startTime = new Date(result.focusStartTime).getTime();
    const durationMs = result.focusDuration * 60 * 1000;
    const now = Date.now();
    const elapsed = now - startTime;
    const remaining = Math.max(0, durationMs - elapsed);

    const totalSeconds = Math.ceil(remaining / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    document.getElementById('timer').textContent =
      `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    if (remaining <= 0) {
      document.getElementById('timer').textContent = '00:00';
      document.querySelector('.message').textContent =
        'Your focus session has ended! You can close this tab.';
    }
  });
}

function setRandomEncouragement() {
  const el = document.getElementById('encouragement');
  el.textContent = encouragements[Math.floor(Math.random() * encouragements.length)];
}

setRandomEncouragement();
updateTimer();
setInterval(updateTimer, 1000);
setInterval(setRandomEncouragement, 10000);
