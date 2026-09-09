function handleClick() {
  const log = document.getElementById('status-log');
  log.innerHTML = '✨ <strong>Success:</strong> Interactive event triggered! Dynamic code execution active at ' + new Date().toLocaleTimeString();
  log.style.color = '#34d399';
}
console.log('IRIS Workspace Application Initialized.');